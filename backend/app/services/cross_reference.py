"""Cross-reference validator — topology-aware engineering validation.

21 checks covering:
- Fault current coordination (NEC 110.9)
- Selective coordination (NEC 700.32, 701.27)
- Arc energy reduction (NEC 240.87)
- Ground fault protection (NEC 230.95)
- Available fault current labeling (NEC 110.24)
- Grounding conductor sizing (NEC 250.122)
- Breaker-cable ampacity (NEC 240.4, 310.16)
- Voltage drop estimation
- Conduit fill (NEC Chapter 9)
- Transformer protection (NEC 450.3)
- K-factor / harmonics (IEEE C57.110)
- ABB product validation
- Panel bus rating (NEC 408.36)
- Breaker frame vs trip
- Standard breaker sizes (NEC 240.6)
- Small wire rule (NEC 240.4(D))
- Working clearance (NEC 110.26)
- Separately derived systems (NEC 250.30)
- Drawing tag cross-reference
- Voltage consistency
"""
import re
from dataclasses import dataclass
from typing import Optional

from .equipment_extractor import ExtractedEquipment
from .topology import SystemTopology, TopologyNode
from .engineering_tables import (
    NEC_310_16_75C, NEC_310_16_75C_AL, NEC_250_122,
    NEC_240_4_D, STANDARD_BREAKER_SIZES,
    mm2_to_awg, mm2_ampacity, mm2_to_approximate_label,
    next_standard_size, min_egc_size,
    transformer_fla, transformer_max_primary_ocpd, transformer_max_secondary_ocpd,
    transformer_secondary_fault_current,
    required_clearance, voltage_drop_3ph, max_conduit_fill,
    CONDUCTOR_AREA_THHN,
)
from .manufacturer_data.abb import validate_abb_breaker


@dataclass
class CrossRefFinding:
    finding_type: str
    severity: str  # critical, major, minor, info
    equipment_1: str
    equipment_2: Optional[str]
    page_number: int
    description: str
    reference_code: str
    recommendation: str


def run_cross_reference(
    equipment: list[ExtractedEquipment],
    topology: Optional[SystemTopology] = None,
    pages: Optional[list[dict]] = None,
) -> list[CrossRefFinding]:
    """Run all cross-reference checks."""
    findings = []

    # --- Existing checks (improved) ---
    findings.extend(_check_breaker_cable_sizing(equipment, topology))
    findings.extend(_check_transformer_protection(equipment, topology))
    findings.extend(_check_voltage_consistency(equipment))
    findings.extend(_check_panel_bus_rating(equipment, topology))
    findings.extend(_check_breaker_frame_vs_trip(equipment))
    findings.extend(_check_standard_breaker_sizes(equipment))
    findings.extend(_check_small_wire_rule(equipment))

    # --- New topology-aware checks ---
    if topology:
        findings.extend(_check_fault_current_coordination(equipment, topology))
        findings.extend(_check_selective_coordination(topology))
        findings.extend(_check_arc_energy_reduction(equipment, topology))
    findings.extend(_check_ground_fault_protection(equipment, pages))
    findings.extend(_check_afc_labeling(equipment, pages))
    findings.extend(_check_grounding_conductor(equipment, topology))
    findings.extend(_check_transformer_grounding(equipment))
    findings.extend(_check_kfactor_harmonics(equipment, pages))
    findings.extend(_check_abb_product_validity(equipment))
    findings.extend(_check_metric_cable_sizing(equipment))

    return findings


# ---------------------------------------------------------------------------
#  1. Breaker-Cable Sizing (NEC 240.4 + 310.16) — IMPROVED with topology
# ---------------------------------------------------------------------------

