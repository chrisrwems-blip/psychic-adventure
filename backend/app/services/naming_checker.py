"""Naming consistency checker — flags inconsistent, missing, or illogical equipment labels.

Checks:
1. Same Q-designation has different descriptive names between SLD and schedules
2. Equipment on SLD with no descriptive label
3. Mixed naming conventions (Q1 vs CB-1 vs BKR-1)
4. Labels that won't make sense in the field
"""
import re
from collections import Counter
from .cross_reference import CrossRefFinding
from .sld_schedule_crosscheck import extract_schedule_entries, ScheduleEntry


def check_naming_consistency(pages: list[dict]) -> list[CrossRefFinding]:
    """Run all naming consistency checks."""
    findings = []

    sld_entries, schedule_entries = extract_schedule_entries(pages)
    all_entries = sld_entries + schedule_entries

    findings.extend(_check_description_consistency(sld_entries, schedule_entries))
    findings.extend(_check_missing_labels(sld_entries, schedule_entries))
    findings.extend(_check_naming_convention(all_entries))
    findings.extend(_check_duplicate_designations(all_entries))

    return findings


def _check_description_consistency(sld_entries: list, schedule_entries: list) -> list[CrossRefFinding]:
    """Flag same Q-number with different descriptions between SLD and schedule."""
    findings = []

    sld_descs = {}
    for e in sld_entries:
        q = _norm_q(e.q_designation)
        if q and e.description:
            sld_descs[q] = (e.description.strip(), e.page_number)

    sched_descs = {}
    for e in schedule_entries:
        q = _norm_q(e.q_designation)
        if q and e.description:
            sched_descs[q] = (e.description.strip(), e.page_number)

    for q in sld_descs:
        if q not in sched_descs:
            continue
        sld_desc, sld_pg = sld_descs[q]
        sched_desc, sched_pg = sched_descs[q]

        # Normalize for comparison
        sld_norm = re.sub(r'\s+', ' ', sld_desc.upper())
        sched_norm = re.sub(r'\s+', ' ', sched_desc.upper())

        if sld_norm != sched_norm and len(sld_norm) > 3 and len(sched_norm) > 3:
            findings.append(CrossRefFinding(
                finding_type="naming_inconsistency",
                severity="major",
                equipment_1=q,
                equipment_2=None,
                page_number=sched_pg,
                description=(
                    f"Breaker {q}: Different descriptions between SLD and schedule. "
                    f"SLD (pg {sld_pg}): \"{sld_desc}\". "
                    f"Schedule (pg {sched_pg}): \"{sched_desc}\". "
                    f"Equipment labels must be consistent across all drawings."
                ),
                reference_code="Drawing Consistency",
                recommendation="Normalize equipment description across SLD and panel schedule.",
            ))

    return findings


def _check_missing_labels(sld_entries: list, schedule_entries: list) -> list[CrossRefFinding]:
    """Flag breakers with Q-designations but no descriptive label.

    Only flag major breakers (>= 400A) missing labels — small branch breakers
    with no label are expected and not worth flagging individually.
    Report as a single finding with a count rather than one per breaker.
    """
    findings = []
    missing = []

    for entry in sld_entries:
        q = _norm_q(entry.q_designation)
        if not q:
            continue
        if not entry.description or len(entry.description.strip()) < 3:
            missing.append((q, entry.frame_amps, entry.page_number))

    # Only flag individually for major breakers (>= 400A)
    major_missing = [(q, a, p) for q, a, p in missing if a and a >= 400]
    for q, amps, page in major_missing:
        findings.append(CrossRefFinding(
            finding_type="missing_label",
            severity="major",
            equipment_1=q,
            equipment_2=None,
            page_number=page,
            description=(
                f"SLD Page {page}: Breaker {q} ({amps}A) has no descriptive label. "
                f"Major equipment should have a logical field label."
            ),
            reference_code="Drawing Standards",
            recommendation="Add descriptive label (e.g., 'MECH UPS FEED', 'SOURCE A INCOMER').",
        ))

    # Summarize small breakers missing labels as one finding
    small_missing = len(missing) - len(major_missing)
    if small_missing > 5:
        findings.append(CrossRefFinding(
            finding_type="missing_label",
            severity="minor",
            equipment_1="Multiple breakers",
            equipment_2=None,
            page_number=0,
            description=(
                f"{small_missing} branch breakers on the SLD have no descriptive labels. "
                f"Consider normalizing naming convention for field identification."
            ),
            reference_code="Drawing Standards",
            recommendation="Add descriptive labels to all breakers for clarity in the field.",
        ))

    return findings


def _check_naming_convention(entries: list) -> list[CrossRefFinding]:
    """Flag mixed naming conventions across the submittal."""
    findings = []

    # Collect all designation styles
    styles = Counter()
    for entry in entries:
        q = entry.q_designation or ""
        if re.match(r'^Q\d+', q):
            styles["Q-number (ABB)"] += 1
        elif re.match(r'^CB[-\s]?\d+', q, re.IGNORECASE):
            styles["CB-number"] += 1
        elif re.match(r'^BKR[-\s]?\d+', q, re.IGNORECASE):
            styles["BKR-number"] += 1
        elif re.match(r'^BR[-\s]?\d+', q, re.IGNORECASE):
            styles["BR-number"] += 1

    if len(styles) > 1:
        style_list = ", ".join(f"{style}: {count}" for style, count in styles.most_common())
        findings.append(CrossRefFinding(
            finding_type="mixed_naming",
            severity="minor",
            equipment_1="All Breakers",
            equipment_2=None,
            page_number=0,
            description=(
                f"Mixed breaker naming conventions detected: {style_list}. "
                f"Recommend standardizing to a single convention for clarity."
            ),
            reference_code="Drawing Standards",
            recommendation="Standardize breaker designations to one convention throughout.",
        ))

    return findings


def _check_duplicate_designations(entries: list) -> list[CrossRefFinding]:
    """Flag duplicate Q-designations with different ratings (possible copy-paste errors)."""
    findings = []

    by_q = {}
    for entry in entries:
        q = _norm_q(entry.q_designation)
        if not q:
            continue
        by_q.setdefault(q, [])
        by_q[q].append(entry)

    for q, dupes in by_q.items():
        if len(dupes) < 2:
            continue

        # Check if ratings differ among duplicates
        frames = set(e.frame_amps for e in dupes if e.frame_amps)
        models = set(e.breaker_model for e in dupes if e.breaker_model)

        if len(frames) > 1:
            frame_list = ", ".join(f"{e.frame_amps}A (pg {e.page_number})" for e in dupes if e.frame_amps)
            findings.append(CrossRefFinding(
                finding_type="duplicate_with_mismatch",
                severity="critical",
                equipment_1=q,
                equipment_2=None,
                page_number=dupes[0].page_number,
                description=(
                    f"Breaker {q} appears with different frame sizes: {frame_list}. "
                    f"Same designation must have same ratings across all drawings."
                ),
                reference_code="Drawing Consistency",
                recommendation="Resolve which frame size is correct and update all references.",
            ))

    return findings


def _norm_q(q: str) -> str:
    if not q:
        return ""
    m = re.match(r'(Q\d+[A-Z]?)', q.upper().strip())
    return m.group(1) if m else ""
