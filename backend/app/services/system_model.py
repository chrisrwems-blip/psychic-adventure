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

    # Loads (from SLD load designations)
    loads: list = field(default_factory=list)  # list of dicts {designation, description, kva, kw, page}

    # QF designations (from SLD breaker numbering)
    qf_designations: dict = field(default_factory=dict)  # {qf_num: {model, amps, description, ...}}

    # Generator
    generator_kva: Optional[float] = None
    generator_kw: Optional[float] = None

    # Source fault current
    available_fault_current_kA: Optional[float] = None

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
    has_spd_reference: bool = False
    has_neutral_sizing_reference: bool = False
    has_working_clearance_reference: bool = False
    has_grounding_reference: bool = False  # NEC 250.30
    has_energy_storage: bool = False  # batteries, BESS, UPS batteries
    has_thermal_runaway_protection: bool = False
    is_modular_data_center: bool = False  # NEC 646, UL 2755
    unconfirmed_items: list = field(default_factory=list)  # ["INTERLOCKING TBC", ...]

    # Physical dimensions (from extracted text)
    panel_width_mm: Optional[float] = None
    panel_height_mm: Optional[float] = None
    panel_depth_mm: Optional[float] = None
    panel_weight_kg: Optional[float] = None

    # Breaker mounting types found
    withdrawable_breakers: list = field(default_factory=list)
    fixed_breakers: list = field(default_factory=list)
    plugin_breakers: list = field(default_factory=list)

    # Topology patterns detected
    has_dual_mains: bool = False
    has_ups_feed_through: bool = False  # "TO IT" / "FROM IT" pattern
    has_bypass: bool = False
    has_loadbank: bool = False
    has_coupler: bool = False
    mains_count: int = 0
    coupler_count: int = 0

    # Raw counts for context
    total_equipment_count: int = 0
    total_pages: int = 0
    rack_plug_count: int = 0  # number of rack plug circuits


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

    # --- SLD-specific: QF designations, loads, generator, fault current ---
    full_text = "\n".join(p.get("text", "") for p in pages)

    # Parse -QF designations (ABB SLD format)
    for m in re.finditer(r'-QF(\d+)\s+(.*?)(?=-QF|-L\d|\n\n|$)', full_text, re.DOTALL):
        qf_num = int(m.group(1))
        context = m.group(2).strip()[:200]
        model.qf_designations[qf_num] = {
            "raw": context,
            "model": None,
            "amps": None,
            "description": None,
        }
        # Extract breaker model
        bm = re.search(r'(E\d\.\d[HNSLV]?\d*|XT\d+[HMLNSLVBC]*\d*)', context)
        if bm:
            model.qf_designations[qf_num]["model"] = bm.group(1)
        # Extract amps
        am = re.search(r'(?:LSI|LSIG)\s*(\d+)', context)
        if am:
            model.qf_designations[qf_num]["amps"] = int(am.group(1))
        # Extract description (uppercase functional name)
        dm = re.search(r'((?:SOURCE|UPS|MECH|IT|NETWORK|CHILLER|BYPASS|PUMP|RACK|FEED|OSP)\w*(?:\s*\w+)*)', context)
        if dm:
            model.qf_designations[qf_num]["description"] = dm.group(1).strip()[:60]

    # Parse load designations (-L{n})
    for m in re.finditer(r'-L(\d+)\s+(.*?)(?=-L\d|-QF|-WC|$)', full_text, re.DOTALL):
        l_num = int(m.group(1))
        context = m.group(2).strip()[:150]
        load = {"num": l_num, "raw": context, "description": None, "kva": None}
        # Extract Sn= value
        sn = re.search(r'Sn\s*=\s*([\d.]+)\s*\[?kVA\]?', context)
        if sn:
            load["kva"] = float(sn.group(1))
        # Extract description
        desc = re.search(r'(\w[\w\s\-\.]+?)(?:\s+Sn=|$)', context)
        if desc:
            load["description"] = desc.group(1).strip()[:60]
        model.loads.append(load)

    # Generator
    gen_m = re.search(r'-G\d+.*?Sn\s*=\s*([\d.]+)\s*kVA.*?P\s*=\s*([\d.]+)\s*kW', full_text)
    if gen_m:
        model.generator_kva = float(gen_m.group(1))
        model.generator_kw = float(gen_m.group(2))

    # Source fault current
    fc_m = re.search(r'IkLLL\s*[\n\s]*([\d.]+)', full_text)
    if not fc_m:
        fc_m = re.search(r'(\d{2,3})\.\d\s+\d', full_text)  # e.g., "65.0 39.0 39.0"
    if fc_m:
        try:
            model.available_fault_current_kA = float(fc_m.group(1))
        except ValueError:
            pass

    # --- Physical dimensions from text ---
    for pattern, field_name in [
        (r'width\s*[:=]\s*(?:mm\s*)?(\d[\d,\.]+)', "panel_width_mm"),
        (r'height\s*[:=]\s*(?:mm\s*)?(\d[\d,\.]+)', "panel_height_mm"),
        (r'depth\s*[:=]\s*(?:mm\s*)?(\d[\d,\.]+)', "panel_depth_mm"),
        (r'weight\s*[:=]\s*(?:kg\s*)?(\d[\d,\.]+)', "panel_weight_kg"),
    ]:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            try:
                setattr(model, field_name, float(m.group(1).replace(",", "")))
            except ValueError:
                pass

    # --- Breaker mounting types and topology patterns ---
    full_text_combined = full_text.lower()
    for b in model.breakers:
        raw = b.raw_text.lower()
        if "withdrawable" in raw or "withdrawlable" in raw or "drawout" in raw:
            model.withdrawable_breakers.append(b.designation)
        elif "plug" in raw and "in" in raw:
            model.plugin_breakers.append(b.designation)
        elif "fixed" in raw:
            model.fixed_breakers.append(b.designation)

        if b.is_service_entrance:
            model.mains_count += 1

    model.has_dual_mains = model.mains_count >= 2
    model.has_ups_feed_through = ("to it" in full_text_combined and "from it" in full_text_combined)
    model.has_bypass = "bypass" in full_text_combined
    model.has_loadbank = "loadbank" in full_text_combined or "load bank" in full_text_combined
    model.has_coupler = "coupler" in full_text_combined or "tie" in full_text_combined
    model.coupler_count = full_text_combined.count("coupler")

    # Count rack plugs
    rack_match = re.findall(r'(\d+)\s*x\s*.*?rack\s*plug', full_text_combined)
    model.rack_plug_count = sum(int(x) for x in rack_match)

    # --- Document-level flags from full text ---
    full_text_lower = full_text_combined

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

    model.has_spd_reference = any(kw in full_text_lower for kw in [
        "surge protective", "spd", "surge protection", "surge arrester",
        "tvss", "transient voltage",
    ])

    model.has_neutral_sizing_reference = any(kw in full_text_lower for kw in [
        "200% neutral", "double neutral", "oversized neutral",
        "neutral sized for harmonics", "harmonic neutral",
    ])

    model.has_working_clearance_reference = any(kw in full_text_lower for kw in [
        "working clearance", "working space", "110.26",
    ])

    model.has_grounding_reference = any(kw in full_text_lower for kw in [
        "250.30", "separately derived", "system bonding jumper",
        "grounding electrode conductor", "bonding jumper",
    ])

    model.has_energy_storage = any(kw in full_text_lower for kw in [
        "battery", "bess", "energy storage", "lithium", "vrla",
        "li-ion", "lifepo4",
    ])

    model.has_thermal_runaway_protection = any(kw in full_text_lower for kw in [
        "thermal runaway", "nfpa 855", "ul 9540", "deflagration",
        "explosion control",
    ])

    model.is_modular_data_center = any(kw in full_text_lower for kw in [
        "modular data center", "mdc", "prefabricated", "ul 2755",
        "article 646", "nec 646", "factory built",
    ])

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

    findings.extend(_check_leviathan_spec(model))
    findings.extend(_check_abb_model_naming(model))
    findings.extend(_check_qf_designation_issues(model))
    findings.extend(_check_load_accounting(model))
    findings.extend(_check_identical_equipment_ratings(model))
    findings.extend(_check_undefined_loads(model))
    findings.extend(_check_nec_646_modular(model))
    findings.extend(_check_spd_requirements(model))
    findings.extend(_check_neutral_sizing(model))
    findings.extend(_check_terminal_temperature(model))
    findings.extend(_check_working_clearance(model))
    findings.extend(_check_separately_derived_grounding(model))
    findings.extend(_check_energy_storage(model))
    findings.extend(_check_constructability(model))
    findings.extend(_check_thermal(model))
    findings.extend(_check_operations_maintainability(model))
    findings.extend(_check_protection_philosophy(model))
    findings.extend(_check_ups_topology(model))
    findings.extend(_check_cable_routing(model))
    findings.extend(_check_metering_monitoring(model))
    findings.extend(_check_missing_designations(model))
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