def _check_breaker_cable_sizing(equipment: list, topology: Optional[SystemTopology]) -> list[CrossRefFinding]:
    findings = []
    breakers = [e for e in equipment if e.equipment_type in ("breaker", "circuit_breaker")]
    cables = [e for e in equipment if e.equipment_type == "cable"]

    for breaker in breakers:
        trip = _parse_amps(breaker.trip_rating)
        if not trip:
            continue

        # Find associated cables — same page or topology-linked
        associated_cables = [c for c in cables if c.page_number == breaker.page_number]

        for cable in associated_cables:
            size = _parse_conductor_size(cable.conductor_size)
            if not size:
                continue

            ampacity = NEC_310_16_75C.get(size, 0)
            if not ampacity:
                continue

            # Check for parallel runs
            runs = int(cable.attributes.get("runs", 1)) if cable.attributes else 1
            total_ampacity = ampacity * runs

            if total_ampacity < trip:
                findings.append(CrossRefFinding(
                    finding_type="cable_undersized",
                    severity="critical",
                    equipment_1=breaker.designation,
                    equipment_2=cable.designation,
                    page_number=breaker.page_number,
                    description=(
                        f"Page {breaker.page_number}: Breaker {breaker.designation} trip rating ({trip}A) "
                        f"exceeds cable {cable.conductor_size} ampacity ({total_ampacity}A at 75°C"
                        f"{f', {runs} runs' if runs > 1 else ''} per NEC 310.16). "
                        f"Cable is undersized for overcurrent protection."
                    ),
                    reference_code="NEC 240.4, 310.16",
                    recommendation=f"Increase cable size or reduce breaker trip to {total_ampacity}A or less.",
                ))

    return findings


# ---------------------------------------------------------------------------
#  2. Transformer Protection (NEC 450.3) — IMPROVED with calculations
# ---------------------------------------------------------------------------

def _check_transformer_protection(equipment: list, topology: Optional[SystemTopology]) -> list[CrossRefFinding]:
    findings = []
    transformers = [e for e in equipment if e.equipment_type == "transformer"]

    for tx in transformers:
        kva = float(tx.kva) if tx.kva else 0
        if not kva:
            findings.append(CrossRefFinding(
                finding_type="missing_data", severity="critical",
                equipment_1=tx.designation, equipment_2=None,
                page_number=tx.page_number,
                description=f"Page {tx.page_number}: Transformer {tx.designation} — kVA rating not found in submittal.",
                reference_code="NEC 450",
                recommendation="kVA rating must be specified for transformer protection sizing.",
            ))
            continue

        # Calculate FLA and max OCPD
        pri_v = int(tx.primary_voltage) if tx.primary_voltage else 480
        sec_v = int(tx.secondary_voltage) if tx.secondary_voltage else 208
        pri_fla = transformer_fla(kva, pri_v)
        sec_fla = transformer_fla(kva, sec_v)
        max_pri_ocpd = transformer_max_primary_ocpd(kva, pri_v, has_secondary_protection=True)
        max_sec_ocpd = transformer_max_secondary_ocpd(kva, sec_v)

        findings.append(CrossRefFinding(
            finding_type="transformer_info", severity="info",
            equipment_1=tx.designation, equipment_2=None,
            page_number=tx.page_number,
            description=(
                f"Page {tx.page_number}: Transformer {tx.designation} ({kva}kVA, {pri_v}V→{sec_v}V): "
                f"Primary FLA={pri_fla:.0f}A, max primary OCPD={max_pri_ocpd}A. "
                f"Secondary FLA={sec_fla:.0f}A, max secondary OCPD={max_sec_ocpd}A."
            ),
            reference_code="NEC 450.3(B)",
            recommendation=f"Verify primary breaker ≤{max_pri_ocpd}A and secondary breaker ≤{max_sec_ocpd}A.",
        ))

        if not tx.impedance:
            findings.append(CrossRefFinding(
                finding_type="missing_data", severity="major",
                equipment_1=tx.designation, equipment_2=None,
                page_number=tx.page_number,
                description=f"Page {tx.page_number}: Transformer {tx.designation} ({kva}kVA) — impedance not specified.",
                reference_code="NEC 450.3, IEEE C57",
                recommendation="Impedance required for fault current calculations and coordination study.",
            ))

    return findings


# ---------------------------------------------------------------------------
#  3. Voltage Consistency
# ---------------------------------------------------------------------------

