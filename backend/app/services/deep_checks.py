"""Deeper equipment-level checks that catch specific engineering issues.

These checks go beyond cross-referencing to find:
- Missing data on specific device types (UPS without frame/trip specified)
- Equipment discrepancies (3 chillers with different ratings)
- Missing designations (ATS without normal/emergency source label)
- Metering location mismatches
- Sequential naming gaps (UIB A, B, C — where's D?)
- Missing phase color identification
"""
import re
from collections import Counter, defaultdict
from typing import Optional

from .cross_reference import CrossRefFinding
from .equipment_extractor import ExtractedEquipment
from .sld_schedule_crosscheck import ScheduleEntry


def run_deep_equipment_checks(
    equipment: list[ExtractedEquipment],
    sld_entries: list[ScheduleEntry],
    schedule_entries: list[ScheduleEntry],
    pages: list[dict],
) -> list[CrossRefFinding]:
    """Run all deep equipment-level checks."""
    findings = []
    full_text = "\n".join(p.get("text_lower", "") for p in pages)

    findings.extend(_check_ups_breaker_details(sld_entries, schedule_entries))
    findings.extend(_check_identical_equipment_discrepancies(equipment, pages))
    findings.extend(_check_ats_source_designation(pages))
    findings.extend(_check_metering_location(sld_entries, schedule_entries, pages))
    findings.extend(_check_sequential_naming_gaps(sld_entries))
    findings.extend(_check_phase_color_identification(full_text, pages))
    findings.extend(_check_missing_device_details(sld_entries))

    return findings


def _check_ups_breaker_details(sld_entries: list, schedule_entries: list) -> list[CrossRefFinding]:
    """Flag UPS input/output/battery breakers that don't have frame size and trip specified."""
    findings = []

    ups_keywords = ["ups", "uib", "uob", "uic", "uid", "battery", "bypass"]

    for entry in sld_entries + schedule_entries:
        desc = (entry.description or "").lower()
        raw = (entry.raw_text or "").lower()

        is_ups_related = any(kw in desc or kw in raw for kw in ups_keywords)
        if not is_ups_related:
            continue

        if not entry.frame_amps and not entry.trip_amps:
            findings.append(CrossRefFinding(
                finding_type="missing_ups_detail",
                severity="major",
                equipment_1=entry.q_designation,
                equipment_2=None,
                page_number=entry.page_number,
                description=(
                    f"Page {entry.page_number}: UPS-related breaker {entry.q_designation} "
                    f"({entry.breaker_model or 'model TBD'}) — frame size and trip setting "
                    f"not specified. UPS input, output, and DC battery breakers must have "
                    f"frame and trip ratings documented."
                ),
                reference_code="Submittal Requirements",
                recommendation="Show frame size and trip setting for all UPS input, output, and battery breakers.",
            ))

    return findings


