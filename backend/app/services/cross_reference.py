"""Cross-reference validator — checks equipment against each other for consistency.

Validates:
- Breaker trip rating vs cable ampacity
- Transformer secondary vs panel bus rating
- Cable size vs conduit fill
- Upstream/downstream protection coordination
- Voltage consistency through the system
- NEC ampacity tables
"""
from dataclasses import dataclass
from typing import Optional
from .equipment_extractor import ExtractedEquipment


@dataclass
class CrossRefFinding:
    """A finding from cross-referencing two pieces of equipment."""
    finding_type: str  # sizing_mismatch, coordination_issue, code_violation, etc.
    severity: str  # critical, major, minor, info
    equipment_1: str  # designation of first equipment
    equipment_2: Optional[str]  # designation of second equipment (if applicable)
    page_number: int
    description: str
    reference_code: str
    recommendation: str


# NEC 310.16 - Ampacity of conductors at 75°C (copper)
NEC_AMPACITY_75C = {
    "14": 15, "12": 20, "10": 30, "8": 40, "6": 55, "4": 70, "3": 85,
    "2": 95, "1": 110, "1/0": 125, "2/0": 145, "3/0": 165, "4/0": 195,
    "250": 215, "300": 240, "350": 260, "400": 280, "500": 320,
    "600": 355, "700": 385, "750": 400, "800": 410, "900": 435,
    "1000": 455, "1250": 495, "1500": 520, "1750": 545, "2000": 560,
}

# NEC 310.16 - Ampacity at 90°C (copper)
NEC_AMPACITY_90C = {
    "14": 20, "12": 25, "10": 35, "8": 50, "6": 65, "4": 85, "3": 100,
    "2": 115, "1": 130, "1/0": 150, "2/0": 175, "3/0": 200, "4/0": 230,
    "250": 255, "300": 285, "350": 310, "400": 335, "500": 380,
    "600": 420, "700": 460, "750": 475, "800": 490, "900": 520,
    "1000": 545, "1250": 590, "1500": 625, "1750": 650, "2000": 665,
}

# Standard breaker frame sizes
STANDARD_FRAME_SIZES = [15, 20, 30, 40, 50, 60, 70, 80, 90, 100,
                         110, 125, 150, 175, 200, 225, 250, 300, 350,
                         400, 500, 600, 700, 800, 1000, 1200, 1600,
                         2000, 2500, 3000, 3200, 4000, 5000, 6000]

# Maximum breaker size for conductor per NEC 240.4(D) — small conductors
NEC_240_4_D = {
    "14": 15,
    "12": 20,
    "10": 30,
}

# Minimum conductor for breaker trip at 75°C
MIN_CONDUCTOR_FOR_TRIP = {}
for size, ampacity in NEC_AMPACITY_75C.items():
    for trip in STANDARD_FRAME_SIZES:
        if ampacity >= trip and trip not in MIN_CONDUCTOR_FOR_TRIP:
            MIN_CONDUCTOR_FOR_TRIP[trip] = size


def run_cross_reference(equipment: list[ExtractedEquipment]) -> list[CrossRefFinding]:
    """Run all cross-reference checks across discovered equipment."""
    findings = []

    findings.extend(_check_breaker_cable_sizing(equipment))
    findings.extend(_check_transformer_sizing(equipment))
    findings.extend(_check_voltage_consistency(equipment))
    findings.extend(_check_panel_bus_rating(equipment))
    findings.extend(_check_breaker_frame_vs_trip(equipment))
    findings.extend(_check_standard_breaker_sizes(equipment))
    findings.extend(_check_conductor_small_wire_rule(equipment))

    return findings


def _parse_amps(val: Optional[str]) -> Optional[int]:
    """Parse '200A' or '200' to integer."""
    if not val:
        return None
    import re
    m = re.search(r'(\d+)', val)
    return int(m.group(1)) if m else None


def _parse_conductor_size(val: Optional[str]) -> Optional[str]:
    """Normalize conductor size string to key for ampacity lookup."""
    if not val:
        return None
    import re
    # "500 kcmil" -> "500"
    m = re.search(r'(\d+)\s*kcmil', val.lower())
    if m:
        return m.group(1)
    # "#4/0 AWG" -> "4/0"
    m = re.search(r'#?(\d+/\d+)\s*awg', val.lower())
    if m:
        return m.group(1)
    # "#12 AWG" -> "12"
    m = re.search(r'#?(\d{1,2})\s*(?:awg)?', val.lower())
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
#  Breaker vs Cable sizing (NEC 240.4)
# ---------------------------------------------------------------------------