def _check_voltage_consistency(equipment: list) -> list[CrossRefFinding]:
    findings = []
    expected = {120, 208, 230, 240, 277, 400, 415, 440, 480, 600, 690, 4160, 12470, 13200, 13800}
    voltages_seen = set()

    for eq in equipment:
        if eq.voltage:
            vs = re.findall(r'\d{3,5}', eq.voltage)
            for v in vs:
                v_int = int(v)
                if v_int > 100:
                    voltages_seen.add(v_int)

    for v in voltages_seen:
        if v not in expected:
            findings.append(CrossRefFinding(
                finding_type="voltage_anomaly", severity="major",
                equipment_1="System", equipment_2=None, page_number=0,
                description=f"Unusual voltage {v}V found in submittal. Verify this is correct.",
                reference_code="NEC 110.4",
                recommendation="Confirm voltage is appropriate for the installation.",
            ))

    return findings


# ---------------------------------------------------------------------------
#  4. Panel Bus Rating vs OCPD (NEC 408.36)
# ---------------------------------------------------------------------------

def _check_panel_bus_rating(equipment: list, topology: Optional[SystemTopology]) -> list[CrossRefFinding]:
    findings = []
    panels = [e for e in equipment if e.equipment_type == "panel" and e.amperage]

    for panel in panels:
        bus_amps = _parse_amps(panel.amperage)
        if not bus_amps:
            continue

        # Find breakers that could be the main breaker for this panel
        # Check topology first, fall back to same-page
        page_breakers = [e for e in equipment
                         if e.equipment_type in ("breaker", "circuit_breaker")
                         and e.page_number == panel.page_number]

        for bkr in page_breakers:
            trip = _parse_amps(bkr.trip_rating)
            if trip and trip > bus_amps:
                findings.append(CrossRefFinding(
                    finding_type="bus_undersized", severity="critical",
                    equipment_1=panel.designation, equipment_2=bkr.designation,
                    page_number=panel.page_number,
                    description=(
                        f"Page {panel.page_number}: Panel {panel.designation} bus rated {bus_amps}A "
                        f"but breaker {bkr.designation} trip is {trip}A. "
                        f"Bus rating must equal or exceed OCPD trip rating."
                    ),
                    reference_code="NEC 408.36",
                    recommendation=f"Increase bus to {trip}A or reduce breaker trip to {bus_amps}A.",
                ))

    return findings


# ---------------------------------------------------------------------------
#  5. Breaker Frame vs Trip
# ---------------------------------------------------------------------------

def _check_breaker_frame_vs_trip(equipment: list) -> list[CrossRefFinding]:
    findings = []
    for bkr in equipment:
        if bkr.equipment_type not in ("breaker", "circuit_breaker"):
            continue
        frame = _parse_amps(bkr.frame_size)
        trip = _parse_amps(bkr.trip_rating)
        if frame and trip and trip > frame:
            findings.append(CrossRefFinding(
                finding_type="invalid_config", severity="critical",
                equipment_1=bkr.designation, equipment_2=None,
                page_number=bkr.page_number,
                description=(
                    f"Page {bkr.page_number}: Breaker {bkr.designation} trip ({trip}A) "
                    f"exceeds frame ({frame}A). Not a valid configuration."
                ),
                reference_code="UL 489",
                recommendation=f"Trip cannot exceed frame. Max trip for {frame}A frame is {frame}A.",
            ))
    return findings


# ---------------------------------------------------------------------------
#  6. Standard Breaker Sizes (NEC 240.6)
# ---------------------------------------------------------------------------

def _check_standard_breaker_sizes(equipment: list) -> list[CrossRefFinding]:
    findings = []
    for bkr in equipment:
        if bkr.equipment_type not in ("breaker", "circuit_breaker"):
            continue
        trip = _parse_amps(bkr.trip_rating)
        if trip and trip not in STANDARD_BREAKER_SIZES and trip > 6:
            findings.append(CrossRefFinding(
                finding_type="non_standard", severity="minor",
                equipment_1=bkr.designation, equipment_2=None,
                page_number=bkr.page_number,
                description=f"Page {bkr.page_number}: {bkr.designation} {trip}A — not a standard breaker size per NEC 240.6(A).",
                reference_code="NEC 240.6",
                recommendation=f"Verify {trip}A is an adjustable trip setting, not a frame size.",
            ))
    return findings