def _check_identical_equipment_discrepancies(equipment: list, pages: list) -> list[CrossRefFinding]:
    """Flag groups of identical equipment (e.g., 3 chillers) with different ratings."""
    findings = []

    # Group equipment by type keywords (chiller, pump, fan, rack, etc.)
    groups = defaultdict(list)
    for eq in equipment:
        raw = (eq.raw_text or "").lower()
        for keyword in ["chiller", "pump", "fan coil", "rack", "power shelf"]:
            if keyword in raw:
                groups[keyword].append(eq)
                break

    for group_name, items in groups.items():
        if len(items) < 2:
            continue

        # Check if ratings differ among items that should be identical
        kva_values = [eq.kva for eq in items if eq.kva]
        amp_values = [eq.amperage for eq in items if eq.amperage]

        if kva_values and len(set(kva_values)) > 1:
            vals = ", ".join(f"{v}kVA (pg {eq.page_number})" for eq, v in zip(items, kva_values) if eq.kva)
            findings.append(CrossRefFinding(
                finding_type="equipment_discrepancy",
                severity="major",
                equipment_1=f"{group_name.title()} group",
                equipment_2=None,
                page_number=items[0].page_number,
                description=(
                    f"{len(items)} {group_name}s found with different kVA ratings: {vals}. "
                    f"If these are identical units, ratings should match. "
                    f"Clarify the discrepancy."
                ),
                reference_code="Drawing Consistency",
                recommendation=f"Verify whether all {group_name}s are identical. If so, ratings must match.",
            ))

    # Also check Sn= values from the SLD for same equipment types
    full_text = "\n".join(p.get("text_lower", "") for p in pages)
    sn_by_type = defaultdict(list)

    for page_data in pages:
        if page_data.get("page_type") != "single_line_diagram":
            continue
        text = page_data.get("text_lower", "")
        # Find "CHILLER1 Sn=415.44" and "CHILLER2 Sn=416.67" patterns
        for match in re.finditer(r'(chiller|pump|fan)\s*(\d+)\s*\n?\s*sn\s*=\s*(\d+\.?\d*)', text):
            eq_type = match.group(1)
            eq_num = match.group(2)
            sn_val = match.group(3)
            sn_by_type[eq_type].append((eq_num, float(sn_val), page_data["page"]))

    for eq_type, entries in sn_by_type.items():
        if len(entries) < 2:
            continue
        values = set(v for _, v, _ in entries)
        if len(values) > 1:
            detail = ", ".join(f"{eq_type}{n}: {v}kVA" for n, v, _ in entries)
            findings.append(CrossRefFinding(
                finding_type="equipment_discrepancy",
                severity="major",
                equipment_1=f"{eq_type.title()} group",
                equipment_2=None,
                page_number=entries[0][2],
                description=(
                    f"SLD shows {len(entries)} {eq_type}s with different Sn ratings: {detail}. "
                    f"If identical units, why the discrepancy?"
                ),
                reference_code="Drawing Consistency",
                recommendation=f"Clarify whether {eq_type}s are identical. Different ratings may affect sizing.",
            ))

    return findings


def _check_ats_source_designation(pages: list) -> list[CrossRefFinding]:
    """Flag ATS devices that don't clearly identify which source is normal vs emergency."""
    findings = []

    for page_data in pages:
        text_lower = page_data.get("text_lower", "")
        if "ats" not in text_lower and "transfer switch" not in text_lower:
            continue

        has_normal = any(kw in text_lower for kw in ["normal source", "normal supply", "preferred source"])
        has_emergency = any(kw in text_lower for kw in ["emergency source", "alternate source", "standby source", "generator"])

        if ("ats" in text_lower or "transfer switch" in text_lower) and not (has_normal and has_emergency):
            # Only flag on SLD/schedule pages, not cut sheets
            if page_data.get("page_type") in ("single_line_diagram", "panel_schedule", "equipment_schedule"):
                findings.append(CrossRefFinding(
                    finding_type="ats_source_unclear",
                    severity="major",
                    equipment_1="ATS",
                    equipment_2=None,
                    page_number=page_data["page"],
                    description=(
                        f"Page {page_data['page']}: ATS/transfer switch referenced but normal "
                        f"and emergency sources not clearly designated. Which source is normal "
                        f"(utility or generator)? This affects NEC 700/701/702 classification."
                    ),
                    reference_code="NEC 700.5, 701.5",
                    recommendation="Clearly label which source is normal and which is emergency/standby.",
                ))
                break  # Only flag once

    return findings


def _check_metering_location(sld_entries: list, schedule_entries: list, pages: list) -> list[CrossRefFinding]:
    """Flag metering/PQM location differences between SLD and schedules."""
    findings = []

    # Find meter references on SLD
    sld_meters = []
    for entry in sld_entries:
        raw = (entry.raw_text or "").lower()
        if any(kw in raw for kw in ["meter", "pqm", "pm 8210", "pm8210", "measuring"]):
            sld_meters.append(entry)

    # Find meter references in schedules
    sched_meters = []
    for entry in schedule_entries:
        raw = (entry.raw_text or "").lower()
        if any(kw in raw for kw in ["meter", "pqm", "pm 8210", "pm8210", "measuring"]):
            sched_meters.append(entry)

    # Check if meters are mentioned but location not shown
    full_text = "\n".join(p.get("text_lower", "") for p in pages)
    has_pqm_ref = "pqm" in full_text or "power quality meter" in full_text or "pm 8210" in full_text

    if has_pqm_ref:
        # Check if PQM location is specified on any drawing page
        pqm_on_drawing = False
        for page_data in pages:
            if page_data.get("page_type") in ("single_line_diagram", "plan_drawing"):
                text = page_data.get("text_lower", "")
                if "pqm" in text or "pm 8210" in text or "power quality" in text:
                    pqm_on_drawing = True
                    break

        if not pqm_on_drawing:
            findings.append(CrossRefFinding(
                finding_type="pqm_location_missing",
                severity="major",
                equipment_1="PQM/Power Quality Meters",
                equipment_2=None,
                page_number=0,
                description=(
                    "Power quality meters (PQM) are referenced in the submittal but "
                    "their physical locations are not shown on any drawing. "
                    "Show PQM locations on the SLD and/or layout drawings."
                ),
                reference_code="Submittal Requirements",
                recommendation="Show PQM locations on drawings. Verify meter locations match the SLD.",
            ))

    return findings


