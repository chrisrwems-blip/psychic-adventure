"""System model — structured representation of what a submittal actually describes.

Instead of running 500 keyword checks against raw text, we build a model of the
electrical system and reason against it. The model answers questions like:
- What's the service entrance rating?
- Which breakers are >= 1200A?
- Is there a transformer, and does it have impedance specified?
- What's the system voltage and jurisdiction?

The model is built from already-extracted data (equipment, topology, page types,
jurisdiction). No new parsing — just structured reasoning over existing extraction.
"""
from dataclasses import dataclass, field
from typing import Optional
import re

from .equipment_extractor import ExtractedEquipment
from .topology import SystemTopology, TopologyNode
from .page_classifier import PageType
from .engineering_tables import (
    NEC_310_16_75C, NEC_310_16_75C_AL, NEC_240_4_D, STANDARD_BREAKER_SIZES,
    NEC_250_122, mm2_ampacity, transformer_fla, transformer_max_primary_ocpd,
    transformer_max_secondary_ocpd, transformer_secondary_fault_current,
    voltage_drop_3ph, CONDUCTOR_RESISTANCE_CU_STEEL,
)


# ---------------------------------------------------------------------------
#  System Model
# ---------------------------------------------------------------------------

@dataclass
class ServiceEntrance:
    """The main service — utility connection point."""
    designation: str
    rating_amps: Optional[int] = None
    voltage: Optional[int] = None
    interrupting_kA: Optional[int] = None
    model: Optional[str] = None
    has_ground_fault_protection: bool = False
    trip_unit_type: Optional[str] = None  # LSI, LSIG, etc.


@dataclass
class Breaker:
    """A circuit breaker in the system."""
    designation: str
    equipment_type: str  # "breaker", "circuit_breaker"
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    frame_amps: Optional[int] = None
    trip_amps: Optional[int] = None
    poles: Optional[int] = None
    interrupting_kA: Optional[int] = None
    trip_unit_type: Optional[str] = None  # LSI, LSIG, etc.
    is_service_entrance: bool = False
    feeds_description: Optional[str] = None
    page_number: int = 0
    raw_text: str = ""


@dataclass
class Transformer:
    """A transformer in the system."""
    designation: str
    kva: Optional[float] = None
    primary_voltage: Optional[int] = None
    secondary_voltage: Optional[int] = None
    impedance_pct: Optional[float] = None
    k_factor: Optional[str] = None
    winding_config: Optional[str] = None
    is_feeding_it_loads: bool = False
    page_number: int = 0


@dataclass
class Cable:
    """A cable/feeder in the system."""
    designation: str
    conductor_size: Optional[str] = None  # "#6 AWG", "500 kcmil", "50mm2"
    conductor_size_normalized: Optional[str] = None  # "6", "500", etc. for table lookup
    size_mm2: Optional[float] = None
    is_metric: bool = False
    material: Optional[str] = None  # copper, aluminum
    insulation: Optional[str] = None
    length_ft: Optional[int] = None
    runs: int = 1  # parallel runs
    breaker_amps: Optional[int] = None  # the breaker protecting this cable
    ampacity: Optional[int] = None  # looked up from NEC/IEC tables
    page_number: int = 0


@dataclass
class SystemModel:
    """Structured model of the electrical system described in a submittal."""

    # What the document is about
    document_scope: set = field(default_factory=set)  # {"switchgear", "panelboard", "transformer", ...}
    page_types_found: dict = field(default_factory=dict)  # PageType -> count

    # System-level properties
    system_voltage: Optional[int] = None  # 480, 208, 400, etc.
    frequency: Optional[int] = None  # 50 or 60
    jurisdiction: str = "unknown"  # "NEC", "IEC", "MIXED"
    jurisdiction_confidence: float = 0.0

    # Service entrance
    service_entrances: list = field(default_factory=list)  # list[ServiceEntrance]

    # Equipment
    breakers: list = field(default_factory=list)  # list[Breaker]
    transformers: list = field(default_factory=list)  # list[Transformer]
    cables: list = field(default_factory=list)  # list[Cable]

    # Topology
    topology: Optional[SystemTopology] = None

    # Panels (bus ratings)
    panels: list = field(default_factory=list)  # list of dicts with designation, bus_amps, page

    # Document quality flags
    has_afc_label: bool = False
    has_arc_flash_reference: bool = False
    has_voltage_label: bool = False
    has_coordination_study_reference: bool = False
    has_phase_color_id: bool = False
    has_fuses: bool = False
    has_fuse_schedule: bool = False
    has_ul_listing: bool = False
    has_iec_only: bool = False
    unconfirmed_items: list = field(default_factory=list)  # ["INTERLOCKING TBC", ...]

    # Raw counts for context
    total_equipment_count: int = 0
    total_pages: int = 0