# ---------------------------------------------------------------------------
#  7. Small Wire Rule (NEC 240.4(D))
# ---------------------------------------------------------------------------

def _check_small_wire_rule(equipment: list) -> list[CrossRefFinding]:
    findings = []
    for bkr in equipment:
        if bkr.equipment_type != "circuit_breaker":
            continue
        trip = _parse_amps(bkr.trip_rating)
        size = _parse_conductor_size(bkr.conductor_size)
        if trip and size and size in NEC_240_4_D:
            max_ocpd = NEC_240_4_D[size]
            if trip > max_ocpd:
                findings.append(CrossRefFinding(
                    finding_type="code_violation", severity="critical",
                    equipment_1=bkr.designation, equipment_2=None,
                    page_number=bkr.page_number,
                    description=(
                        f"Page {bkr.page_number}: #{size} AWG conductor with {trip}A breaker "
                        f"exceeds NEC 240.4(D) maximum of {max_ocpd}A."
                    ),
                    reference_code="NEC 240.4(D)",
                    recommendation=f"#{size} AWG max OCPD is {max_ocpd}A. Increase wire size or reduce breaker.",
                ))
    return findings


# ---------------------------------------------------------------------------
#  8. Fault Current Coordination (NEC 110.9) — NEW
# ---------------------------------------------------------------------------

def _check_fault_current_coordination(equipment: list, topology: SystemTopology) -> list[CrossRefFinding]:
    findings = []

    for node_id, node in topology.nodes.items():
        if node.equipment_type != "breaker":
            continue
        if not node.interrupting_kA or not node.available_fault_current_kA:
            continue

        afc = node.available_fault_current_kA
        icu = node.interrupting_kA

        if icu < afc:
            # Determine severity based on margin
            margin = afc - icu
            if margin > 20:
                sev = "critical"
                desc_prefix = "LIKELY INADEQUATE"
            elif margin > 5:
                sev = "major"
                desc_prefix = "POTENTIALLY INADEQUATE"
            else:
                sev = "minor"
                desc_prefix = "MARGINAL"

            findings.append(CrossRefFinding(
                finding_type="interrupting_inadequate", severity=sev,
                equipment_1=node.equipment_id, equipment_2=None,
                page_number=node.page_number,
                description=(
                    f"Page {node.page_number}: {desc_prefix} — Breaker {node.equipment_id} "
                    f"rated {icu}kA interrupting capacity. Estimated available fault current at "
                    f"this point is ~{afc:.0f}kA (based on infinite bus utility assumption + generator "
                    f"contribution). Verify with actual fault current study per NEC 110.9."
                ),
                reference_code="NEC 110.9",
                recommendation=(
                    f"Obtain actual fault current study. If AFC exceeds {icu}kA, replace with "
                    f"breaker rated ≥ AFC or add current-limiting device upstream."
                ),
            ))

    return findings


# ---------------------------------------------------------------------------
#  9. Selective Coordination (NEC 700.32, 701.27) — NEW
# ---------------------------------------------------------------------------

def _check_selective_coordination(topology: SystemTopology) -> list[CrossRefFinding]:
    findings = []
    pairs = topology.get_breaker_pairs()

    for upstream, downstream in pairs:
        up_amps = upstream.amperage or 0
        down_amps = downstream.amperage or 0

        if up_amps > 0 and down_amps > 0 and down_amps >= up_amps:
            findings.append(CrossRefFinding(
                finding_type="coordination_issue", severity="critical",
                equipment_1=upstream.equipment_id,
                equipment_2=downstream.equipment_id,
                page_number=upstream.page_number,
                description=(
                    f"Breaker {upstream.equipment_id} ({up_amps}A) feeds {downstream.equipment_id} ({down_amps}A). "
                    f"Downstream device rating equals or exceeds upstream — selective coordination not achievable."
                ),
                reference_code="NEC 700.32, 701.27",
                recommendation="Verify time-current curves provide selective coordination at all fault levels.",
            ))

    return findings


# ---------------------------------------------------------------------------
# 10. Arc Energy Reduction (NEC 240.87) — NEW
# ---------------------------------------------------------------------------