def _validate_abb_frame(model_str: str, frame_amps: Optional[int]) -> Optional[str]:
    """Validate ABB breaker model against frame size limits."""
    if not frame_amps:
        return None

    model_upper = model_str.upper().replace(" ", "")

    for prefix, info in ABB_XT_FRAMES.items():
        if model_upper.startswith(prefix) and frame_amps > info["max_amps"]:
            return (f"{model_str} specified at {frame_amps}A but {prefix} frame "
                    f"maximum is {info['max_amps']}A. This product doesn't exist.")

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

# ===========================================================================
#  ENGINEERING REASONING CHECKS
#  These think about whether the equipment will actually work, not just
#  whether it complies with a code article.
# ===========================================================================


# ---------------------------------------------------------------------------
#  Constructability — will it fit, can you install it, can you move it?
# ---------------------------------------------------------------------------

def _check_constructability(model: SystemModel) -> list[ModelFinding]:
    findings = []

    # Leviathan envelope: 13,600mm wide, ~3,600mm electrical zone
    LEVIATHAN_WIDTH_MM = 13600
    LEVIATHAN_ELEC_ZONE_MM = 3600  # approximate

    if model.panel_width_mm:
        # Does the panel fit in the Leviathan?
        if model.panel_width_mm > LEVIATHAN_WIDTH_MM * 0.95:
            findings.append(ModelFinding(
                check_id="ENG-FIT-WIDTH",
                severity="critical",
                description=(f"Panel width {model.panel_width_mm:.0f}mm vs Leviathan width "
                             f"{LEVIATHAN_WIDTH_MM}mm — only {LEVIATHAN_WIDTH_MM - model.panel_width_mm:.0f}mm "
                             f"clearance total. How does it get through the door? Does it ship "
                             f"in sections? What's the assembly sequence on site?"),
                reference="Constructability",
            ))
        elif model.panel_width_mm > LEVIATHAN_WIDTH_MM * 0.85:
            findings.append(ModelFinding(
                check_id="ENG-FIT-WIDTH",
                severity="major",
                description=(f"Panel width {model.panel_width_mm:.0f}mm is {model.panel_width_mm/LEVIATHAN_WIDTH_MM*100:.0f}% "
                             f"of Leviathan width ({LEVIATHAN_WIDTH_MM}mm). Tight fit. "
                             f"Confirm transport sectionalizing, lifting points, and "
                             f"assembly sequence. Verify cable access on both sides."),
                reference="Constructability",
            ))

    if model.panel_depth_mm:
        # NEC 110.26 working clearance vs physical depth
        required_clearance_mm = 1067  # 42 inches = 1067mm for Condition 2 at 480V
        if model.panel_depth_mm + required_clearance_mm > LEVIATHAN_ELEC_ZONE_MM:
            findings.append(ModelFinding(
                check_id="ENG-FIT-DEPTH",
                severity="critical",
                description=(f"Panel depth {model.panel_depth_mm:.0f}mm + NEC 110.26 working clearance "
                             f"{required_clearance_mm}mm = {model.panel_depth_mm + required_clearance_mm:.0f}mm "
                             f"total required. Verify this fits in the electrical plant zone. "
                             f"If rear access is needed, add another {required_clearance_mm}mm."),
                reference="NEC 110.26, Constructability",
            ))

    # No seismic rating on transportable equipment
    if model.is_modular_data_center or model.panel_width_mm:
        has_seismic = any(
            "seismic" in b.raw_text.lower() or "asce" in b.raw_text.lower()
            for b in model.breakers
        )
        if not has_seismic:
            findings.append(ModelFinding(
                check_id="ENG-SEISMIC",
                severity="major",
                description=("No seismic rating specified. Leviathan deploys to unknown sites — "
                             "ASCE 7 seismic requirements vary by location. Switchgear mounting "
                             "method and seismic certification (SDS/SD1) must be documented."),
                reference="IBC/ASCE 7",
            ))

    return findings