# ---------------------------------------------------------------------------
#  Model Builder
# ---------------------------------------------------------------------------

def build_system_model(
    equipment: list[ExtractedEquipment],
    topology: SystemTopology,
    pages: list[dict],
    page_summary: dict,
    jurisdiction_result=None,
    global_metadata: dict = None,
) -> SystemModel:
    """Build a SystemModel from already-extracted data.

    No new text parsing — this is pure structured reasoning over existing extraction.
    """
    model = SystemModel()
    model.topology = topology
    model.total_equipment_count = len(equipment)
    model.total_pages = len(pages)
    model.page_types_found = page_summary

    # --- Jurisdiction ---
    if jurisdiction_result:
        model.jurisdiction = jurisdiction_result.code
        model.jurisdiction_confidence = jurisdiction_result.confidence

    # --- System voltage and frequency from metadata ---
    if global_metadata:
        voltages = global_metadata.get("voltages_found", [])
        # Pick the most likely system voltage
        for v in [480, 400, 415, 208, 240, 600]:
            if v in voltages:
                model.system_voltage = v
                model.has_voltage_label = True
                break

        freq = global_metadata.get("frequency")
        if freq:
            model.frequency = freq

    # --- Document scope: what equipment types are actually present ---
    for eq in equipment:
        model.document_scope.add(eq.equipment_type)

    # --- Build breaker list ---
    for eq in equipment:
        if eq.equipment_type in ("breaker", "circuit_breaker"):
            b = Breaker(
                designation=eq.designation,
                equipment_type=eq.equipment_type,
                model=eq.model,
                manufacturer=eq.manufacturer,
                frame_amps=_parse_int(eq.frame_size or eq.amperage),
                trip_amps=_parse_int(eq.trip_rating),
                poles=_parse_int(eq.poles),
                interrupting_kA=_parse_int(eq.interrupting_rating),
                page_number=eq.page_number,
                raw_text=eq.raw_text,
            )

            # Detect trip unit type from raw text (LSI vs LSIG)
            raw_lower = (eq.raw_text or "").lower()
            if "lsig" in raw_lower:
                b.trip_unit_type = "LSIG"
            elif "lsi" in raw_lower:
                b.trip_unit_type = "LSI"

            # Detect service entrance
            if any(kw in raw_lower for kw in ["incoming", "incomer", "mains", "source", "utility"]):
                b.is_service_entrance = True

            # Detect what it feeds
            feeds_match = re.search(
                r'(?:to|feeds?|for)\s+([\w\s\-\.]+)',
                eq.raw_text or "", re.IGNORECASE
            )
            if feeds_match:
                b.feeds_description = feeds_match.group(1).strip()[:60]

            model.breakers.append(b)

    # --- Service entrances ---
    for b in model.breakers:
        if b.is_service_entrance:
            se = ServiceEntrance(
                designation=b.designation,
                rating_amps=b.frame_amps,
                voltage=model.system_voltage,
                interrupting_kA=b.interrupting_kA,
                model=b.model,
                trip_unit_type=b.trip_unit_type,
                has_ground_fault_protection=(b.trip_unit_type == "LSIG"),
            )
            model.service_entrances.append(se)

    # --- Transformers ---
    for eq in equipment:
        if eq.equipment_type == "transformer":
            tx = Transformer(
                designation=eq.designation,
                kva=_parse_float(eq.kva),
                primary_voltage=_parse_int(eq.primary_voltage or eq.voltage),
                secondary_voltage=_parse_int(eq.secondary_voltage),
                impedance_pct=_parse_float(eq.impedance),
                page_number=eq.page_number,
            )
            # Detect K-factor from raw text
            raw_lower = (eq.raw_text or "").lower()
            k_match = re.search(r'k[-\s]?(\d+)', raw_lower)
            if k_match:
                tx.k_factor = f"K-{k_match.group(1)}"

            # Detect if feeding IT loads
            if any(kw in raw_lower for kw in ["it ", "rack", "server", "gpu", "compute"]):
                tx.is_feeding_it_loads = True

            model.transformers.append(tx)

    # --- Cables ---
    for eq in equipment:
        if eq.equipment_type == "cable":
            c = Cable(
                designation=eq.designation,
                conductor_size=eq.conductor_size,
                is_metric="mm" in (eq.conductor_size or "").lower(),
                material=eq.conductor_material,
                insulation=eq.insulation_type,
                page_number=eq.page_number,
            )
            # Parse runs
            runs = eq.attributes.get("runs")
            if runs:
                c.runs = int(runs)

            # Parse length
            length_match = re.search(r'(\d+)\s*(?:ft|feet|\')', (eq.raw_text or ""))
            if length_match:
                c.length_ft = int(length_match.group(1))

            # Normalize conductor size and look up ampacity
            if c.conductor_size:
                c.conductor_size_normalized = _normalize_conductor_size(c.conductor_size)
                if c.is_metric:
                    mm2 = eq.attributes.get("size_mm2")
                    if mm2:
                        c.size_mm2 = float(mm2)
                        c.ampacity = mm2_ampacity(c.size_mm2)
                elif c.conductor_size_normalized and c.conductor_size_normalized in NEC_310_16_75C:
                    c.ampacity = NEC_310_16_75C[c.conductor_size_normalized]

            # Parse breaker amps from raw text
            bkr_match = re.search(r'breaker[:\s]*(\d+)\s*a', (eq.raw_text or "").lower())
            if bkr_match:
                c.breaker_amps = int(bkr_match.group(1))

            model.cables.append(c)

    # --- Panels ---
    for eq in equipment:
        if eq.equipment_type == "panel":
            bus_amps = _parse_int(eq.amperage)
            if bus_amps:
                model.panels.append({
                    "designation": eq.designation,
                    "bus_amps": bus_amps,
                    "page": eq.page_number,
                })

    # --- Document-level flags from full text ---
    full_text_lower = "\n".join(p.get("text_lower", "") for p in pages)

    model.has_afc_label = any(kw in full_text_lower for kw in [
        "available fault current", "afc label", "nec 110.24",
    ])

    model.has_arc_flash_reference = any(kw in full_text_lower for kw in [
        "arc flash", "arc-flash", "incident energy", "ieee 1584", "nfpa 70e",
    ])

    model.has_coordination_study_reference = any(kw in full_text_lower for kw in [
        "coordination study", "selective coordination", "time-current",
    ])

    model.has_phase_color_id = any(kw in full_text_lower for kw in [
        "phase color", "conductor color", "tape color", "color code",
        "brown black grey", "red blue black", "phase identification",
    ])

    model.has_fuses = any(kw in full_text_lower for kw in [
        "fuse", "hrc", " gr ", " gg ", "fuse link", "fuse holder",
    ])
    model.has_fuse_schedule = any(kw in full_text_lower for kw in [
        "fuse schedule", "fuse size", "fuse rating", "fuse type",
    ])

    # UL listing check for cut sheet pages
    ul_keywords = ["ul listed", "ul recognized", "ul file", "ul 489", "ul 891",
                   "ul 67", "ul 1558", "ul 1778", "ul 1008", "culus", "c-ul"]
    iec_only_keywords = ["iec 61439", "iec 60947", "iec 60898", "ce marking", "ce mark"]
    model.has_ul_listing = any(kw in full_text_lower for kw in ul_keywords)
    model.has_iec_only = (any(kw in full_text_lower for kw in iec_only_keywords)
                          and not model.has_ul_listing)

    # Detect unconfirmed items (TBC, TBD, TBA)
    for match in re.finditer(r'(\b[\w\s]{3,30})\s+(TBC|TBD|TBA)\b', full_text_lower, re.IGNORECASE):
        item = match.group(0).strip()
        if len(item) > 5:
            model.unconfirmed_items.append(item.upper())

    return model