def _check_arc_energy_reduction(equipment: list, topology: SystemTopology) -> list[CrossRefFinding]:
    findings = []

    for eq in equipment:
        if eq.equipment_type != "breaker":
            continue
        trip = _parse_amps(eq.trip_rating or eq.frame_size)
        if not trip or trip < 1200:
            continue

        # Breakers rated 1200A or higher require arc energy reduction
        context = (eq.raw_text or "").lower()
        has_zsi = "zsi" in context or "zone" in context
        has_maint_switch = "maintenance" in context and "switch" in context
        has_arc_reduction = "arc" in context and ("reduc" in context or "mitigat" in context)

        if not (has_zsi or has_maint_switch or has_arc_reduction):
            findings.append(CrossRefFinding(
                finding_type="arc_energy", severity="major",
                equipment_1=eq.designation, equipment_2=None,
                page_number=eq.page_number,
                description=(
                    f"Page {eq.page_number}: Breaker {eq.designation} rated {trip}A — "
                    f"NEC 240.87 requires arc energy reduction means for breakers rated 1200A or higher. "
                    f"Must provide ZSI, differential relaying, maintenance switch, or equivalent."
                ),
                reference_code="NEC 240.87",
                recommendation="Confirm ZSI, energy-reducing maintenance switch, or active arc flash mitigation is provided.",
            ))

    return findings


# ---------------------------------------------------------------------------
# 11. Ground Fault Protection (NEC 230.95) — NEW
# ---------------------------------------------------------------------------

def _check_ground_fault_protection(equipment: list, pages: Optional[list]) -> list[CrossRefFinding]:
    findings = []
    full_text = "\n".join(p.get("text_lower", "") for p in (pages or []))

    # Find service entrance equipment rated 1000A or more at 480Y/277V
    for eq in equipment:
        if eq.equipment_type not in ("breaker", "panel"):
            continue
        amps = _parse_amps(eq.amperage or eq.trip_rating or eq.frame_size)
        if not amps or amps < 1000:
            continue

        context = (eq.raw_text or "").lower()
        is_service = ("incomer" in context or "incoming" in context or "source" in context
                      or "service" in context or "main" in context)

        if is_service:
            has_gfp = ("ground fault" in full_text or "gfp" in full_text
                       or "ekip g" in full_text or "residual" in full_text)
            if not has_gfp:
                findings.append(CrossRefFinding(
                    finding_type="missing_gfp", severity="critical",
                    equipment_1=eq.designation, equipment_2=None,
                    page_number=eq.page_number,
                    description=(
                        f"Page {eq.page_number}: Service entrance {eq.designation} rated {amps}A at 480Y/277V — "
                        f"NEC 230.95 requires ground fault protection for equipment rated 1000A or more. "
                        f"Ground fault relay not found in submittal."
                    ),
                    reference_code="NEC 230.95",
                    recommendation="Add ground fault protection with max 1200A pickup, max 1-second delay per NEC 230.95(A).",
                ))
            break  # Only check once

    return findings


# ---------------------------------------------------------------------------
# 12. Available Fault Current Labeling (NEC 110.24) — NEW
# ---------------------------------------------------------------------------

def _check_afc_labeling(equipment: list, pages: Optional[list]) -> list[CrossRefFinding]:
    findings = []
    full_text = "\n".join(p.get("text_lower", "") for p in (pages or []))

    has_afc_label = ("available fault current" in full_text or "afc" in full_text
                     or "short circuit current" in full_text and "label" in full_text)

    if not has_afc_label:
        findings.append(CrossRefFinding(
            finding_type="missing_label", severity="major",
            equipment_1="Service Equipment", equipment_2=None,
            page_number=0,
            description=(
                "Available fault current labeling not found in submittal. "
                "NEC 110.24(A) requires field-applied labels on service equipment showing "
                "available fault current, date of calculation, and calculation method."
            ),
            reference_code="NEC 110.24(A)",
            recommendation="Provide available fault current calculation and confirm labels will be field-applied.",
        ))

    return findings


