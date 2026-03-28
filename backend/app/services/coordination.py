"""Protection coordination and arc flash analysis.

Equipment-agnostic checks:
1. Selective coordination — upstream breaker must be larger than downstream
2. Trip ratio analysis — flags difficult coordination scenarios
3. ZSI detection — checks if zone-selective interlocking is mentioned
4. Arc flash estimation — simplified IEEE 1584 incident energy calculation
5. Ground fault coordination — main GFP vs feeder GFP settings
"""
import re
import math
from typing import Optional

from .cross_reference import CrossRefFinding
from .topology import SystemTopology
from .equipment_extractor import ExtractedEquipment
from .engineering_tables import transformer_fla


def run_coordination_analysis(
    equipment: list[ExtractedEquipment],
    topology: Optional[SystemTopology],
) -> list[CrossRefFinding]:
    """Run all protection coordination checks."""
    findings = []

    if topology:
        findings.extend(_check_selective_coordination_ratio(topology))
        findings.extend(_check_zsi_requirement(equipment, topology))
        findings.extend(_check_arc_flash_estimate(equipment, topology))
    findings.extend(_check_ground_fault_coordination(equipment))

    return findings


def _parse_amps(val) -> Optional[int]:
    if not val:
        return None
    m = re.search(r'(\d+)', str(val))
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# 1. Selective Coordination Ratio
# ---------------------------------------------------------------------------

def _check_selective_coordination_ratio(topology: SystemTopology) -> list[CrossRefFinding]:
    """Check trip ratios between upstream/downstream breaker pairs.

    Rules of thumb:
    - Ratio > 3:1 — coordination usually achievable with standard trip units
    - Ratio 2:1 to 3:1 — coordination possible but requires careful trip unit selection
    - Ratio < 2:1 — coordination very difficult, may need ZSI or fuses
    """
    findings = []
    pairs = topology.get_breaker_pairs()

    for upstream, downstream in pairs:
        up_amps = upstream.amperage or 0
        down_amps = downstream.amperage or 0

        if up_amps <= 0 or down_amps <= 0:
            continue

        # Skip if downstream is larger (topology error, already caught elsewhere)
        if down_amps >= up_amps:
            continue

        ratio = up_amps / down_amps

        if ratio < 1.5:
            findings.append(CrossRefFinding(
                finding_type="coordination_very_difficult",
                severity="critical",
                equipment_1=upstream.equipment_id,
                equipment_2=downstream.equipment_id,
                page_number=upstream.page_number,
                description=(
                    f"{upstream.equipment_id} ({up_amps}A) → {downstream.equipment_id} ({down_amps}A): "
                    f"ratio {ratio:.1f}:1 — selective coordination extremely difficult. "
                    f"ZSI, differential protection, or fuses required."
                ),
                reference_code="NEC 700.32, 701.27",
                recommendation="Implement ZSI between these devices or consider fuse-breaker coordination.",
            ))
        elif ratio < 2.0:
            findings.append(CrossRefFinding(
                finding_type="coordination_difficult",
                severity="major",
                equipment_1=upstream.equipment_id,
                equipment_2=downstream.equipment_id,
                page_number=upstream.page_number,
                description=(
                    f"{upstream.equipment_id} ({up_amps}A) → {downstream.equipment_id} ({down_amps}A): "
                    f"ratio {ratio:.1f}:1 — selective coordination difficult. "
                    f"Requires careful trip unit selection and possibly ZSI."
                ),
                reference_code="NEC 700.32, 701.27",
                recommendation="Verify coordination study demonstrates selectivity at all fault levels.",
            ))

    return findings


# ---------------------------------------------------------------------------
# 2. ZSI Requirement Detection
# ---------------------------------------------------------------------------

def _check_zsi_requirement(equipment: list, topology: SystemTopology) -> list[CrossRefFinding]:
    """Flag breaker pairs that likely need ZSI but don't mention it."""
    findings = []
    pairs = topology.get_breaker_pairs()

    for upstream, downstream in pairs:
        up_amps = upstream.amperage or 0
        down_amps = downstream.amperage or 0

        if up_amps <= 0 or down_amps <= 0 or down_amps >= up_amps:
            continue

        ratio = up_amps / down_amps

        # Only check if ratio is tight (< 3:1) and upstream is large (>= 800A)
        if ratio >= 3.0 or up_amps < 800:
            continue

        # Check if ZSI is mentioned in either breaker's context
        up_eq = next((e for e in equipment if e.designation == upstream.equipment_id), None)
        down_eq = next((e for e in equipment if e.designation == downstream.equipment_id), None)

        up_text = (up_eq.raw_text or "").lower() if up_eq else ""
        down_text = (down_eq.raw_text or "").lower() if down_eq else ""
        combined = up_text + " " + down_text

        has_zsi = any(kw in combined for kw in ["zsi", "zone selective", "zone-selective"])

        if not has_zsi:
            findings.append(CrossRefFinding(
                finding_type="zsi_recommended",
                severity="major",
                equipment_1=upstream.equipment_id,
                equipment_2=downstream.equipment_id,
                page_number=upstream.page_number,
                description=(
                    f"{upstream.equipment_id} ({up_amps}A) → {downstream.equipment_id} ({down_amps}A): "
                    f"ratio {ratio:.1f}:1 with upstream ≥800A. "
                    f"Zone Selective Interlocking (ZSI) recommended but not found in submittal."
                ),
                reference_code="NEC 240.87, 700.32",
                recommendation="Verify ZSI is provided between these breakers for selective coordination.",
            ))

    return findings