# ---------------------------------------------------------------------------
#  Model-Aware Checks
# ---------------------------------------------------------------------------

@dataclass
class ModelFinding:
    """A finding from model-based reasoning."""
    check_id: str
    severity: str  # "critical", "major", "minor", "info"
    description: str
    reference: str  # NEC article, standard
    equipment_ref: str = ""  # Which equipment this applies to
    page_number: int = 0


def check_model(model: SystemModel) -> list[ModelFinding]:
    """Run all model-aware checks. Only checks relevant to what's in the document."""
    findings = []

    if _has_switchgear(model):
        findings.extend(_check_service_entrance(model))
        findings.extend(_check_large_breakers(model))
        findings.extend(_check_breaker_ratings(model))
        findings.extend(_check_breaker_coordination(model))
        findings.extend(_check_fault_current_adequacy(model))

    if _has_transformers(model):
        findings.extend(_check_transformers(model))

    if _has_cables(model):
        findings.extend(_check_cable_ampacity(model))
        findings.extend(_check_small_wire_rule(model))
        findings.extend(_check_voltage_drop(model))

    findings.extend(_check_document_completeness(model))
    findings.extend(_check_jurisdiction_issues(model))
    findings.extend(_check_unconfirmed_items(model))

    return findings


def _has_switchgear(model: SystemModel) -> bool:
    return "breaker" in model.document_scope or "panel" in model.document_scope