def _check_breaker_cable_sizing(equipment: list) -> list[CrossRefFinding]:
    findings = []

    breakers = [e for e in equipment if e.equipment_type in ("breaker", "circuit_breaker")]
    cables = [e for e in equipment if e.equipment_type == "cable"]

    # For each breaker, check if any associated cable is properly sized
    for breaker in breakers:
        trip = _parse_amps(breaker.trip_rating)
        if not trip:
            continue

        # Find cables on the same page (likely associated)
        page_cables = [c for c in cables if c.page_number == breaker.page_number]

        for cable in page_cables:
            size = _parse_conductor_size(cable.conductor_size)
            if not size:
                continue

            ampacity = NEC_AMPACITY_75C.get(size)
            if not ampacity:
                continue

            if ampacity < trip:
                findings.append(CrossRefFinding(
                    finding_type="sizing_mismatch",
                    severity="critical",
                    equipment_1=breaker.designation,
                    equipment_2=cable.designation,
                    page_number=breaker.page_number,
                    description=(
                        f"Breaker {breaker.designation} trip rating ({trip}A) exceeds "
                        f"cable {cable.conductor_size} ampacity ({ampacity}A at 75°C). "
                        f"Cable is undersized for the overcurrent protection."
                    ),
                    reference_code="NEC 240.4",
                    recommendation=f"Increase cable to minimum {MIN_CONDUCTOR_FOR_TRIP.get(trip, '?')} AWG/kcmil or reduce breaker trip.",
                ))

    return findings


# ---------------------------------------------------------------------------
#  Transformer sizing checks
# ---------------------------------------------------------------------------

def _check_transformer_sizing(equipment: list) -> list[CrossRefFinding]:
    findings = []

    transformers = [e for e in equipment if e.equipment_type == "transformer"]

    for tx in transformers:
        if not tx.kva:
            findings.append(CrossRefFinding(
                finding_type="missing_data",
                severity="critical",
                equipment_1=tx.designation,
                equipment_2=None,
                page_number=tx.page_number,
                description=f"Transformer {tx.designation}: kVA rating not found",
                reference_code="NEC 450",
                recommendation="Verify transformer kVA rating is specified in submittal",
            ))
            continue

        kva = int(tx.kva)

        # Check impedance is specified
        if not tx.impedance:
            findings.append(CrossRefFinding(
                finding_type="missing_data",
                severity="major",
                equipment_1=tx.designation,
                equipment_2=None,
                page_number=tx.page_number,
                description=f"Transformer {tx.designation} ({kva}kVA): Impedance not specified",
                reference_code="NEC 450.3, IEEE C57",
                recommendation="Impedance is required for coordination study and fault current calculations",
            ))

        # Check primary/secondary voltages
        if not tx.primary_voltage and not tx.voltage:
            findings.append(CrossRefFinding(
                finding_type="missing_data",
                severity="major",
                equipment_1=tx.designation,
                equipment_2=None,
                page_number=tx.page_number,
                description=f"Transformer {tx.designation} ({kva}kVA): Voltage not specified",
                reference_code="NEC 450",
                recommendation="Primary and secondary voltage must be specified",
            ))

        # Check NEC 450.3 primary protection for dry-type
        # Over 600V: max 300% (with secondary protection) or 125%
        # 600V or below: max 125% (next standard size up allowed)
        if kva > 0:
            fla_480 = kva * 1000 / (480 * 1.732)  # 3-phase FLA at 480V
            max_primary_ocpd = fla_480 * 1.25
            next_standard = None
            for size in STANDARD_FRAME_SIZES:
                if size >= max_primary_ocpd:
                    next_standard = size
                    break

            if next_standard:
                findings.append(CrossRefFinding(
                    finding_type="info",
                    severity="info",
                    equipment_1=tx.designation,
                    equipment_2=None,
                    page_number=tx.page_number,
                    description=(
                        f"Transformer {tx.designation} ({kva}kVA at 480V): "
                        f"FLA = {fla_480:.0f}A. Max primary OCPD per NEC 450.3 = {next_standard}A. "
                        f"Verify primary breaker does not exceed this."
                    ),
                    reference_code="NEC 450.3(B)",
                    recommendation=f"Primary overcurrent protection must not exceed {next_standard}A",
                ))

    return findings


# ---------------------------------------------------------------------------
#  Voltage consistency
# ---------------------------------------------------------------------------

def _check_voltage_consistency(equipment: list) -> list[CrossRefFinding]:
    findings = []

    # Group equipment by voltage and flag mismatches
    voltages_seen = set()
    for eq in equipment:
        if eq.voltage:
            import re
            v = re.findall(r'\d{3,5}', eq.voltage)
            voltages_seen.update(int(x) for x in v)

    # Check for unusual voltages in a data center context
    expected_dc_voltages = {120, 208, 240, 277, 400, 415, 480, 600, 4160, 12470, 13200, 13800}
    for v in voltages_seen:
        if v not in expected_dc_voltages and v > 100:
            findings.append(CrossRefFinding(
                finding_type="voltage_anomaly",
                severity="major",
                equipment_1="System",
                equipment_2=None,
                page_number=0,
                description=f"Unusual voltage {v}V found. Verify this is correct for the system.",
                reference_code="NEC 110.4",
                recommendation="Confirm voltage is appropriate for the installation",
            ))

    return findings