# ---------------------------------------------------------------------------
#  Thermal — will it overheat in an enclosed modular unit?
# ---------------------------------------------------------------------------

def _check_thermal(model: SystemModel) -> list[ModelFinding]:
    findings = []

    # Estimate heat dissipation from breakers
    # Rule of thumb: ACB power loss ≈ 0.03% of rated current × voltage per pole
    # For a 4000A ACB at 480V: ~2-4kW per breaker
    total_breaker_amps = sum(b.frame_amps or 0 for b in model.breakers)

    if total_breaker_amps > 5000 and model.panel_depth_mm and model.panel_depth_mm < 1000:
        findings.append(ModelFinding(
            check_id="ENG-THERMAL",
            severity="major",
            description=(f"Total breaker capacity {total_breaker_amps}A in an enclosure "
                         f"{model.panel_depth_mm:.0f}mm deep. Significant heat dissipation "
                         f"in a confined space. Confirm: forced ventilation in switchgear room? "
                         f"Ambient temperature derating applied? Maximum operating temperature "
                         f"for EKIP trip units (typically 70°C)?"),
            reference="IEC 61439-1, IEEE C37.20",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Operations & Maintainability — can someone safely service this?
# ---------------------------------------------------------------------------

def _check_operations_maintainability(model: SystemModel) -> list[ModelFinding]:
    findings = []

    # Fixed breakers on critical IT paths can't be racked out for maintenance
    critical_fixed = []
    for b in model.breakers:
        if b.designation in model.fixed_breakers:
            desc = (b.feeds_description or b.raw_text[:40]).lower()
            if any(kw in desc for kw in ["it", "ups", "mech", "rack", "critical"]):
                critical_fixed.append(b.designation)

    if critical_fixed:
        findings.append(ModelFinding(
            check_id="ENG-MAINT-FIXED",
            severity="major",
            description=(f"Fixed-mount breakers on critical paths: {', '.join(critical_fixed[:5])}. "
                         f"Fixed breakers cannot be racked out for maintenance — the circuit "
                         f"must be de-energized to service the breaker. For Tier III concurrent "
                         f"maintainability, critical path breakers should be withdrawable. "
                         f"Confirm this is acceptable for the uptime requirements."),
            reference="Uptime Tier III, Maintainability",
        ))

    # Withdrawable vs fixed count for situational awareness
    if model.withdrawable_breakers and model.fixed_breakers:
        total = len(model.withdrawable_breakers) + len(model.fixed_breakers) + len(model.plugin_breakers)
        if total > 0:
            fixed_pct = len(model.fixed_breakers) / total * 100
            if fixed_pct > 50:
                findings.append(ModelFinding(
                    check_id="ENG-MAINT-RATIO",
                    severity="info",
                    description=(f"{len(model.fixed_breakers)} of {total} breakers are fixed-mount "
                                 f"({fixed_pct:.0f}%). Consider withdrawable for critical circuits "
                                 f"to enable concurrent maintenance."),
                    reference="Uptime Tier III",
                ))

    return findings


# ---------------------------------------------------------------------------
#  Protection Philosophy — does the topology make sense?
# ---------------------------------------------------------------------------

def _check_protection_philosophy(model: SystemModel) -> list[ModelFinding]:
    findings = []

    # Dual mains without clear interlock
    if model.has_dual_mains:
        has_interlock = any("interlock" in item.lower() for item in model.unconfirmed_items)
        has_confirmed_interlock = any(
            "interlock" in b.raw_text.lower() and "tbc" not in b.raw_text.lower()
            for b in model.breakers
        )
        if not has_confirmed_interlock:
            findings.append(ModelFinding(
                check_id="ENG-PROT-INTERLOCK",
                severity="critical",
                description=(f"Dual mains detected ({model.mains_count} service entrance breakers) "
                             f"but interlock scheme is not confirmed. Without mechanical or "
                             f"electrical interlocking, both sources could be paralleled — "
                             f"fault current doubles, coordination study is invalid, and "
                             f"available fault current may exceed equipment ratings."),
                reference="NEC 700.5, Uptime Institute",
            ))

    # Loadbank breaker without clear purpose in protection hierarchy
    if model.has_loadbank:
        findings.append(ModelFinding(
            check_id="ENG-PROT-LOADBANK",
            severity="info",
            description=("Loadbank breaker present — confirm its position in the protection "
                         "hierarchy. Is it interlocked with the mains? Does the coordination "
                         "study include the loadbank circuit? What's the transfer sequence?"),
            reference="Commissioning Requirements",
        ))

    # Couplers without clear topology explanation
    if model.coupler_count >= 2:
        findings.append(ModelFinding(
            check_id="ENG-PROT-COUPLER",
            severity="major",
            description=(f"{model.coupler_count} bus couplers detected. Confirm: main-tie-main "
                         f"topology? Which bus sections are the couplers connecting? What is "
                         f"the coupler's normal operating position (open or closed)? The "
                         f"coordination study must cover all switching states."),
            reference="IEEE C37.20, Protection Philosophy",
        ))

    return findings


# ---------------------------------------------------------------------------
#  UPS Topology — trace the power path
# ---------------------------------------------------------------------------

def _check_ups_topology(model: SystemModel) -> list[ModelFinding]:
    findings = []

    if model.has_ups_feed_through:
        # Count "TO IT" and "FROM IT" breakers
        to_it = [b for b in model.breakers
                 if "to it" in (b.feeds_description or b.raw_text).lower()]
        from_it = [b for b in model.breakers
                   if "from it" in (b.feeds_description or b.raw_text).lower()]

        total_to = sum(b.frame_amps or 0 for b in to_it)
        total_from = sum(b.frame_amps or 0 for b in from_it)

        findings.append(ModelFinding(
            check_id="ENG-UPS-PATH",
            severity="major",
            description=(f"UPS feed-through topology detected: {len(to_it)} breakers 'TO IT' "
                         f"({total_to}A total), {len(from_it)} breakers 'FROM IT' ({total_from}A total). "
                         f"The UPS itself is not shown on this drawing. Confirm: UPS rating, "
                         f"location, input/output connections, static bypass path, and whether "
                         f"the {total_to}A out = {total_from}A return is correct or includes "
                         f"redundancy."),
            reference="UPS System Design",
        ))

    if model.has_bypass:
        bypass_breakers = [b for b in model.breakers
                           if "bypass" in (b.raw_text or "").lower()]
        for b in bypass_breakers:
            amps = b.frame_amps or 0
            findings.append(ModelFinding(
                check_id="ENG-UPS-BYPASS",
                severity="info",
                description=(f"UPS bypass breaker {b.designation} ({amps}A). Confirm: bypass is "
                             f"rated for full UPS load, bypass and UPS output are synchronized "
                             f"before transfer, and the bypass path is included in the "
                             f"coordination study."),
                reference="IEEE 446, UPS Design",
                equipment_ref=b.designation,
                page_number=b.page_number,
            ))

    return findings


# ---------------------------------------------------------------------------
#  Cable Routing — will the cables physically fit?
# ---------------------------------------------------------------------------

def _check_cable_routing(model: SystemModel) -> list[ModelFinding]:
    findings = []

    # Rack plug count vs cable routing space
    if model.rack_plug_count > 24:
        findings.append(ModelFinding(
            check_id="ENG-CABLE-DENSITY",
            severity="major",
            description=(f"{model.rack_plug_count} rack plug circuits exiting top of panel. "
                         f"Each circuit is a 3-phase cable. In a modular enclosure, these "
                         f"route through the ceiling space to racks. Confirm: cable tray "
                         f"sizing, conduit fill calculations (NEC Ch. 9 Table 1, 40% max "
                         f"for 3+ conductors), and physical routing path from switchgear "
                         f"to rack positions."),
            reference="NEC Ch. 9, Constructability",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Metering & Monitoring — can you see what's happening?
# ---------------------------------------------------------------------------

def _check_metering_monitoring(model: SystemModel) -> list[ModelFinding]:
    findings = []

    # Check if all breakers have monitoring but no aggregation point
    has_modbus = any("mod tcp" in b.raw_text.lower() or "modbus" in b.raw_text.lower()
                     for b in model.breakers)
    has_pqm = any("pqm" in b.raw_text.lower() or "power quality" in b.raw_text.lower()
                   for b in model.breakers)

    if has_modbus and not has_pqm:
        findings.append(ModelFinding(
            check_id="ENG-MONITOR-AGG",
            severity="minor",
            description=("Breakers have Modbus TCP communication but no power quality meter "
                         "(PQM) or monitoring aggregation point is shown. Where do the Modbus "
                         "connections terminate? Is there a network switch in the switchgear? "
                         "How does the BMS/EPMS collect data from these devices?"),
            reference="Monitoring & BMS Integration",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Missing Designations — every breaker needs a unique ID
# ---------------------------------------------------------------------------

def _check_missing_designations(model: SystemModel) -> list[ModelFinding]:
    findings = []

    # Check if breakers have functional names but no Q-designations
    has_q_numbers = any(
        re.match(r'Q\d', b.designation) for b in model.breakers
    )

    if len(model.breakers) > 3 and not has_q_numbers:
        findings.append(ModelFinding(
            check_id="ENG-NO-Q-DESIG",
            severity="major",
            description=(f"{len(model.breakers)} breakers found but none have Q-designations "
                         f"(Q1, Q2, etc.) or unique circuit IDs. Every breaker needs a unique "
                         f"identifier for: coordination study references, factory wiring, "
                         f"commissioning test sheets, field labeling, and spare parts ordering. "
                         f"Equipment is currently identified only by rating and function."),
            reference="Drawing Standards, IEC 81346",
        ))

    return findings


# ---------------------------------------------------------------------------
#  NEC CODE CHECKS (existing)
# ---------------------------------------------------------------------------


# ===========================================================================
#  SLD ENGINEERING INTELLIGENCE
#  Checks that require understanding the Leviathan product, ABB equipment
#  naming, load accounting, and drawing consistency.
# ===========================================================================


# ---------------------------------------------------------------------------
#  Leviathan Product Spec Cross-Check
# ---------------------------------------------------------------------------

# Reference values from CLAUDE.md — the Leviathan spec
LEVIATHAN_IT_LOAD_KW = 1770       # 1.77 MW per Leviathan
LEVIATHAN_COOLING_KW = 2200       # 2.2 MW cooling capacity
LEVIATHAN_COMPUTE_RACKS = 8       # 8× racks at 200 kW each
LEVIATHAN_NETWORK_RACKS = 4       # 4× racks at 42.5 kW each
LEVIATHAN_RACK_POWER_KW = 200     # per compute rack
LEVIATHAN_NETWORK_RACK_KW = 42.5  # per network rack


def _check_leviathan_spec(model: SystemModel) -> list[ModelFinding]:
    """Cross-check SLD load totals against Leviathan product specification."""
    findings = []

    # Count power shelves and their total load
    power_shelves = [ld for ld in model.loads if "powershelf" in (ld.get("description") or "").lower().replace(" ", "")]
    if power_shelves:
        total_it_kw = len(power_shelves) * 33  # 33kW per power shelf
        total_it_kva = sum(ld.get("kva") or 0 for ld in power_shelves)

        if total_it_kw > LEVIATHAN_IT_LOAD_KW * 1.1:
            findings.append(ModelFinding(
                check_id="ENG-LEV-ITLOAD",
                severity="critical",
                description=(f"{len(power_shelves)} power shelves × 33kW = {total_it_kw}kW IT load. "
                             f"Leviathan spec is {LEVIATHAN_IT_LOAD_KW}kW (1.77MW). "
                             f"SLD shows {total_it_kw/LEVIATHAN_IT_LOAD_KW*100:.0f}% of spec — "
                             f"{total_it_kw - LEVIATHAN_IT_LOAD_KW}kW over. "
                             f"Confirm: is the spec outdated, or is the SLD oversized?"),
                reference="Leviathan Specification",
            ))

    # Count chillers and verify cooling capacity
    chillers = [ld for ld in model.loads if "chiller" in (ld.get("description") or "").lower()]
    if chillers:
        total_chiller_kva = sum(ld.get("kva") or 0 for ld in chillers)
        # Typical chiller PF ~0.85
        total_chiller_kw = total_chiller_kva * 0.85
        findings.append(ModelFinding(
            check_id="ENG-LEV-COOLING",
            severity="info",
            description=(f"{len(chillers)} chillers, total {total_chiller_kva:.0f}kVA "
                         f"(~{total_chiller_kw:.0f}kW at 0.85 PF). Leviathan cooling spec: "
                         f"{LEVIATHAN_COOLING_KW}kW."),
            reference="Leviathan Specification",
        ))

    # Generator vs total load
    if model.generator_kva:
        total_load_kw = sum(ld.get("kva", 0) or 0 for ld in model.loads) * 0.9  # rough PF
        if model.generator_kw and total_load_kw > model.generator_kw * 1.1:
            findings.append(ModelFinding(
                check_id="ENG-LEV-GENSIZE",
                severity="major",
                description=(f"Generator rated {model.generator_kw:.0f}kW but estimated "
                             f"total load is {total_load_kw:.0f}kW. Generator may be undersized "
                             f"for full-load operation."),
                reference="Generator Sizing",
            ))

    return findings


# ---------------------------------------------------------------------------
#  ABB Model Naming Intelligence
# ---------------------------------------------------------------------------

# ABB Emax 2 model variants and their meanings
ABB_EMAX_BREAKING = {
    "N": "Normal (lowest breaking capacity)",
    "S": "Standard",
    "H": "High",
    "L": "Low instantaneous (higher breaking capacity)",
    "V": "Very high",
}

# ABB Tmax XT frame limits (UL catalog)
ABB_XT_FRAMES = {
    "XT1": {"max_amps": 160, "description": "Tmax XT1 MCCB"},
    "XT2": {"max_amps": 160, "description": "Tmax XT2 MCCB"},
    "XT3": {"max_amps": 225, "description": "Tmax XT3 MCCB"},
    "XT4": {"max_amps": 250, "description": "Tmax XT4 MCCB"},
    "XT5": {"max_amps": 600, "description": "Tmax XT5 MCCB"},
    "XT6": {"max_amps": 800, "description": "Tmax XT6 MCCB"},
    "XT7": {"max_amps": 1200, "description": "Tmax XT7 MCCB"},
    "XT7M": {"max_amps": 1600, "description": "Tmax XT7M Motor protection MCCB"},
}


def _check_abb_model_naming(model: SystemModel) -> list[ModelFinding]:
    """Check ABB breaker model/suffix consistency and validity."""
    findings = []

    for qf_num, props in model.qf_designations.items():
        mdl = props.get("model") or ""
        amps = props.get("amps")
        desc = props.get("description") or ""

        if not mdl:
            continue

        # Check E4.3N vs E4.3H — N is lower breaking capacity
        if "E4.3N" in mdl and model.available_fault_current_kA:
            findings.append(ModelFinding(
                check_id="ENG-ABB-BREAKING",
                severity="critical",
                description=(f"QF{qf_num} ({mdl}) — E4.3**N** suffix means Normal (lowest) "
                             f"breaking capacity. With {model.available_fault_current_kA:.0f}kA "
                             f"available fault current, verify N-type interrupting rating is "
                             f"adequate. H-type has higher kAIC. {desc}"),
                reference="ABB Emax 2 Product Data, NEC 110.9",
                equipment_ref=f"QF{qf_num}",
            ))

        # Check XT7M vs XT7 — M is motor protection variant
        if "XT7M" in mdl.upper():
            findings.append(ModelFinding(
                check_id="ENG-ABB-VARIANT",
                severity="major",
                description=(f"QF{qf_num} ({mdl}) — XT7**M** is the motor protection variant. "
                             f"All other UPS input breakers use XT7L. Why is this one different? "
                             f"Confirm: is UIB A feeding a motor load, or should this be XT7L? "
                             f"{desc}"),
                reference="ABB Tmax XT Product Data",
                equipment_ref=f"QF{qf_num}",
            ))

        # Check XT7L at 1600A — standard XT7 max is 1200A, XT7M goes to 1600A
        xt_match = re.match(r'XT(\d+)([HMLNSLVBC]*)', mdl.upper())
        if xt_match:
            xt_num = f"XT{xt_match.group(1)}"
            suffix = xt_match.group(2)
            key = f"{xt_num}M" if "M" in suffix else xt_num

            frame_info = ABB_XT_FRAMES.get(key) or ABB_XT_FRAMES.get(xt_num)
            if frame_info and amps and amps > frame_info["max_amps"]:
                findings.append(ModelFinding(
                    check_id="ENG-ABB-FRAME",
                    severity="major",
                    description=(f"QF{qf_num} ({mdl} {amps}A) — {key} frame maximum is "
                                 f"{frame_info['max_amps']}A. {amps}A exceeds this. "
                                 f"Verify product availability. {desc}"),
                    reference="ABB Tmax XT Product Data",
                    equipment_ref=f"QF{qf_num}",
                ))

    return findings


# ---------------------------------------------------------------------------
#  QF Designation Issues — duplicates, gaps, missing breaker models
# ---------------------------------------------------------------------------

def _check_qf_designation_issues(model: SystemModel) -> list[ModelFinding]:
    """Check for duplicate functional names, missing models, inconsistencies."""
    findings = []

    # Find QF breakers with no model specified
    missing_model = []
    for qf_num, props in model.qf_designations.items():
        if not props.get("model") and props.get("description"):
            missing_model.append((qf_num, props.get("description")))

    if missing_model:
        items = ", ".join(f"QF{n} ({d})" for n, d in missing_model[:5])
        findings.append(ModelFinding(
            check_id="ENG-QF-NOMODEL",
            severity="critical",
            description=(f"{len(missing_model)} breaker(s) have no model specified: {items}. "
                         f"Cannot verify frame size, breaking capacity, or trip unit configuration "
                         f"without the breaker model."),
            reference="Submittal Requirements",
        ))

    # Find duplicate functional descriptions (e.g., two breakers both called "UPS UIB A")
    desc_map = {}  # description -> list of QF numbers
    for qf_num, props in model.qf_designations.items():
        desc = props.get("description")
        if desc and len(desc) > 3:
            key = desc.upper().replace(" ", "")
            desc_map.setdefault(key, []).append((qf_num, desc))

    for key, items in desc_map.items():
        if len(items) > 1:
            qf_list = ", ".join(f"QF{n}" for n, _ in items)
            desc = items[0][1]
            findings.append(ModelFinding(
                check_id="ENG-QF-DUPLICATE",
                severity="critical",
                description=(f"Duplicate designation '{desc}' on {len(items)} breakers: {qf_list}. "
                             f"Each breaker must have a unique functional name for the "
                             f"coordination study, factory wiring, and field identification."),
                reference="Drawing Consistency, IEC 81346",
            ))

    return findings


# ---------------------------------------------------------------------------
#  Load Accounting — total kVA/kW vs source capacity
# ---------------------------------------------------------------------------

def _check_load_accounting(model: SystemModel) -> list[ModelFinding]:
    """Verify load totals make sense against source capacity."""
    findings = []

    if not model.loads:
        return findings

    # Find loads with no description
    unnamed = [ld for ld in model.loads if not ld.get("description") and ld.get("kva")]
    if unnamed:
        items = ", ".join(f"L{ld['num']} ({ld.get('kva', '?')}kVA)" for ld in unnamed[:5])
        findings.append(ModelFinding(
            check_id="ENG-LOAD-UNNAMED",
            severity="major",
            description=(f"{len(unnamed)} load(s) have kVA ratings but no description: {items}. "
                         f"What are these loads? Cannot verify sizing without knowing the load type."),
            reference="Drawing Completeness",
        ))

    # Check for "TO BE DEFINED" loads
    full_text_lower = " ".join(ld.get("raw", "") for ld in model.loads).lower()
    # Also check the broader document text
    has_tbd_loads = any(
        "to be defined" in (ld.get("description") or "").lower() or
        "tbd" in (ld.get("description") or "").lower()
        for ld in model.loads
    )

    return findings


# ---------------------------------------------------------------------------
#  Identical Equipment Rating Discrepancies
# ---------------------------------------------------------------------------

def _check_identical_equipment_ratings(model: SystemModel) -> list[ModelFinding]:
    """Flag groups of supposedly identical equipment with different ratings."""
    findings = []

    # Group loads by base name (e.g., CHILLER1, CHILLER2, CHILLER3)
    groups = {}
    for ld in model.loads:
        desc = ld.get("description") or ""
        # Strip trailing numbers to get base name
        base = re.sub(r'\d+$', '', desc).strip()
        if base and len(base) > 2:
            groups.setdefault(base, []).append(ld)

    for base, items in groups.items():
        if len(items) < 2:
            continue
        kvas = [ld.get("kva") for ld in items if ld.get("kva")]
        if len(set(kvas)) > 1 and len(kvas) >= 2:
            details = ", ".join(f"L{ld['num']} ({ld.get('kva', '?')}kVA)" for ld in items)
            findings.append(ModelFinding(
                check_id="ENG-EQUIP-MISMATCH",
                severity="major",
                description=(f"'{base}' equipment has different ratings: {details}. "
                             f"Supposedly identical equipment should have the same Sn value. "
                             f"Different ratings suggest different models — verify spare parts "
                             f"interchangeability and confirm intentional."),
                reference="Equipment Consistency",
            ))

    return findings


# ---------------------------------------------------------------------------
#  Undefined / Incomplete Loads
# ---------------------------------------------------------------------------

def _check_undefined_loads(model: SystemModel) -> list[ModelFinding]:
    """Flag 'LOADS TO BE DEFINED' and similar incomplete items."""
    findings = []

    # Search for TBD patterns in the full text available via loads and breakers
    all_text = " ".join(
        [ld.get("raw", "") for ld in model.loads] +
        [props.get("raw", "") for props in model.qf_designations.values()]
    ).lower()

    if "loads to be defined" in all_text or "to be defined" in all_text:
        findings.append(ModelFinding(
            check_id="ENG-LOAD-TBD",
            severity="major",
            description=("'LOADS TO BE DEFINED' found on the SLD. These undefined loads affect "
                         "total load calculation, generator sizing, cable sizing, and breaker "
                         "coordination. When will they be defined? What is the estimated load "
                         "for design contingency?"),
            reference="Design Completeness",
        ))

    return findings


# ---------------------------------------------------------------------------
#  NEC CODE CHECKS (existing)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
#  NEC 646 — Modular Data Centers / UL 2755
# ---------------------------------------------------------------------------

def _check_nec_646_modular(model: SystemModel) -> list[ModelFinding]:
    """NEC Article 646 and UL 2755 requirements for modular data centers."""
    findings = []

    if not model.is_modular_data_center:
        return findings

    # SCCR must be documented for the entire assembly
    has_any_sccr = any(b.interrupting_kA for b in model.breakers)
    if not has_any_sccr:
        findings.append(ModelFinding(
            check_id="MODEL-MDC-SCCR",
            severity="critical",
            description=("Modular data center (NEC 646) — assembly SCCR not documented. "
                         "NEC 646.7 requires short-circuit ratings for the complete MDC. "
                         "Every component's SCCR must meet or exceed available fault current."),
            reference="NEC 646.7, UL 2755",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Surge Protection (NEC 242, 700.8)
# ---------------------------------------------------------------------------

def _check_spd_requirements(model: SystemModel) -> list[ModelFinding]:
    """NEC 700.8 requires SPDs on emergency system switchgear."""
    findings = []

    has_large_system = any((b.frame_amps or 0) >= 800 for b in model.breakers)
    if has_large_system and not model.has_spd_reference:
        findings.append(ModelFinding(
            check_id="MODEL-SPD",
            severity="major",
            description=("No surge protective device (SPD) referenced. NEC 700.8 requires "
                         "a listed SPD on all emergency system switchgear, switchboards, and "
                         "panelboards. Best practice: SPDs at every distribution voltage level."),
            reference="NEC 700.8, 242",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Neutral Conductor Sizing (Harmonics)
# ---------------------------------------------------------------------------

def _check_neutral_sizing(model: SystemModel) -> list[ModelFinding]:
    """200% neutral required for IT loads with triplen harmonics."""
    findings = []

    # Only relevant if there are IT/compute loads
    has_it_loads = any(
        tx.is_feeding_it_loads for tx in model.transformers
    ) or any(
        "it " in (b.feeds_description or "").lower() or
        "rack" in (b.feeds_description or "").lower() or
        "server" in (b.feeds_description or "").lower() or
        "gpu" in (b.feeds_description or "").lower()
        for b in model.breakers
    )

    if has_it_loads and not model.has_neutral_sizing_reference:
        findings.append(ModelFinding(
            check_id="MODEL-NEUTRAL",
            severity="major",
            description=("IT/compute loads detected but no 200% neutral sizing referenced. "
                         "Non-linear loads (SMPS, GPU servers) generate triplen harmonics "
                         "(3rd, 9th, 15th) that add arithmetically in the neutral conductor. "
                         "Neutral current can reach 150-200% of phase current. Per NEC "
                         "310.15(C)(1), neutral must be treated as current-carrying conductor "
                         "and sized accordingly. Industry standard: 200% neutral."),
            reference="NEC 310.15(C)(1), 220.61, IEEE C57.110",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Terminal Temperature Rating (NEC 110.14(C))
# ---------------------------------------------------------------------------

def _check_terminal_temperature(model: SystemModel) -> list[ModelFinding]:
    """Flag conductors that may be sized at 90°C when terminals are 75°C."""
    findings = []

    for c in model.cables:
        if not c.conductor_size_normalized or not c.ampacity:
            continue
        # Check if conductor ampacity suggests 90°C rating was used
        # NEC 310.16 75°C column should be the reference for most terminations
        size = c.conductor_size_normalized
        if size in NEC_310_16_75C:
            amp_75c = NEC_310_16_75C[size]
            if c.ampacity and c.ampacity > amp_75c:
                findings.append(ModelFinding(
                    check_id="MODEL-TERM-TEMP",
                    severity="major",
                    description=(f"{c.designation} — conductor ampacity ({c.ampacity}A) exceeds "
                                 f"75°C column value ({amp_75c}A) for #{size}. Per NEC 110.14(C), "
                                 f"ampacity must be based on the lowest temperature rating of "
                                 f"conductor or terminal. Most terminals are rated 75°C. Verify "
                                 f"terminal temperature rating before using 90°C ampacity."),
                    reference="NEC 110.14(C)",
                    equipment_ref=c.designation,
                    page_number=c.page_number,
                ))

    return findings


# ---------------------------------------------------------------------------
#  Working Clearance (NEC 110.26)
# ---------------------------------------------------------------------------

def _check_working_clearance(model: SystemModel) -> list[ModelFinding]:
    """Flag if no working clearance reference on a large switchgear submittal."""
    findings = []

    has_large_gear = any((b.frame_amps or 0) >= 400 for b in model.breakers)
    if has_large_gear and not model.has_working_clearance_reference:
        voltage = model.system_voltage or 480
        if voltage <= 600:
            req_depth = 42  # inches, Condition 2
        else:
            req_depth = 48
        findings.append(ModelFinding(
            check_id="MODEL-CLEARANCE",
            severity="major",
            description=(f"No working clearance reference found. NEC 110.26 requires "
                         f"{req_depth}\" depth (Condition 2) for equipment at {voltage}V. "
                         f"Minimum 30\" width, 78\" headroom. Verify switchgear dimensions "
                         f"allow adequate clearance in modular enclosure."),
            reference="NEC 110.26",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Separately Derived System Grounding (NEC 250.30)
# ---------------------------------------------------------------------------

def _check_separately_derived_grounding(model: SystemModel) -> list[ModelFinding]:
    """Transformers ≥15kVA must address NEC 250.30 grounding."""
    findings = []

    large_transformers = [tx for tx in model.transformers if tx.kva and tx.kva >= 15]
    if large_transformers and not model.has_grounding_reference:
        desigs = ", ".join(tx.designation for tx in large_transformers[:3])
        findings.append(ModelFinding(
            check_id="MODEL-SDS-GROUND",
            severity="major",
            description=(f"Transformer(s) {desigs} — no NEC 250.30 separately derived system "
                         f"grounding referenced. Requires: system bonding jumper (at source OR "
                         f"first disconnect, not both), supply-side bonding jumper, grounding "
                         f"electrode conductor. Incorrect bonding causes nuisance GFP tripping."),
            reference="NEC 250.30",
        ))

    return findings


# ---------------------------------------------------------------------------
#  Energy Storage / Battery Systems (NEC 706, NFPA 855)
# ---------------------------------------------------------------------------

def _check_energy_storage(model: SystemModel) -> list[ModelFinding]:
    """Battery/BESS requirements per NEC 706 and NFPA 855."""
    findings = []

    if not model.has_energy_storage:
        return findings

    # Lithium-ion without thermal runaway protection
    if not model.has_thermal_runaway_protection:
        findings.append(ModelFinding(
            check_id="MODEL-BATT-THERMAL",
            severity="critical",
            description=("Energy storage system detected but no thermal runaway protection "
                         "documented. NFPA 855 requires fire suppression, ventilation for "
                         "flammable gas dispersal, and explosion control for lithium-ion "
                         "installations. UL 9540A large-scale fire testing required if "
                         "group energy exceeds 50 kWh."),
            reference="NFPA 855, NEC 706, UL 9540A",
        ))

    return findings


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