def _has_transformers(model: SystemModel) -> bool:
    return "transformer" in model.document_scope


def _has_cables(model: SystemModel) -> bool:
    return "cable" in model.document_scope


# ---------------------------------------------------------------------------
#  Service Entrance Checks
# ---------------------------------------------------------------------------

def _check_service_entrance(model: SystemModel) -> list[ModelFinding]:
    """NEC requirements for the service entrance."""
    findings = []

    for se in model.service_entrances:
        # NEC 230.95 — GFP required for 480Y/277V services >= 1000A
        if (se.rating_amps and se.rating_amps >= 1000 and
                model.system_voltage in (480, None) and  # None = voltage not stated, assume 480 for DC
                not se.has_ground_fault_protection):

            # Check if it's LSI (no G) vs LSIG (has G)
            if se.trip_unit_type == "LSI":
                detail = (f"{se.designation} ({se.rating_amps}A) — trip unit is {se.trip_unit_type} "
                          f"(no ground fault). NEC 230.95 requires GFP for services >= 1000A at "
                          f"480Y/277V. Trip unit should be LSIG or a separate GFP relay is needed.")
            else:
                detail = (f"{se.designation} ({se.rating_amps}A) — no ground fault protection "
                          f"documented. NEC 230.95 requires GFP for services >= 1000A at 480Y/277V.")

            findings.append(ModelFinding(
                check_id="MODEL-GFP",
                severity="critical",
                description=detail,
                reference="NEC 230.95",
                equipment_ref=se.designation,
            ))

        # NEC 110.9 — interrupting rating must be specified
        if not se.interrupting_kA:
            findings.append(ModelFinding(
                check_id="MODEL-AIC",
                severity="critical",
                description=(f"{se.designation} ({se.rating_amps or '?'}A) — no interrupting "
                             f"rating (kAIC) specified. Cannot verify NEC 110.9 compliance. "
                             f"If available fault current exceeds the breaker's interrupting "
                             f"rating, the breaker will fail catastrophically during a fault."),
                reference="NEC 110.9",
                equipment_ref=se.designation,
            ))

    return findings


# ---------------------------------------------------------------------------
#  Large Breaker Checks (>= 1200A)
# ---------------------------------------------------------------------------

def _check_large_breakers(model: SystemModel) -> list[ModelFinding]:
    """NEC 240.87 — arc energy reduction for breakers >= 1200A."""
    findings = []

    for b in model.breakers:
        amps = b.frame_amps or b.trip_amps
        if not amps or amps < 1200:
            continue

        # Check for arc energy reduction in raw text
        raw_lower = b.raw_text.lower()
        has_arc_reduction = any(kw in raw_lower for kw in [
            "zsi", "zone selective", "maintenance mode", "maintenance switch",
            "arc reduction", "arc-reduction", "instantaneous override",
        ])

        if not has_arc_reduction and not model.has_arc_flash_reference:
            findings.append(ModelFinding(
                check_id="MODEL-ARC240.87",
                severity="major",
                description=(f"{b.designation} ({amps}A) — NEC 240.87 requires arc energy "
                             f"reduction for breakers >= 1200A. No ZSI, maintenance mode, "
                             f"or arc reduction means documented."),
                reference="NEC 240.87",
                equipment_ref=b.designation,
                page_number=b.page_number,
            ))

    return findings


# ---------------------------------------------------------------------------
#  Breaker Rating Checks
# ---------------------------------------------------------------------------

def _check_breaker_ratings(model: SystemModel) -> list[ModelFinding]:
    """Check breaker ratings for obvious issues."""
    findings = []

    for b in model.breakers:
        # Trip > frame
        if b.frame_amps and b.trip_amps and b.trip_amps > b.frame_amps:
            findings.append(ModelFinding(
                check_id="MODEL-TRIP-FRAME",
                severity="critical",
                description=(f"{b.designation} — trip ({b.trip_amps}A) exceeds frame "
                             f"({b.frame_amps}A). Physically impossible configuration."),
                reference="Equipment spec",
                equipment_ref=b.designation,
                page_number=b.page_number,
            ))

        # ABB frame size validation
        if b.model:
            issue = _validate_abb_frame(b.model, b.frame_amps)
            if issue:
                findings.append(ModelFinding(
                    check_id="MODEL-ABB",
                    severity="major",
                    description=f"{b.designation} — {issue}",
                    reference="ABB Tmax XT Product Data",
                    equipment_ref=b.designation,
                    page_number=b.page_number,
                ))

    return findings


