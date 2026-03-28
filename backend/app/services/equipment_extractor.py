"""Equipment extractor — pulls every piece of equipment from submittal text.

Scans every page for:
- Transformers (kVA, voltage, impedance)
- Breakers (frame, trip, poles)
- Cables (size, type, length)
- Panels/switchboards (designation, bus rating)
- Generators (kW, voltage)
- UPS systems (kVA, topology)
- ATS units (amps, poles)
- PDUs (kVA, output circuits)
- Motor starters / VFDs
- Receptacles and branch circuits
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedEquipment:
    """A single piece of equipment found in the submittal."""
    equipment_type: str
    designation: str  # e.g., "TX-1", "PNL-2A", "MCC-1"
    page_number: int
    raw_text: str  # The text snippet it was found in

    # Common fields
    voltage: Optional[str] = None
    amperage: Optional[str] = None
    kva: Optional[str] = None
    kw: Optional[str] = None
    phases: Optional[str] = None
    frequency: Optional[str] = None

    # Breaker-specific
    frame_size: Optional[str] = None
    trip_rating: Optional[str] = None
    poles: Optional[str] = None
    interrupting_rating: Optional[str] = None

    # Transformer-specific
    primary_voltage: Optional[str] = None
    secondary_voltage: Optional[str] = None
    impedance: Optional[str] = None
    winding_config: Optional[str] = None  # delta-wye, etc.

    # Cable-specific
    conductor_size: Optional[str] = None
    conductor_material: Optional[str] = None
    insulation_type: Optional[str] = None
    conduit_size: Optional[str] = None
    cable_length: Optional[str] = None

    # Feeder info
    fed_from: Optional[str] = None
    feeds: Optional[str] = None

    # Additional attributes
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    attributes: dict = field(default_factory=dict)


def extract_all_equipment(pages: list[dict]) -> list[ExtractedEquipment]:
    """Extract every piece of equipment from all pages."""
    equipment = []

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]
        text_lower = page_data["text_lower"]
        page_type = page_data.get("page_type", "unknown")

        # Run all extractors
        equipment.extend(_extract_transformers(text, text_lower, page_num))
        equipment.extend(_extract_breakers(text, text_lower, page_num))
        equipment.extend(_extract_panels(text, text_lower, page_num))
        equipment.extend(_extract_cables(text, text_lower, page_num))
        equipment.extend(_extract_generators(text, text_lower, page_num))
        equipment.extend(_extract_ups_systems(text, text_lower, page_num))
        equipment.extend(_extract_ats_units(text, text_lower, page_num))
        equipment.extend(_extract_motors(text, text_lower, page_num))
        equipment.extend(_extract_pdus(text, text_lower, page_num))

        # Panel schedule-specific extraction
        if page_type == "panel_schedule":
            equipment.extend(_extract_panel_schedule_circuits(text, text_lower, page_num))

    # Deduplicate by designation + type
    seen = set()
    unique = []
    for eq in equipment:
        key = (eq.equipment_type, eq.designation.upper())
        if key not in seen:
            seen.add(key)
            unique.append(eq)

    return unique


# ---------------------------------------------------------------------------
#  Transformer extraction
# ---------------------------------------------------------------------------

def _extract_transformers(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    # Pattern: TX-1, T-1, XFMR-1, etc. with kVA
    patterns = [
        r'((?:tx|xfmr|t|tr)[-\s]*\d+[a-z]?)\s*[:\-\s]+(\d+)\s*kva',
        r'(\d+)\s*kva\s+(?:transformer|xfmr)\s*(?:[-\s]*((?:tx|t)[-\s]*\d+[a-z]?))?',
        r'transformer\s+((?:tx|t|xfmr)[-\s]*\d+[a-z]?)[:\s]+(\d+)\s*kva',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            desig = groups[0].strip().upper() if groups[0] else f"TX-{page}"
            kva_val = None
            for g in groups:
                if g and g.isdigit():
                    kva_val = g
                    break

            eq = ExtractedEquipment(
                equipment_type="transformer",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-20):match.end()+50],
                kva=kva_val,
            )

            # Look for impedance near this match
            context = text_lower[max(0, match.start()-100):match.end()+200]
            imp_match = re.search(r'(\d+\.?\d*)\s*%?\s*(?:impedance|z)', context)
            if imp_match:
                eq.impedance = imp_match.group(1)

            # Look for voltage
            volt_match = re.findall(r'(\d{3,5})\s*(?:v|volt)', context)
            if len(volt_match) >= 2:
                eq.primary_voltage = volt_match[0]
                eq.secondary_voltage = volt_match[1]
            elif volt_match:
                eq.voltage = volt_match[0]

            # Winding config
            if "delta" in context and "wye" in context:
                eq.winding_config = "delta-wye"
            elif "wye" in context:
                eq.winding_config = "wye-wye"

            results.append(eq)

    # Also catch standalone kVA transformer mentions
    for match in re.finditer(r'(\d{2,5})\s*kva\s+(?:dry[- ]?type\s+)?transformer', text_lower):
        kva_val = match.group(1)
        eq = ExtractedEquipment(
            equipment_type="transformer",
            designation=f"TX-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-10):match.end()+50],
            kva=kva_val,
        )
        results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Breaker extraction
# ---------------------------------------------------------------------------

def _extract_breakers(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    # Pattern: breaker designations with frame/trip
    # e.g., "Main Breaker: 4000AF/4000AT" or "200A frame, 150A trip"
    patterns = [
        r'(\d{2,5})\s*a[ft]\s*/\s*(\d{2,5})\s*a[ft]',  # 800AF/800AT
        r'(\d{2,5})\s*(?:amp|a)\s+frame\s*[,/]\s*(\d{2,5})\s*(?:amp|a)\s+trip',
        r'frame\s*[:\s]*(\d{2,5})\s*a\s*[,/]\s*trip\s*[:\s]*(\d{2,5})\s*a',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            frame = match.group(1)
            trip = match.group(2)

            # Look for designation nearby
            context = text_lower[max(0, match.start()-80):match.start()]
            desig_match = re.search(r'((?:cb|br|bkr|breaker)[-\s]*\d+[a-z]?)', context)
            desig = desig_match.group(1).upper() if desig_match else f"BKR-{frame}AF-PG{page}"

            eq = ExtractedEquipment(
                equipment_type="breaker",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-20):match.end()+30],
                frame_size=f"{frame}A",
                trip_rating=f"{trip}A",
            )

            # Look for interrupting rating
            ir_context = text_lower[match.start():match.end()+100]
            ir_match = re.search(r'(\d{2,3})\s*(?:ka|kaic)', ir_context)
            if ir_match:
                eq.interrupting_rating = f"{ir_match.group(1)}kA"

            # Poles
            pole_match = re.search(r'(\d)\s*(?:pole|p\b)', ir_context)
            if pole_match:
                eq.poles = pole_match.group(1)

            results.append(eq)

    # Catch simpler breaker mentions: "200A breaker", "100AT"
    for match in re.finditer(r'(\d{2,5})\s*(?:at|af)\b', text_lower):
        val = match.group(1)
        context = text_lower[max(0, match.start()-50):match.end()+50]
        if "breaker" in context or "circuit" in context or "cb" in context:
            eq = ExtractedEquipment(
                equipment_type="breaker",
                designation=f"BKR-{val}A-PG{page}",
                page_number=page,
                raw_text=text[max(0, match.start()-10):match.end()+30],
                trip_rating=f"{val}A",
            )
            results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Panel/switchboard extraction
# ---------------------------------------------------------------------------

def _extract_panels(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    # Panel designations: PNL-1, LP-A, DP-1, MDP, etc.
    patterns = [
        r'((?:pnl|panel|lp|dp|mdp|msp|swbd|sb|switchboard|mcc)[-\s]*[a-z0-9]{1,5})',
        r'panel\s+["\']?((?:[a-z]{1,3}[-\s]*\d{1,3}[a-z]?))["\']?',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            desig = match.group(1).strip().upper()
            if len(desig) < 2:
                continue

            context = text_lower[match.start():min(match.end()+300, len(text_lower))]

            eq = ExtractedEquipment(
                equipment_type="panel",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-10):min(match.end()+100, len(text))],
            )

            # Bus rating
            bus_match = re.search(r'(\d{2,5})\s*(?:a|amp)\s*(?:bus|main)', context)
            if bus_match:
                eq.amperage = f"{bus_match.group(1)}A"

            # Voltage
            volt_match = re.search(r'(\d{3})\s*/\s*(\d{3})\s*v', context)
            if volt_match:
                eq.voltage = f"{volt_match.group(1)}/{volt_match.group(2)}V"
            else:
                volt_match2 = re.search(r'(\d{3,5})\s*v', context)
                if volt_match2:
                    eq.voltage = f"{volt_match2.group(1)}V"

            # Fed from
            fed_match = re.search(r'fed\s+from\s+([\w\-]+)', context)
            if fed_match:
                eq.fed_from = fed_match.group(1).upper()

            results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Cable extraction
# ---------------------------------------------------------------------------

def _extract_cables(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    # Cable designations with sizes
    # "3#500 kcmil + 1#250 kcmil GND in 4" conduit"
    # "#4/0 AWG copper THHN"
    cable_patterns = [
        r'(\d+)\s*#\s*(\d{1,4})\s*(kcmil|awg)',
        r'(\d{1,4})\s*(awg|kcmil)\s+(copper|aluminum|cu|al)',
        r'((?:\d+[-/]\d+|\d{1,4})\s*(?:awg|kcmil)).*?(thhn|xhhw|thwn|mc|so|use)',
    ]

    for pattern in cable_patterns:
        for match in re.finditer(pattern, text_lower):
            raw = text[max(0, match.start()-20):min(match.end()+80, len(text))]
            context = text_lower[max(0, match.start()-50):min(match.end()+100, len(text_lower))]

            eq = ExtractedEquipment(
                equipment_type="cable",
                designation=f"CABLE-PG{page}-{len(results)+1}",
                page_number=page,
                raw_text=raw,
                conductor_size=match.group(0).strip(),
            )

            # Material
            if "copper" in context or " cu " in context:
                eq.conductor_material = "copper"
            elif "aluminum" in context or " al " in context:
                eq.conductor_material = "aluminum"

            # Insulation
            for ins_type in ["thhn", "xhhw", "thwn", "use-2", "rhh", "rhw"]:
                if ins_type in context:
                    eq.insulation_type = ins_type.upper()
                    break

            # Conduit
            conduit_match = re.search(r'(\d+[/.]?\d*)\s*["\u2033]?\s*(?:conduit|emt|imc|rmc|pvc)', context)
            if conduit_match:
                eq.conduit_size = conduit_match.group(1) + '"'

            results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Generator extraction
# ---------------------------------------------------------------------------

def _extract_generators(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    patterns = [
        r'((?:gen|g|eg)[-\s]*\d+[a-z]?)\s*[:\-\s]+(\d+)\s*kw',
        r'(\d{3,5})\s*kw\s+(?:standby\s+)?(?:generator|genset)',
        r'generator\s*.*?(\d{3,5})\s*kw',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            desig = None
            kw_val = None
            for g in groups:
                if g and re.match(r'\d{3,5}$', g):
                    kw_val = g
                elif g and not g.isdigit():
                    desig = g.strip().upper()

            if not desig:
                desig = f"GEN-PG{page}"

            eq = ExtractedEquipment(
                equipment_type="generator",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-10):match.end()+50],
                kw=kw_val,
            )

            context = text_lower[match.start():match.end()+200]
            if "diesel" in context:
                eq.attributes["fuel_type"] = "diesel"
            elif "natural gas" in context:
                eq.attributes["fuel_type"] = "natural_gas"

            volt_match = re.search(r'(\d{3,5})\s*v', context)
            if volt_match:
                eq.voltage = f"{volt_match.group(1)}V"

            results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  UPS extraction
# ---------------------------------------------------------------------------

def _extract_ups_systems(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    patterns = [
        r'((?:ups)[-\s]*\d+[a-z]?)\s*[:\-\s]+(\d+)\s*kva',
        r'(\d{2,5})\s*kva\s+ups',
        r'ups\s*.*?(\d{2,5})\s*kva',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            desig = None
            kva_val = None
            for g in groups:
                if g and re.match(r'\d{2,5}$', g):
                    kva_val = g
                elif g and not g.isdigit():
                    desig = g.strip().upper()

            if not desig:
                desig = f"UPS-PG{page}"

            eq = ExtractedEquipment(
                equipment_type="ups",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-10):match.end()+50],
                kva=kva_val,
            )

            context = text_lower[match.start():match.end()+200]
            if "double conversion" in context or "double-conversion" in context:
                eq.attributes["topology"] = "double_conversion"

            results.append(eq)

    # Also catch "UPS Modules" style references
    for match in re.finditer(r'ups\s+module', text_lower):
        context = text_lower[match.start():min(match.end()+200, len(text_lower))]
        eq = ExtractedEquipment(
            equipment_type="ups",
            designation=f"UPS-MODULE-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-10):min(match.end()+50, len(text))],
        )
        kva_m = re.search(r'(\d{2,5})\s*kva', context)
        if kva_m:
            eq.kva = kva_m.group(1)
        results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  ATS extraction
# ---------------------------------------------------------------------------

def _extract_ats_units(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    patterns = [
        r'((?:ats)[-\s]*\d+[a-z]?)\s*[:\-\s]+(\d+)\s*(?:a|amp)',
        r'(\d{2,5})\s*(?:a|amp)\s+(?:ats|transfer\s+switch)',
        r'(?:ats|automatic\s+transfer\s+switch)\s*.*?(\d{2,5})\s*(?:a|amp)',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            desig = None
            amp_val = None
            for g in groups:
                if g and re.match(r'\d{2,5}$', g):
                    amp_val = g
                elif g and not g.isdigit():
                    desig = g.strip().upper()

            if not desig:
                desig = f"ATS-PG{page}"

            eq = ExtractedEquipment(
                equipment_type="ats",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-10):match.end()+50],
                amperage=f"{amp_val}A" if amp_val else None,
            )
            results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Motor extraction
# ---------------------------------------------------------------------------

def _extract_motors(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    patterns = [
        r'((?:mtr|motor|m)[-\s]*\d+[a-z]?)\s*[:\-\s]+(\d+)\s*hp',
        r'(\d{1,4})\s*hp\s+motor',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            desig = None
            hp_val = None
            for g in groups:
                if g and re.match(r'\d{1,4}$', g):
                    hp_val = g
                elif g and not g.isdigit():
                    desig = g.strip().upper()

            if not desig:
                desig = f"MTR-PG{page}"

            eq = ExtractedEquipment(
                equipment_type="motor",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-10):match.end()+50],
                attributes={"hp": hp_val} if hp_val else {},
            )
            results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  PDU extraction
# ---------------------------------------------------------------------------

def _extract_pdus(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    patterns = [
        r'((?:pdu)[-\s]*\d+[a-z]?)\s*[:\-\s]+(\d+)\s*kva',
        r'(\d{2,4})\s*kva\s+pdu',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            desig = None
            kva_val = None
            for g in groups:
                if g and re.match(r'\d{2,4}$', g):
                    kva_val = g
                elif g and not g.isdigit():
                    desig = g.strip().upper()

            if not desig:
                desig = f"PDU-PG{page}"

            eq = ExtractedEquipment(
                equipment_type="pdu",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-10):match.end()+50],
                kva=kva_val,
            )
            results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Panel schedule circuit extraction
# ---------------------------------------------------------------------------

def _extract_panel_schedule_circuits(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    """Extract individual circuits from a panel schedule page."""
    results = []

    # Look for circuit patterns: "1  20A  1P  #12 AWG  Lighting"
    circuit_pattern = r'(\d{1,3})\s+(\d{1,3})\s*(?:a|at)\s+(\d)\s*(?:p|pole)'
    for match in re.finditer(circuit_pattern, text_lower):
        ckt_num = match.group(1)
        trip = match.group(2)
        poles = match.group(3)

        context = text_lower[match.start():min(match.end()+100, len(text_lower))]

        eq = ExtractedEquipment(
            equipment_type="circuit_breaker",
            designation=f"CKT-{ckt_num}-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-5):min(match.end()+50, len(text))],
            trip_rating=f"{trip}A",
            poles=poles,
        )

        # Wire size
        wire_match = re.search(r'#(\d{1,2})\s*(?:awg)?', context)
        if wire_match:
            eq.conductor_size = f"#{wire_match.group(1)} AWG"

        results.append(eq)

    return results
