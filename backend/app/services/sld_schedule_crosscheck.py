"""SLD-to-Schedule Cross-Check — the #1 review check per real engineer feedback.

Extracts equipment designations (Q-numbers) from SLD pages and panel schedule
pages, then compares: flags mismatches in frame size, trip rating, kAIC,
poles, breaker model, and items that exist in one but not the other.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from .cross_reference import CrossRefFinding


@dataclass
class ScheduleEntry:
    """A breaker/device entry from either the SLD or a panel schedule."""
    q_designation: str  # Q1, Q2, Q7, Q14A-H, etc.
    qf_designation: Optional[str] = None  # QF-number (ABB internal tag)
    breaker_model: Optional[str] = None  # E6.2H, XT7H, XT2H, etc.
    frame_amps: Optional[int] = None
    trip_amps: Optional[int] = None
    poles: Optional[int] = None
    kaic: Optional[int] = None  # Interrupting rating in kA
    description: Optional[str] = None  # "MECH UPS", "NETWORK RACKS", etc.
    feed_type: Optional[str] = None  # INCOMING, OUTGOING, etc.
    mounting: Optional[str] = None  # FIXED, PLUGIN, WITHDRAWABLE, DRAWOUT
    trip_unit: Optional[str] = None  # EKIP TOUCH MEASURING LSI, etc.
    page_number: int = 0
    source: str = ""  # "SLD" or "schedule"
    raw_text: str = ""


def extract_schedule_entries(pages: list[dict]) -> tuple[list[ScheduleEntry], list[ScheduleEntry]]:
    """Extract breaker entries from SLD pages and schedule pages separately.

    Returns: (sld_entries, schedule_entries)
    """
    sld_entries = []
    schedule_entries = []

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]
        text_lower = page_data.get("text_lower", text.lower())
        page_type = page_data.get("page_type", "unknown")

        # If page_type not set, detect from content keywords
        if page_type == "unknown" or not page_type:
            if any(kw in text_lower for kw in ["single line", "one-line", "one line", "sld"]):
                page_type = "single_line_diagram"
            elif any(kw in text_lower for kw in ["breaker details", "breaker type", "cubicle no",
                                                   "panel schedule", "branch circuit"]):
                page_type = "panel_schedule"

        if page_type == "single_line_diagram":
            entries = _extract_from_sld(text, page_num)
            sld_entries.extend(entries)
        elif page_type in ("panel_schedule", "equipment_schedule"):
            entries = _extract_from_schedule(text, page_num)
            schedule_entries.extend(entries)

    return sld_entries, schedule_entries


def crosscheck_sld_vs_schedule(sld_entries: list[ScheduleEntry],
                                schedule_entries: list[ScheduleEntry]) -> list[CrossRefFinding]:
    """Compare SLD entries against schedule entries. Flag discrepancies."""
    findings = []

    # Index by Q-designation
    # Q-numbers like Q1, Q2, Q3 are reused across different panels (MDB vs MSDB vs IT MDB).
    # Only cross-check Q-numbers that appear uniquely — if Q1 appears on 3+ different pages
    # it's being reused and we can't match them without panel scoping.
    from collections import Counter

    sld_q_pages = Counter()
    for entry in sld_entries:
        q = _normalize_q(entry.q_designation)
        if q:
            sld_q_pages[q] += 1

    schedule_q_pages = Counter()
    for entry in schedule_entries:
        q = _normalize_q(entry.q_designation)
        if q:
            schedule_q_pages[q] += 1

    # Skip Q-numbers that appear more than once on the SLD (reused across panels)
    sld_by_q = {}
    for entry in sld_entries:
        q = _normalize_q(entry.q_designation)
        if q and sld_q_pages[q] == 1:
            sld_by_q[q] = entry

    schedule_by_q = {}
    for entry in schedule_entries:
        q = _normalize_q(entry.q_designation)
        if q and schedule_q_pages[q] <= 2:
            if q not in schedule_by_q or (entry.breaker_model and not schedule_by_q[q].breaker_model):
                schedule_by_q[q] = entry

    # --- Check 1: Items in schedule but NOT on SLD ---
    for q, sched in schedule_by_q.items():
        if q not in sld_by_q:
            findings.append(CrossRefFinding(
                finding_type="missing_from_sld",
                severity="major",
                equipment_1=sched.q_designation,
                equipment_2=None,
                page_number=sched.page_number,
                description=(
                    f"Page {sched.page_number}: Breaker {sched.q_designation} "
                    f"({sched.breaker_model or 'model TBD'} {sched.frame_amps or '?'}A) "
                    f"exists in panel schedule but NOT found on the SLD. "
                    f"Description: {sched.description or 'N/A'}."
                ),
                reference_code="Drawing Consistency",
                recommendation="Add this breaker to the SLD or confirm it is intentionally omitted.",
            ))

    # --- Check 2: Items on SLD but NOT in schedule ---
    for q, sld in sld_by_q.items():
        if q not in schedule_by_q:
            # Only flag breakers with real designations (not generic ones)
            if sld.breaker_model or sld.frame_amps:
                findings.append(CrossRefFinding(
                    finding_type="missing_from_schedule",
                    severity="major",
                    equipment_1=sld.q_designation,
                    equipment_2=None,
                    page_number=sld.page_number,
                    description=(
                        f"SLD Page {sld.page_number}: Breaker {sld.q_designation} "
                        f"({sld.breaker_model or '?'} {sld.frame_amps or '?'}A) "
                        f"shown on SLD but NOT found in any panel schedule."
                    ),
                    reference_code="Drawing Consistency",
                    recommendation="Add this breaker to the panel schedule or confirm SLD is correct.",
                ))

    # --- Check 3: Items in BOTH — compare details ---
    for q in sld_by_q:
        if q not in schedule_by_q:
            continue

        sld = sld_by_q[q]
        sched = schedule_by_q[q]

        # Compare breaker model
        if sld.breaker_model and sched.breaker_model:
            sld_model = _normalize_model(sld.breaker_model)
            sched_model = _normalize_model(sched.breaker_model)
            if sld_model and sched_model and sld_model != sched_model:
                findings.append(CrossRefFinding(
                    finding_type="model_mismatch",
                    severity="major",
                    equipment_1=sld.q_designation,
                    equipment_2=None,
                    page_number=sched.page_number,
                    description=(
                        f"Breaker {q}: Model mismatch — SLD (pg {sld.page_number}) shows "
                        f"{sld.breaker_model}, schedule (pg {sched.page_number}) shows {sched.breaker_model}."
                    ),
                    reference_code="Drawing Consistency",
                    recommendation="Resolve model discrepancy between SLD and panel schedule.",
                ))

        # Compare frame size
        if sld.frame_amps and sched.frame_amps and sld.frame_amps != sched.frame_amps:
            findings.append(CrossRefFinding(
                finding_type="frame_mismatch",
                severity="critical",
                equipment_1=sld.q_designation,
                equipment_2=None,
                page_number=sched.page_number,
                description=(
                    f"Breaker {q}: Frame size mismatch — SLD (pg {sld.page_number}) shows "
                    f"{sld.frame_amps}A, schedule (pg {sched.page_number}) shows {sched.frame_amps}A. "
                    f"This affects fault current calculations and coordination study."
                ),
                reference_code="Drawing Consistency, SCCR",
                recommendation="Resolve frame size discrepancy. Ensure SCCSAF uses correct value.",
            ))

        # Compare trip rating
        if sld.trip_amps and sched.trip_amps and sld.trip_amps != sched.trip_amps:
            findings.append(CrossRefFinding(
                finding_type="trip_mismatch",
                severity="critical",
                equipment_1=sld.q_designation,
                equipment_2=None,
                page_number=sched.page_number,
                description=(
                    f"Breaker {q}: Trip rating mismatch — SLD (pg {sld.page_number}) shows "
                    f"{sld.trip_amps}A trip, schedule (pg {sched.page_number}) shows {sched.trip_amps}A trip."
                ),
                reference_code="Drawing Consistency, NEC 240",
                recommendation="Resolve trip rating discrepancy. Verify conductor sizing matches correct trip.",
            ))

        # Compare kAIC (interrupting rating)
        if sld.kaic and sched.kaic and sld.kaic != sched.kaic:
            findings.append(CrossRefFinding(
                finding_type="kaic_mismatch",
                severity="critical",
                equipment_1=sld.q_designation,
                equipment_2=None,
                page_number=sched.page_number,
                description=(
                    f"Breaker {q}: Interrupting rating mismatch — SLD (pg {sld.page_number}) shows "
                    f"{sld.kaic}kAIC, schedule (pg {sched.page_number}) shows {sched.kaic}kAIC. "
                    f"Verify adequate for available fault current per NEC 110.9."
                ),
                reference_code="NEC 110.9, Drawing Consistency",
                recommendation="Resolve kAIC discrepancy. Use the higher value or verify AFC at this point.",
            ))

        # Compare poles
        if sld.poles and sched.poles and sld.poles != sched.poles:
            findings.append(CrossRefFinding(
                finding_type="poles_mismatch",
                severity="major",
                equipment_1=sld.q_designation,
                equipment_2=None,
                page_number=sched.page_number,
                description=(
                    f"Breaker {q}: Pole count mismatch — SLD (pg {sld.page_number}) shows "
                    f"{sld.poles}P, schedule (pg {sched.page_number}) shows {sched.poles}P."
                ),
                reference_code="Drawing Consistency",
                recommendation="Resolve pole count discrepancy. 4P required for switched neutral applications.",
            ))

    # --- Check 4: kAIC inconsistency among same-level breakers ---
    # Group schedule entries by their feed type and similar ratings
    incoming_breakers = [s for s in schedule_entries if s.feed_type and "incoming" in s.feed_type.lower()]
    if len(incoming_breakers) >= 2:
        kaics = [(s.q_designation, s.kaic, s.page_number) for s in incoming_breakers if s.kaic]
        if len(kaics) >= 2:
            unique_kaics = set(k for _, k, _ in kaics)
            if len(unique_kaics) > 1:
                desigs = ", ".join(f"{q} ({k}kA)" for q, k, _ in kaics)
                findings.append(CrossRefFinding(
                    finding_type="kaic_inconsistency",
                    severity="major",
                    equipment_1="Multiple Incomers",
                    equipment_2=None,
                    page_number=kaics[0][2],
                    description=(
                        f"Incoming breakers have different interrupting ratings: {desigs}. "
                        f"If fed from the same source, these should typically have the same kAIC. "
                        f"Verify the reason for the discrepancy."
                    ),
                    reference_code="NEC 110.9",
                    recommendation="Confirm different kAIC ratings are intentional and adequate for AFC at each point.",
                ))

    # --- Check 5: TBD / missing trip units ---
    for entry in schedule_entries:
        if entry.trip_unit and "tbd" in entry.trip_unit.lower():
            findings.append(CrossRefFinding(
                finding_type="tbd_trip_unit",
                severity="major",
                equipment_1=entry.q_designation,
                equipment_2=None,
                page_number=entry.page_number,
                description=(
                    f"Page {entry.page_number}: Breaker {entry.q_designation} "
                    f"({entry.breaker_model or '?'}) — trip unit is listed as TBD. "
                    f"Trip unit type affects coordination study and must be specified."
                ),
                reference_code="Coordination Study",
                recommendation="Specify trip unit type (TMD, TMA, Ekip Touch, etc.) before fabrication.",
            ))

    return findings


# ---------------------------------------------------------------------------
#  SLD Extraction
# ---------------------------------------------------------------------------

def _extract_from_sld(text: str, page_num: int) -> list[ScheduleEntry]:
    """Extract breaker entries from SLD page text."""
    entries = []
    text_lower = text.lower()

    # Pattern: -QF{n}/Q{n} followed by breaker model and ratings
    # Example: "-QF2/Q8\nE6.2 H 4000 EkipTouch\nLSIG 4000"
    # Example: "-QF12/Q9\nXT7H 1000 Ekip Touch\nMeasuring LSI 1000"
    for match in re.finditer(r'-QF(\d+)/Q(\d+[A-Z]?)', text):
        qf_num = match.group(1)
        q_num = match.group(2)
        q_desig = f"Q{q_num}"

        # Get context after this match (next 200 chars)
        start = match.end()
        context = text[start:start+300]
        context_lower = context.lower()

        entry = ScheduleEntry(
            q_designation=q_desig,
            qf_designation=f"QF{qf_num}",
            page_number=page_num,
            source="SLD",
            raw_text=text[match.start():start+150],
        )

        # Extract breaker model
        model_match = re.search(r'(E\d\.\d\s*[HNSLV]?|XT\d+[HNSLBC]?)\s*(\d{2,5})', context)
        if model_match:
            entry.breaker_model = model_match.group(1).strip()
            entry.frame_amps = int(model_match.group(2))
            # Trip is usually same as frame on SLD, or specified as LSI/LSIG number
            lsi_match = re.search(r'(?:LSI|LSIG)\s*(\d+)', context)
            if lsi_match:
                entry.trip_amps = int(lsi_match.group(1))
            else:
                entry.trip_amps = entry.frame_amps

        # Extract poles
        pole_match = re.search(r'(\d)\s*[pP]', context)
        if pole_match:
            entry.poles = int(pole_match.group(1))

        # Extract kAIC
        ka_match = re.search(r'(\d{2,3})\s*(?:ka|kaic)', context_lower)
        if ka_match:
            entry.kaic = int(ka_match.group(1))

        # Extract description (what it feeds)
        desc_patterns = [
            r'((?:MECH|IT|NETWORK|BYPASS|RECIRC|CHILLER|SOURCE|UPS|RACK)\s*[\w\s\-\.]+)',
        ]
        for dp in desc_patterns:
            desc_match = re.search(dp, context)
            if desc_match:
                entry.description = desc_match.group(1).strip()[:60]
                break

        entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
#  Panel Schedule Extraction
# ---------------------------------------------------------------------------

def _extract_from_schedule(text: str, page_num: int) -> list[ScheduleEntry]:
    """Extract breaker entries from panel schedule page text.

    Format typically:
        DESCRIPTION
        Q{n}
        INCOMING/OUTGOING
        {poles}P {amps}A {kAIC}kA
        FIXED/PLUGIN/WITHDRAWABLE
        BREAKER MODEL {model}
    """
    entries = []

    # Split into blocks by Q-designation
    # Pattern: Q followed by number, optionally with letter suffix or comma-separated
    q_blocks = re.split(r'(?=\bQ\d+[A-Z]?\b)', text)

    for block in q_blocks:
        if not block.strip():
            continue

        # Extract Q-designation
        q_match = re.match(r'(Q\d+[A-Z]?(?:\s*[,+]\s*Q\d+[A-Z]?)*)', block)
        if not q_match:
            continue

        q_desig = q_match.group(1).strip()
        # If it's a range like "Q4,Q5,Q6" take the first one
        first_q = re.match(r'(Q\d+[A-Z]?)', q_desig).group(1) if re.match(r'Q\d+', q_desig) else q_desig

        context = block[:500]
        context_lower = context.lower()

        entry = ScheduleEntry(
            q_designation=first_q,
            page_number=page_num,
            source="schedule",
            raw_text=context[:200],
        )

        # Feed type
        if "incoming" in context_lower:
            entry.feed_type = "INCOMING"
        elif "outgoing" in context_lower:
            entry.feed_type = "OUTGOING"
        elif "sub-outgoing" in context_lower:
            entry.feed_type = "SUB-OUTGOING"

        # Poles + Amps + kA pattern: "4P 1000A 85kA" or "3P 60A 65kA"
        rating_match = re.search(r'(\d)[pP]\s+(\d{2,5})\s*[aA]\s+(\d{2,3})\s*(?:ka|kA)', context)
        if rating_match:
            entry.poles = int(rating_match.group(1))
            entry.frame_amps = int(rating_match.group(2))
            entry.trip_amps = entry.frame_amps  # Default same; may be overridden below
            entry.kaic = int(rating_match.group(3))

        # Breaker model
        model_match = re.search(r'(E\d\.\d\s*[HNSLV]?|XT\d+[HNSLBC]?)\s*(\d{2,5})?', context)
        if model_match:
            entry.breaker_model = model_match.group(1).strip()
            if model_match.group(2):
                model_frame = int(model_match.group(2))
                # Model frame might differ from rating line frame (this IS the frame)
                if not entry.frame_amps:
                    entry.frame_amps = model_frame

        # Mounting
        if "withdrawable" in context_lower or "drawout" in context_lower:
            entry.mounting = "WITHDRAWABLE"
        elif "plug-in" in context_lower or "plugin" in context_lower:
            entry.mounting = "PLUG-IN"
        elif "fixed" in context_lower:
            entry.mounting = "FIXED"

        # Trip unit
        trip_unit_match = re.search(r'(EKIP\s+\w+(?:\s+\w+){0,3}|TMD|TMA|TMF|TBD)', context, re.IGNORECASE)
        if trip_unit_match:
            entry.trip_unit = trip_unit_match.group(1).strip()

        # Description (what it feeds/is)
        desc_patterns = [
            r'((?:MECH|IT|NETWORK|BYPASS|RECIRC|CHILLER|SOURCE|UPS|RACK|PUMP|FAN)\s*[\w\s\-\.]*)',
            r'((?:INCOMING|OUTGOING))\s*\n?\s*([\w\s\-\.]+)',
        ]
        for dp in desc_patterns:
            desc_match = re.search(dp, context)
            if desc_match:
                entry.description = desc_match.group(0).strip()[:60]
                break

        entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _normalize_q(q: str) -> Optional[str]:
    """Normalize Q-designation for comparison."""
    if not q:
        return None
    # Extract just the Q number: Q1, Q7, Q14A, etc.
    m = re.match(r'(Q\d+[A-Z]?)', q.upper().strip())
    return m.group(1) if m else None


def _normalize_model(model: str) -> Optional[str]:
    """Normalize breaker model for comparison."""
    if not model:
        return None
    # Remove spaces: "E6.2 H" → "E6.2H", "XT7H" stays "XT7H"
    return re.sub(r'\s+', '', model.upper().strip())