def _validate_abb_frame(model: str, frame_amps: Optional[int]) -> Optional[str]:
    """Validate ABB breaker model against frame size limits."""
    if not frame_amps:
        return None

    # ABB Tmax XT frame limits
    xt_limits = {"XT1": 125, "XT2": 125, "XT3": 225, "XT4": 250,
                 "XT5": 600, "XT6": 800, "XT7": 1200}

    model_upper = model.upper().replace(" ", "")
    for prefix, max_amps in xt_limits.items():
        if model_upper.startswith(prefix) and frame_amps > max_amps:
            return (f"{model} specified at {frame_amps}A but {prefix} frame "
                    f"maximum is {max_amps}A. This product doesn't exist.")

    return None


# ---------------------------------------------------------------------------
#  Transformer Checks
# ---------------------------------------------------------------------------

def _check_transformers(model: SystemModel) -> list[ModelFinding]:
    findings = []

    for tx in model.transformers:
        # Missing impedance — can't calculate secondary fault current
        if tx.kva and not tx.impedance_pct:
            findings.append(ModelFinding(
                check_id="MODEL-TX-IMP",
                severity="critical",
                description=(f"{tx.designation} ({tx.kva}kVA) — no impedance (%Z) specified. "
                             f"Cannot calculate secondary fault current. Without %Z, downstream "
                             f"breaker AIC ratings cannot be verified."),
                reference="NEC 110.9, IEEE C57.12",
                equipment_ref=tx.designation,
                page_number=tx.page_number,
            ))

        # Impedance plausibility
        if tx.impedance_pct:
            if tx.impedance_pct < 2.0:
                findings.append(ModelFinding(
                    check_id="MODEL-TX-IMP-LOW",
                    severity="major",
                    description=(f"{tx.designation} — {tx.impedance_pct}%Z is unusually low. "
                                 f"Results in very high secondary fault current. Typical range 3-6%."),
                    reference="IEEE C57.12",
                    equipment_ref=tx.designation,
                    page_number=tx.page_number,
                ))
            elif tx.impedance_pct > 12.0:
                findings.append(ModelFinding(
                    check_id="MODEL-TX-IMP-HIGH",
                    severity="major",
                    description=(f"{tx.designation} — {tx.impedance_pct}%Z is unusually high. "
                                 f"Will cause excessive voltage drop under load. Typical range 3-6%."),
                    reference="IEEE C57.12",
                    equipment_ref=tx.designation,
                    page_number=tx.page_number,
                ))

        # NEC 450.3(B) — transformer protection sizing
        if tx.kva and tx.primary_voltage:
            pri_fla = transformer_fla(tx.kva, tx.primary_voltage)
            max_pri = transformer_max_primary_ocpd(tx.kva, tx.primary_voltage, False)

            # Check if any breaker on the same page is oversized for this transformer
            for b in model.breakers:
                if not b.frame_amps:
                    continue
                # Only match if breaker is on same page or feeds this transformer
                feeds_tx = (b.feeds_description and
                            tx.designation.lower() in (b.feeds_description or "").lower())
                same_page = (b.page_number == tx.page_number)
                if not (feeds_tx or same_page):
                    continue
                # Check if breaker is plausibly the primary OCPD (within 50-300% of FLA)
                if not (pri_fla * 0.5 < b.frame_amps < pri_fla * 3):
                    continue

                if b.frame_amps > max_pri:
                    findings.append(ModelFinding(
                        check_id="MODEL-TX-450.3",
                        severity="critical",
                        description=(f"{tx.designation} ({tx.kva}kVA, {tx.primary_voltage}V primary) — "
                                     f"FLA = {pri_fla:.0f}A. NEC 450.3(B) max primary OCPD = "
                                     f"{max_pri}A. Breaker {b.designation} at {b.frame_amps}A exceeds "
                                     f"this limit. Transformer is unprotected."),
                        reference="NEC 450.3(B)",
                        equipment_ref=tx.designation,
                        page_number=tx.page_number,
                    ))
                break  # Only flag once per transformer

        # Secondary fault current info (if we have kVA + impedance)
        if tx.kva and tx.impedance_pct and tx.secondary_voltage:
            sec_afc = transformer_secondary_fault_current(
                tx.kva, tx.secondary_voltage, tx.impedance_pct) / 1000  # kA
            if sec_afc > 25:
                findings.append(ModelFinding(
                    check_id="MODEL-TX-AFC",
                    severity="info",
                    description=(f"{tx.designation} ({tx.kva}kVA, {tx.impedance_pct}%Z) — "
                                 f"estimated secondary fault current: {sec_afc:.0f}kA. "
                                 f"All downstream equipment must be rated ≥{sec_afc:.0f}kA."),
                    reference="NEC 110.9",
                    equipment_ref=tx.designation,
                    page_number=tx.page_number,
                ))

        # IT loads without K-factor
        if tx.is_feeding_it_loads and not tx.k_factor:
            findings.append(ModelFinding(
                check_id="MODEL-TX-KFACTOR",
                severity="major",
                description=(f"{tx.designation} feeds IT/compute loads but no K-factor rating "
                             f"specified. Non-linear loads (GPU servers, UPS rectifiers) generate "
                             f"harmonics that cause additional heating. Recommend K-13 minimum, "
                             f"K-20 for dedicated IT distribution."),
                reference="IEEE C57.110",
                equipment_ref=tx.designation,
                page_number=tx.page_number,
            ))

    return findings