def _check_sequential_naming_gaps(sld_entries: list) -> list[CrossRefFinding]:
    """Detect gaps in sequential naming (UIB A, B, C — where's D?)."""
    findings = []

    # Group by prefix pattern
    prefix_groups = defaultdict(list)
    for entry in sld_entries:
        raw = (entry.raw_text or "").upper()
        # Look for patterns like "UIB A", "UIB B", "UOA", "UOB"
        for match in re.finditer(r'(U[IO][A-Z])\s*([A-Z])\b', raw):
            prefix = match.group(1)
            suffix = match.group(2)
            prefix_groups[prefix].append(suffix)

    for prefix, suffixes in prefix_groups.items():
        unique = sorted(set(suffixes))
        if len(unique) < 2:
            continue

        # Check for gaps: if we have A, B, C but no D in a set of 4
        expected = [chr(ord('A') + i) for i in range(ord(unique[-1]) - ord('A') + 1)]
        missing = [c for c in expected if c not in unique]

        if missing:
            findings.append(CrossRefFinding(
                finding_type="naming_gap",
                severity="major",
                equipment_1=f"{prefix} series",
                equipment_2=None,
                page_number=sld_entries[0].page_number if sld_entries else 0,
                description=(
                    f"Sequential naming gap: {prefix} has designations "
                    f"{', '.join(unique)} but is missing {', '.join(missing)}. "
                    f"Verify if {prefix} {', '.join(missing)} should exist or if this is a labeling error."
                ),
                reference_code="Drawing Consistency",
                recommendation=f"Clarify whether {prefix} {', '.join(missing)} is intentionally omitted.",
            ))

    return findings


def _check_phase_color_identification(full_text: str, pages: list) -> list[CrossRefFinding]:
    """Check if phase color identification / conductor taping is specified."""
    findings = []

    has_phase_colors = any(kw in full_text for kw in [
        "phase color", "conductor color", "tape color", "color code",
        "brown black grey", "red blue black",  # Common color schemes
        "phase identification", "conductor identification",
    ])

    if not has_phase_colors:
        findings.append(CrossRefFinding(
            finding_type="missing_phase_colors",
            severity="minor",
            equipment_1="System",
            equipment_2=None,
            page_number=0,
            description=(
                "Phase conductor color identification / taping scheme not specified in submittal. "
                "For US installation: NEC 210.5 requires means of identification for ungrounded conductors. "
                "Common US scheme: Phase A=Black, B=Red, C=Blue (208/120V) or A=Brown, B=Orange, C=Yellow (480/277V)."
            ),
            reference_code="NEC 210.5",
            recommendation="Add notes specifying phase color coding per project standards.",
        ))

    return findings


def _check_missing_device_details(sld_entries: list) -> list[CrossRefFinding]:
    """Flag breakers on the SLD that have a model but no frame/trip specified."""
    findings = []

    for entry in sld_entries:
        if entry.breaker_model and not entry.frame_amps:
            findings.append(CrossRefFinding(
                finding_type="missing_device_rating",
                severity="major",
                equipment_1=entry.q_designation,
                equipment_2=None,
                page_number=entry.page_number,
                description=(
                    f"SLD Page {entry.page_number}: Breaker {entry.q_designation} "
                    f"({entry.breaker_model}) — frame size not specified on the SLD. "
                    f"All breakers must show frame size and trip rating."
                ),
                reference_code="Drawing Standards",
                recommendation="Show frame size and trip rating for every breaker on the SLD.",
            ))

    return findings