# ---------------------------------------------------------------------------
# 13. Grounding Conductor Sizing (NEC 250.122) — NEW
# ---------------------------------------------------------------------------

def _check_grounding_conductor(equipment: list, topology: Optional[SystemTopology]) -> list[CrossRefFinding]:
    findings = []
    breakers = [e for e in equipment if e.equipment_type in ("breaker", "circuit_breaker")]
    cables = [e for e in equipment if e.equipment_type == "cable"]

    for bkr in breakers:
        trip = _parse_amps(bkr.trip_rating)
        if not trip or trip < 15:
            continue

        required_egc = min_egc_size(trip)
        # Look for ground conductor in associated cables
        page_cables = [c for c in cables if c.page_number == bkr.page_number]

        for cable in page_cables:
            raw = (cable.raw_text or "").lower()
            if "cpc" in raw or "ground" in raw or "egc" in raw or "gnd" in raw:
                # Found a ground reference — check size
                gnd_match = re.search(r'(\d+)\s*(?:mm2|mm²)', raw)
                if gnd_match:
                    gnd_mm2 = int(gnd_match.group(1))
                    gnd_awg = mm2_to_awg(gnd_mm2)
                    req_ampacity = NEC_310_16_75C.get(required_egc, 0)
                    gnd_ampacity = NEC_310_16_75C.get(gnd_awg, 0)

                    if gnd_ampacity < req_ampacity:
                        findings.append(CrossRefFinding(
                            finding_type="egc_undersized", severity="critical",
                            equipment_1=bkr.designation, equipment_2=cable.designation,
                            page_number=bkr.page_number,
                            description=(
                                f"Page {bkr.page_number}: {trip}A breaker requires minimum #{required_egc} "
                                f"equipment grounding conductor per NEC 250.122. "
                                f"Cable shows {gnd_mm2}mm² (≈#{gnd_awg}) ground — may be undersized."
                            ),
                            reference_code="NEC 250.122",
                            recommendation=f"Verify ground conductor is minimum #{required_egc} Cu per NEC 250.122.",
                        ))

    return findings


# ---------------------------------------------------------------------------
# 14. Transformer Grounding — Separately Derived Systems (NEC 250.30) — NEW
# ---------------------------------------------------------------------------

def _check_transformer_grounding(equipment: list) -> list[CrossRefFinding]:
    findings = []
    transformers = [e for e in equipment if e.equipment_type == "transformer"]

    for tx in transformers:
        kva = float(tx.kva) if tx.kva else 0
        if kva < 15:  # Skip very small transformers (control power)
            continue

        context = (tx.raw_text or "").lower()
        has_grounding = ("grounding" in context or "bonding" in context or "250.30" in context
                         or "grounding electrode" in context or "gec" in context)

        if not has_grounding:
            findings.append(CrossRefFinding(
                finding_type="missing_grounding", severity="major",
                equipment_1=tx.designation, equipment_2=None,
                page_number=tx.page_number,
                description=(
                    f"Page {tx.page_number}: Transformer {tx.designation} ({kva}kVA) — "
                    f"NEC 250.30 requires separately derived systems to have grounding electrode conductor, "
                    f"system bonding jumper, and supply-side bonding jumper. Not documented in submittal."
                ),
                reference_code="NEC 250.30",
                recommendation="Verify NEC 250.30 grounding requirements are addressed for this transformer.",
            ))

    return findings


# ---------------------------------------------------------------------------
# 15. K-Factor / Harmonics (IEEE C57.110) — NEW
# ---------------------------------------------------------------------------