# ---------------------------------------------------------------------------
#  Breaker Coordination (Topology-Aware)
# ---------------------------------------------------------------------------

def _check_breaker_coordination(model: SystemModel) -> list[ModelFinding]:
    """Selective coordination — downstream must trip before upstream."""
    findings = []
    if not model.topology:
        return findings

    for node_id, node in model.topology.nodes.items():
        if not node.downstream_ids or not node.amperage:
            continue
        upstream_amps = node.amperage

        for child_id in node.downstream_ids:
            child = model.topology.nodes.get(child_id)
            if not child or not child.amperage:
                continue
            downstream_amps = child.amperage

            if downstream_amps >= upstream_amps and upstream_amps >= 100:
                ratio = upstream_amps / downstream_amps if downstream_amps > 0 else 0
                findings.append(ModelFinding(
                    check_id="MODEL-COORD",
                    severity="critical",
                    description=(f"{child_id} ({downstream_amps}A) fed from {node_id} "
                                 f"({upstream_amps}A) — downstream rating equals or exceeds "
                                 f"upstream. Ratio {ratio:.1f}:1. Selective coordination "
                                 f"extremely difficult. ZSI or fuses required."),
                    reference="NEC 700.32, 701.27",
                    equipment_ref=child_id,
                    page_number=child.page_number,
                ))
            elif 0 < upstream_amps / max(downstream_amps, 1) < 1.5 and upstream_amps >= 400:
                findings.append(ModelFinding(
                    check_id="MODEL-COORD",
                    severity="major",
                    description=(f"{child_id} ({downstream_amps}A) fed from {node_id} "
                                 f"({upstream_amps}A) — ratio {upstream_amps/downstream_amps:.1f}:1 "
                                 f"is tight. Verify selective coordination with TCC curves."),
                    reference="NEC 700.32, 701.27",
                    equipment_ref=child_id,
                    page_number=child.page_number,
                ))

    return findings


# ---------------------------------------------------------------------------
#  Fault Current Adequacy
# ---------------------------------------------------------------------------

def _check_fault_current_adequacy(model: SystemModel) -> list[ModelFinding]:
    """NEC 110.9 — every breaker's AIC must exceed available fault current."""
    findings = []
    if not model.topology:
        return findings

    for b in model.breakers:
        node = model.topology.nodes.get(b.designation)
        if not node:
            continue
        afc = node.available_fault_current_kA
        icu = b.interrupting_kA
        if afc and icu and icu < afc:
            margin = afc - icu
            severity = "critical" if margin > 20 else "major" if margin > 5 else "minor"
            findings.append(ModelFinding(
                check_id="MODEL-AIC-INAD",
                severity=severity,
                description=(f"{b.designation} — interrupting rating {icu}kA is LESS than "
                             f"available fault current {afc:.0f}kA. Breaker cannot safely "
                             f"interrupt a fault. Margin: {margin:.0f}kA deficient."),
                reference="NEC 110.9",
                equipment_ref=b.designation,
                page_number=b.page_number,
            ))

    return findings


# ---------------------------------------------------------------------------
#  Cable Ampacity (NEC 310.16 / IEC 60364)
# ---------------------------------------------------------------------------

