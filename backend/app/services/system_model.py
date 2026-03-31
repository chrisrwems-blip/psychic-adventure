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
    is_metric: bool = False
    material: Optional[str] = None  # copper, aluminum
    insulation: Optional[str] = None
    length_ft: Optional[int] = None
    breaker_amps: Optional[int] = None  # the breaker protecting this cable
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

    # Document quality flags
    has_afc_label: bool = False
    has_arc_flash_reference: bool = False
    has_voltage_label: bool = False
    has_coordination_study_reference: bool = False
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
            # Parse length
            length_match = re.search(r'(\d+)\s*(?:ft|feet|\')', (eq.raw_text or ""))
            if length_match:
                c.length_ft = int(length_match.group(1))

            model.cables.append(c)

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

    # Only run checks if the document has relevant content
    if _has_switchgear(model):
        findings.extend(_check_service_entrance(model))
        findings.extend(_check_large_breakers(model))
        findings.extend(_check_breaker_ratings(model))

    if _has_transformers(model):
        findings.extend(_check_transformers(model))

    if _has_cables(model):
        findings.extend(_check_cables(model))

    # Document-level checks always run (they're about what's missing)
    findings.extend(_check_document_completeness(model))
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
#  Cable Checks
# ---------------------------------------------------------------------------

def _check_cables(model: SystemModel) -> list[ModelFinding]:
    findings = []

    for c in model.cables:
        # Metric cables in NEC jurisdiction
        if c.is_metric and model.jurisdiction == "NEC":
            findings.append(ModelFinding(
                check_id="MODEL-CABLE-METRIC",
                severity="major",
                description=(f"{c.designation} — metric conductor ({c.conductor_size}) in NEC "
                             f"jurisdiction. Use IEC 60364 ampacity tables directly. Do NOT "
                             f"convert mm² to AWG for NEC 310.16 lookup — the conversion is "
                             f"lossy and dangerous."),
                reference="IEC 60364, NEC 310.16",
                equipment_ref=c.designation,
                page_number=c.page_number,
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
    has_large_gear = any(
        (b.frame_amps or 0) >= 100 for b in model.breakers
    )
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