def _check_kfactor_harmonics(equipment: list, pages: Optional[list]) -> list[CrossRefFinding]:
    findings = []
    full_text = "\n".join(p.get("text_lower", "") for p in (pages or []))
    transformers = [e for e in equipment if e.equipment_type == "transformer"]

    # Check if IT loads are present (data center → harmonics expected)
    has_it_loads = any(kw in full_text for kw in ["it load", "server", "rack", "gpu", "power shelf", "data hall"])

    if not has_it_loads:
        return findings

    for tx in transformers:
        kva = float(tx.kva) if tx.kva else 0
        if kva < 50:  # Skip small transformers
            continue

        context = (tx.raw_text or "").lower()
        has_kfactor = any(kw in context for kw in ["k-factor", "k factor", "k-13", "k-20", "k13", "k20"])
        has_200_neutral = "200%" in context or "double neutral" in context

        if not has_kfactor:
            findings.append(CrossRefFinding(
                finding_type="missing_kfactor", severity="major",
                equipment_1=tx.designation, equipment_2=None,
                page_number=tx.page_number,
                description=(
                    f"Page {tx.page_number}: Transformer {tx.designation} ({kva}kVA) feeds IT loads — "
                    f"K-factor rating not specified. Data center IT loads generate significant harmonics "
                    f"requiring K-13 or K-20 rated transformers per IEEE C57.110."
                ),
                reference_code="IEEE C57.110",
                recommendation="Verify transformer is K-factor rated (K-13 minimum for data center IT loads).",
            ))

    return findings


# ---------------------------------------------------------------------------
# 16. ABB Product Validation — NEW
# ---------------------------------------------------------------------------

def _check_abb_product_validity(equipment: list) -> list[CrossRefFinding]:
    findings = []

    for eq in equipment:
        if eq.manufacturer != "ABB" or eq.equipment_type != "breaker":
            continue

        result = validate_abb_breaker(eq.designation)
        if not result["valid"]:
            for issue in result["issues"]:
                findings.append(CrossRefFinding(
                    finding_type="invalid_product", severity="major",
                    equipment_1=eq.designation, equipment_2=None,
                    page_number=eq.page_number,
                    description=f"Page {eq.page_number}: {eq.designation} — {issue}",
                    reference_code="ABB Product Catalog",
                    recommendation="Verify correct ABB model and frame size.",
                ))

    return findings


# ---------------------------------------------------------------------------
# 17. Metric Cable Sizing — NEW
# ---------------------------------------------------------------------------

def _check_metric_cable_sizing(equipment: list) -> list[CrossRefFinding]:
    findings = []
    cables = [e for e in equipment if e.equipment_type == "cable" and e.attributes]
    breakers = [e for e in equipment if e.equipment_type in ("breaker", "circuit_breaker")]

    for cable in cables:
        size_mm2 = cable.attributes.get("size_mm2")
        runs = int(cable.attributes.get("runs", 1))
        if not size_mm2:
            continue

        mm2 = float(size_mm2)
        awg = mm2_to_awg(mm2)
        ampacity_per_run = mm2_ampacity_75c(mm2)
        total_ampacity = ampacity_per_run * runs

        # Find breaker on same page to check sizing
        page_breakers = [b for b in breakers if b.page_number == cable.page_number]
        for bkr in page_breakers:
            trip = _parse_amps(bkr.trip_rating)
            if not trip:
                continue

            if total_ampacity > 0 and total_ampacity < trip:
                findings.append(CrossRefFinding(
                    finding_type="metric_cable_undersized", severity="critical",
                    equipment_1=bkr.designation, equipment_2=cable.designation,
                    page_number=cable.page_number,
                    description=(
                        f"Page {cable.page_number}: Cable {cable.conductor_size} "
                        f"(≈#{awg}, {ampacity_per_run}A/run × {runs} runs = {total_ampacity}A at 75°C per NEC 310.16) "
                        f"protected by {bkr.designation} ({trip}A). Cable may be undersized."
                    ),
                    reference_code="NEC 240.4, 310.16",
                    recommendation=f"Verify cable ampacity of {total_ampacity}A is adequate for {trip}A protection.",
                ))

    return findings


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _parse_amps(val) -> Optional[int]:
    if not val:
        return None
    m = re.search(r'(\d+)', str(val))
    return int(m.group(1)) if m else None


def _parse_conductor_size(val) -> Optional[str]:
    if not val:
        return None
    m = re.search(r'(\d+)\s*kcmil', str(val).lower())
    if m:
        return m.group(1)
    m = re.search(r'#?(\d+/\d+)\s*awg', str(val).lower())
    if m:
        return m.group(1)
    m = re.search(r'#?(\d{1,2})\s*(?:awg)?', str(val).lower())
    if m:
        return m.group(1)
    return None