def _check_cable_ampacity(model: SystemModel) -> list[ModelFinding]:
    """NEC 240.4 / 310.16 — cable ampacity must match breaker protection."""
    findings = []

    for c in model.cables:
        if not c.ampacity or not c.breaker_amps:
            continue
        total_ampacity = c.ampacity * c.runs

        if total_ampacity < c.breaker_amps:
            table_ref = "IEC 60364" if c.is_metric else "NEC 310.16"
            findings.append(ModelFinding(
                check_id="MODEL-CABLE-SIZE",
                severity="critical",
                description=(f"{c.designation} — {c.conductor_size} "
                             f"({'×' + str(c.runs) + ' runs, ' if c.runs > 1 else ''}"
                             f"{total_ampacity}A ampacity per {table_ref}) on "
                             f"{c.breaker_amps}A breaker. Cable is undersized — will "
                             f"overheat under sustained load."),
                reference=f"NEC 240.4, {table_ref}",
                equipment_ref=c.designation,
                page_number=c.page_number,
            ))

        # Metric cables in NEC jurisdiction warning
        if c.is_metric and model.jurisdiction == "NEC":
            findings.append(ModelFinding(
                check_id="MODEL-CABLE-METRIC",
                severity="major",
                description=(f"{c.designation} — metric conductor ({c.conductor_size}) in NEC "
                             f"jurisdiction. Use IEC 60364 ampacity tables directly. Do NOT "
                             f"convert mm² to AWG for NEC 310.16 lookup."),
                reference="IEC 60364, NEC 310.16",
                equipment_ref=c.designation,
                page_number=c.page_number,
            ))

    return findings


# ---------------------------------------------------------------------------
#  Small Wire Rule (NEC 240.4(D))
# ---------------------------------------------------------------------------

def _check_small_wire_rule(model: SystemModel) -> list[ModelFinding]:
    """NEC 240.4(D) — #14 max 15A, #12 max 20A, #10 max 30A. No exceptions."""
    findings = []

    for c in model.cables:
        if not c.conductor_size_normalized or not c.breaker_amps:
            continue
        max_ocpd = NEC_240_4_D.get(c.conductor_size_normalized)
        if max_ocpd and c.breaker_amps > max_ocpd:
            findings.append(ModelFinding(
                check_id="MODEL-SMALLWIRE",
                severity="critical",
                description=(f"{c.designation} — #{c.conductor_size_normalized} AWG on "
                             f"{c.breaker_amps}A breaker. NEC 240.4(D) limits "
                             f"#{c.conductor_size_normalized} to {max_ocpd}A OCPD maximum. "
                             f"No exceptions."),
                reference="NEC 240.4(D)",
                equipment_ref=c.designation,
                page_number=c.page_number,
            ))

    return findings


# ---------------------------------------------------------------------------
#  Voltage Drop
# ---------------------------------------------------------------------------

def _check_voltage_drop(model: SystemModel) -> list[ModelFinding]:
    """Voltage drop > 3% on feeders is a chronic operational problem."""
    findings = []
    voltage = model.system_voltage or 480

    for c in model.cables:
        if not c.conductor_size_normalized or not c.breaker_amps or not c.length_ft:
            continue
        if c.conductor_size_normalized not in CONDUCTOR_RESISTANCE_CU_STEEL:
            continue

        r_per_1000 = CONDUCTOR_RESISTANCE_CU_STEEL[c.conductor_size_normalized]
        vd_pct = (1.732 * c.length_ft * c.breaker_amps * r_per_1000) / (voltage * 1000) * 100

        if vd_pct > 3.0:
            findings.append(ModelFinding(
                check_id="MODEL-VDROP",
                severity="major" if vd_pct <= 5 else "critical",
                description=(f"{c.designation} — {c.length_ft}ft of #{c.conductor_size_normalized} "
                             f"at {c.breaker_amps}A = {vd_pct:.1f}% voltage drop "
                             f"(NEC recommends <3% for feeders, <5% total). "
                             f"Equipment sees {voltage * (1 - vd_pct/100):.0f}V instead of {voltage}V."),
                reference="NEC 210.19 FPN, 215.2 FPN",
                equipment_ref=c.designation,
                page_number=c.page_number,
            ))


# ---------------------------------------------------------------------------
#  Document Completeness Checks
# ---------------------------------------------------------------------------