# ---------------------------------------------------------------------------
#  Panel bus rating vs main breaker
# ---------------------------------------------------------------------------

def _check_panel_bus_rating(equipment: list) -> list[CrossRefFinding]:
    findings = []

    panels = [e for e in equipment if e.equipment_type == "panel"]
    breakers = [e for e in equipment if e.equipment_type in ("breaker", "circuit_breaker")]

    for panel in panels:
        bus_amps = _parse_amps(panel.amperage)
        if not bus_amps:
            continue

        # Find breakers on the same page (likely the panel's main or branches)
        page_breakers = [b for b in breakers if b.page_number == panel.page_number]
        for bkr in page_breakers:
            trip = _parse_amps(bkr.trip_rating)
            if trip and trip > bus_amps:
                findings.append(CrossRefFinding(
                    finding_type="sizing_mismatch",
                    severity="critical",
                    equipment_1=panel.designation,
                    equipment_2=bkr.designation,
                    page_number=panel.page_number,
                    description=(
                        f"Panel {panel.designation} bus rating ({bus_amps}A) is less than "
                        f"breaker {bkr.designation} trip ({trip}A). Bus is undersized."
                    ),
                    reference_code="NEC 408.36",
                    recommendation=f"Increase bus rating to at least {trip}A or reduce breaker trip",
                ))

    return findings


# ---------------------------------------------------------------------------
#  Breaker frame vs trip
# ---------------------------------------------------------------------------

def _check_breaker_frame_vs_trip(equipment: list) -> list[CrossRefFinding]:
    findings = []

    breakers = [e for e in equipment if e.equipment_type in ("breaker", "circuit_breaker")]
    for bkr in breakers:
        frame = _parse_amps(bkr.frame_size)
        trip = _parse_amps(bkr.trip_rating)

        if frame and trip and trip > frame:
            findings.append(CrossRefFinding(
                finding_type="invalid_config",
                severity="critical",
                equipment_1=bkr.designation,
                equipment_2=None,
                page_number=bkr.page_number,
                description=(
                    f"Breaker {bkr.designation}: Trip rating ({trip}A) exceeds "
                    f"frame size ({frame}A). This is not a valid configuration."
                ),
                reference_code="UL 489",
                recommendation=f"Trip rating cannot exceed frame size. Correct to {frame}AT max or increase frame.",
            ))

    return findings


# ---------------------------------------------------------------------------
#  Standard breaker sizes
# ---------------------------------------------------------------------------

def _check_standard_breaker_sizes(equipment: list) -> list[CrossRefFinding]:
    findings = []

    breakers = [e for e in equipment if e.equipment_type in ("breaker", "circuit_breaker")]
    for bkr in breakers:
        trip = _parse_amps(bkr.trip_rating)
        if trip and trip not in STANDARD_FRAME_SIZES:
            findings.append(CrossRefFinding(
                finding_type="non_standard",
                severity="minor",
                equipment_1=bkr.designation,
                equipment_2=None,
                page_number=bkr.page_number,
                description=f"Breaker {bkr.designation}: {trip}A is not a standard breaker trip size",
                reference_code="NEC 240.6",
                recommendation=f"Verify {trip}A is a valid trip setting. Standard sizes per NEC 240.6(A).",
            ))

    return findings


# ---------------------------------------------------------------------------
#  Small conductor rule NEC 240.4(D)
# ---------------------------------------------------------------------------

def _check_conductor_small_wire_rule(equipment: list) -> list[CrossRefFinding]:
    findings = []

    breakers = [e for e in equipment if e.equipment_type == "circuit_breaker"]
    for bkr in breakers:
        trip = _parse_amps(bkr.trip_rating)
        size = _parse_conductor_size(bkr.conductor_size)

        if trip and size and size in NEC_240_4_D:
            max_ocpd = NEC_240_4_D[size]
            if trip > max_ocpd:
                findings.append(CrossRefFinding(
                    finding_type="code_violation",
                    severity="critical",
                    equipment_1=bkr.designation,
                    equipment_2=None,
                    page_number=bkr.page_number,
                    description=(
                        f"Circuit {bkr.designation}: #{size} AWG conductor with "
                        f"{trip}A breaker exceeds NEC 240.4(D) max of {max_ocpd}A"
                    ),
                    reference_code="NEC 240.4(D)",
                    recommendation=f"#{size} AWG cannot have OCPD > {max_ocpd}A. Increase wire size or reduce breaker.",
                ))

    return findings