# ---------------------------------------------------------------------------
# 3. Arc Flash Estimation
# ---------------------------------------------------------------------------

def _check_arc_flash_estimate(equipment: list, topology: SystemTopology) -> list[CrossRefFinding]:
    """Estimate arc flash incident energy at key points in the system.

    Simplified calculation based on IEEE 1584-2018 concepts:
    - E ≈ (K × Ibf^1.5 × t) / D^2  (very simplified)
    - Where: K = constant, Ibf = bolted fault kA, t = clearing time (s), D = distance (inches)
    - Working distance: 18" for switchgear, 24" for MCC

    This is an ESTIMATE for flagging high-energy locations, not a replacement
    for a proper arc flash study.
    """
    findings = []

    for node_id, node in topology.nodes.items():
        if node.equipment_type != "breaker":
            continue

        afc_kA = node.available_fault_current_kA
        trip_amps = node.amperage

        if not afc_kA or not trip_amps or afc_kA <= 0:
            continue

        # Estimate clearing time based on breaker size
        # Large breakers (>= 1200A) with electronic trips: ~0.1-0.5s
        # Medium breakers: ~0.05-0.3s
        # Small breakers with instantaneous: ~0.02-0.05s
        if trip_amps >= 1200:
            clearing_time = 0.3  # Conservative for large breaker without ZSI
        elif trip_amps >= 400:
            clearing_time = 0.1
        else:
            clearing_time = 0.05

        # Simplified incident energy: E ≈ 4.184 × K × Ibf × t / D²
        # K ≈ 1.0 for open air, D = 18" for switchgear
        D = 18  # inches
        K = 1.5  # adjustment factor

        # Very simplified IEEE 1584 style:
        # E (cal/cm²) ≈ 4.184 × Cf × En × (t/0.2) × (610/D)^x
        # Simplified to: E ≈ 0.01 × Ibf^1.5 × t × (610/D)^2
        ibf = afc_kA  # in kA
        incident_energy = 0.01 * (ibf ** 1.5) * clearing_time * ((610 / D) ** 1.8) / 100

        # Classify PPE category
        if incident_energy < 1.2:
            ppe = "Cat 0"
        elif incident_energy < 4:
            ppe = "Cat 1"
        elif incident_energy < 8:
            ppe = "Cat 2"
        elif incident_energy < 25:
            ppe = "Cat 3"
        elif incident_energy < 40:
            ppe = "Cat 4"
        else:
            ppe = "DANGEROUS"

        # Only flag locations with significant arc flash risk
        if incident_energy > 8:  # Cat 3 or higher
            severity = "critical" if ppe == "DANGEROUS" else "major"
            findings.append(CrossRefFinding(
                finding_type="arc_flash_high",
                severity=severity,
                equipment_1=node.equipment_id,
                equipment_2=None,
                page_number=node.page_number,
                description=(
                    f"Page {node.page_number}: {node.equipment_id} ({trip_amps}A) — "
                    f"estimated arc flash incident energy ~{incident_energy:.1f} cal/cm² ({ppe}). "
                    f"Based on ~{afc_kA:.0f}kA fault current and {clearing_time}s clearing time. "
                    f"This is an ESTIMATE — actual arc flash study required."
                ),
                reference_code="NFPA 70E, IEEE 1584",
                recommendation=(
                    f"Perform IEEE 1584 arc flash study. If confirmed ≥Cat 3, "
                    f"implement arc energy reduction per NEC 240.87 (ZSI, maintenance switch, etc.)."
                ),
            ))

    return findings


# ---------------------------------------------------------------------------
# 4. Ground Fault Coordination
# ---------------------------------------------------------------------------

def _check_ground_fault_coordination(equipment: list) -> list[CrossRefFinding]:
    """Check that ground fault protection settings are coordinated."""
    findings = []

    # Find equipment with GFP references
    gfp_devices = []
    for eq in equipment:
        raw = (eq.raw_text or "").lower()
        if any(kw in raw for kw in ["ground fault", "gfp", "gfi", "ekip g"]):
            # Try to extract pickup value
            pickup_match = re.search(r'(\d{3,5})\s*a.*?ground\s*fault|ground\s*fault.*?(\d{3,5})\s*a', raw)
            pickup = None
            if pickup_match:
                pickup = int(pickup_match.group(1) or pickup_match.group(2))

            gfp_devices.append({
                "designation": eq.designation,
                "page": eq.page_number,
                "pickup": pickup,
                "amps": _parse_amps(eq.trip_rating or eq.frame_size),
            })

    # If multiple GFP devices, check coordination
    if len(gfp_devices) >= 2:
        # Sort by amperage (largest = main, smaller = feeders)
        gfp_devices.sort(key=lambda d: d["amps"] or 0, reverse=True)
        main = gfp_devices[0]

        for feeder in gfp_devices[1:]:
            if main["pickup"] and feeder["pickup"] and feeder["pickup"] >= main["pickup"]:
                findings.append(CrossRefFinding(
                    finding_type="gfp_coordination",
                    severity="critical",
                    equipment_1=main["designation"],
                    equipment_2=feeder["designation"],
                    page_number=feeder["page"],
                    description=(
                        f"Ground fault protection coordination issue: "
                        f"Main GFP ({main['designation']}) pickup {main['pickup']}A, "
                        f"Feeder GFP ({feeder['designation']}) pickup {feeder['pickup']}A. "
                        f"Feeder pickup must be lower than main for coordination."
                    ),
                    reference_code="NEC 230.95, 240.13",
                    recommendation="Set feeder GFP pickup lower than main GFP and with shorter time delay.",
                ))

    return findings