def _check_document_completeness(model: SystemModel) -> list[ModelFinding]:
    findings = []

    # Only check AFC labeling if there's switchgear
    if _has_switchgear(model) and not model.has_afc_label:
        findings.append(ModelFinding(
            check_id="MODEL-AFC",
            severity="major",
            description=("Available fault current labeling not found. NEC 110.24(A) requires "
                         "field-applied labels showing available fault current at service equipment."),
            reference="NEC 110.24(A)",
        ))

    # Only check arc flash if there's switchgear with significant ratings
    has_large_gear = any((b.frame_amps or 0) >= 100 for b in model.breakers)
    if has_large_gear and not model.has_arc_flash_reference:
        findings.append(ModelFinding(
            check_id="MODEL-ARCFLASH",
            severity="major",
            description=("No arc flash analysis referenced. NFPA 70E requires arc flash "
                         "labels on all equipment likely to require examination, adjustment, "
                         "or maintenance while energized."),
            reference="NFPA 70E, IEEE 1584",
        ))

    # Voltage label
    if _has_switchgear(model) and not model.has_voltage_label:
        findings.append(ModelFinding(
            check_id="MODEL-VOLTAGE",
            severity="major",
            description=("System voltage not stated on the drawing. Every SLD must clearly "
                         "identify the system voltage to verify equipment voltage class."),
            reference="NEC 408.4",
        ))

    # Phase color identification
    if _has_cables(model) and not model.has_phase_color_id:
        findings.append(ModelFinding(
            check_id="MODEL-PHASECOLOR",
            severity="minor",
            description="No phase color identification found. NEC 210.5 requires phase identification.",
            reference="NEC 210.5",
        ))

    # Fuses without fuse schedule
    if model.has_fuses and not model.has_fuse_schedule:
        findings.append(ModelFinding(
            check_id="MODEL-FUSESCHED",
            severity="major",
            description="Fuses referenced but no fuse schedule found. Fuse sizes, types, and coordination must be documented.",
            reference="Submittal Requirements",
        ))

    # Coordination study
    has_large_system = any((b.frame_amps or 0) >= 800 for b in model.breakers)
    if has_large_system and not model.has_coordination_study_reference:
        findings.append(ModelFinding(
            check_id="MODEL-COORDSTUDY",
            severity="major",
            description="No coordination study referenced. Systems with breakers ≥800A should have a coordination study to verify selective coordination.",
            reference="NEC 700.32, IEEE 242",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Jurisdiction / Listing Issues
# ---------------------------------------------------------------------------

def _check_jurisdiction_issues(model: SystemModel) -> list[ModelFinding]:
    """NEC 110.2, 110.3 — equipment must be listed for the jurisdiction."""
    findings = []

    # IEC-only equipment in NEC jurisdiction
    if model.has_iec_only and model.jurisdiction == "NEC":
        findings.append(ModelFinding(
            check_id="MODEL-LISTING",
            severity="critical",
            description=("IEC certification found but no UL listing. NEC 110.2 and 110.3 require "
                         "all equipment to be approved (listed by an NRTL such as UL). "
                         "IEC 60947 / CE marking alone is NOT acceptable for US installation."),
            reference="NEC 110.2, 110.3",
        ))

    # Mixed jurisdiction warning
    if model.jurisdiction == "MIXED":
        findings.append(ModelFinding(
            check_id="MODEL-JURISDICTION",
            severity="major",
            description=(f"Mixed NEC/IEC signals detected (confidence: {model.jurisdiction_confidence:.0%}). "
                         f"Verify all equipment is listed/certified for the installation jurisdiction."),
            reference="NEC 110.2",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Unconfirmed Items
# ---------------------------------------------------------------------------

def _check_unconfirmed_items(model: SystemModel) -> list[ModelFinding]:
    findings = []

    for item in model.unconfirmed_items:
        # Determine severity based on what's unconfirmed
        item_lower = item.lower()
        if any(kw in item_lower for kw in ["interlock", "protection", "coordination"]):
            severity = "critical"
        else:
            severity = "major"

        findings.append(ModelFinding(
            check_id="MODEL-TBC",
            severity=severity,
            description=f"Unconfirmed item: '{item}' — requires design confirmation before approval.",
            reference="Submittal Requirements",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _normalize_conductor_size(size_str: str) -> Optional[str]:
    """Normalize conductor size string for NEC table lookup.

    '6 AWG' -> '6', '#4/0' -> '4/0', '500 kcmil' -> '500', '250MCM' -> '250'
    """
    if not size_str:
        return None
    s = size_str.upper().replace("#", "").replace("AWG", "").replace("KCMIL", "").replace("MCM", "").strip()
    # Handle x/0 format
    if "/" in s:
        match = re.match(r'(\d/\d)', s)
        if match:
            return match.group(1)
    # Handle plain number
    match = re.match(r'(\d+)', s)
    if match:
        return match.group(1)
    return None


def _parse_int(val) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    try:
        return int(re.sub(r'[^\d]', '', str(val)))
    except (ValueError, TypeError):
        return None


def _parse_float(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(re.sub(r'[^\d.]', '', str(val)))
    except (ValueError, TypeError):
        return None
