"""Equipment extractor — pulls every piece of equipment from submittal text.

Scans every page for:
- Transformers (kVA, voltage, impedance)
- Breakers / ACBs / MCCBs (frame, trip, poles, interrupting rating)
- Cables (size, type, length)
- Panels/switchboards (designation, bus rating)
- Generators (kW, voltage)
- UPS systems (kVA, topology)
- ATS units (amps, poles)
- PDUs (kVA, output circuits)
- Motor starters / VFDs
- Receptacles and branch circuits

Supports formats from ABB, Eaton, Schneider, Siemens, and generic.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedEquipment:
    """A single piece of equipment found in the submittal."""
    equipment_type: str
    designation: str
    page_number: int
    raw_text: str

    voltage: Optional[str] = None
    amperage: Optional[str] = None
    kva: Optional[str] = None
    kw: Optional[str] = None
    phases: Optional[str] = None
    frequency: Optional[str] = None

    frame_size: Optional[str] = None
    trip_rating: Optional[str] = None
    poles: Optional[str] = None
    interrupting_rating: Optional[str] = None

    primary_voltage: Optional[str] = None
    secondary_voltage: Optional[str] = None
    impedance: Optional[str] = None
    winding_config: Optional[str] = None

    conductor_size: Optional[str] = None
    conductor_material: Optional[str] = None
    insulation_type: Optional[str] = None
    conduit_size: Optional[str] = None
    cable_length: Optional[str] = None

    fed_from: Optional[str] = None
    feeds: Optional[str] = None

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

        # Skip pages with very little text (drawings without text layers)
        if len(text) < 30:
            continue

        # Skip cover sheets and TOC
        if page_type in ("cover_sheet", "table_of_contents"):
            continue

        new_items = []
        new_items.extend(_extract_breakers(text, text_lower, page_num))
        new_items.extend(_extract_transformers(text, text_lower, page_num))
        new_items.extend(_extract_panels(text, text_lower, page_num, page_type))
        new_items.extend(_extract_cables(text, text_lower, page_num))
        new_items.extend(_extract_generators(text, text_lower, page_num))
        new_items.extend(_extract_ups_systems(text, text_lower, page_num))
        new_items.extend(_extract_ats_units(text, text_lower, page_num))
        new_items.extend(_extract_pdus(text, text_lower, page_num))

        if page_type == "panel_schedule":
            new_items.extend(_extract_panel_schedule_circuits(text, text_lower, page_num))

        # Tag source page type — cut sheet items get lower priority
        for item in new_items:
            item.attributes["source_page_type"] = page_type

        equipment.extend(new_items)

    # Smart deduplication: prefer SLD/schedule items over cut sheet duplicates
    PAGE_TYPE_PRIORITY = {
        "single_line_diagram": 0,
        "panel_schedule": 1,
        "equipment_schedule": 2,
        "cable_schedule": 3,
        "load_schedule": 4,
        "specification": 5,
        "cut_sheet": 6,
        "unknown": 7,
    }

    # Group by (type, model+amps) for smarter dedup
    seen = {}  # key -> (priority, equipment)
    for eq in equipment:
        key = (eq.equipment_type, eq.designation.upper().strip())
        source_type = eq.attributes.get("source_page_type", "unknown")
        priority = PAGE_TYPE_PRIORITY.get(source_type, 7)

        if key not in seen or priority < seen[key][0]:
            seen[key] = (priority, eq)

    return [eq for _, eq in seen.values()]


# ---------------------------------------------------------------------------
#  Breaker / ACB / MCCB extraction
# ---------------------------------------------------------------------------

def _extract_breakers(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    # ABB format: "XT7H 1000", "E6.2 H 4000", "XT2H 160", "XT5 630A"
    abb_patterns = [
        # E-series ACBs: E1.2, E2.2, E4.2, E6.2 — MUST have a dot (to avoid UL file numbers like E230163)
        (r'(E\d\.\d\s*[HNSLV]?\s*)(\d{3,5})', "ABB ACB"),
        # XT-series MCCBs: XT2, XT4, XT5, XT7 etc. — require H/N/S/L/B/C suffix or space before amps
        # XT1 is excluded because "XT1 1", "XT1 2" etc. are schematic wire refs
        (r'(XT[2-9][HNSLBC]?\s+)(\d{2,5})', "ABB MCCB"),
        (r'(XT\d+[HNSLBC]\s*)(\d{2,5})', "ABB MCCB"),
        # Tmax series: T1, T4, T5, T6, T7
        (r'(Tmax\s*T\d+[HNSLV]?\s*)(\d{2,5})', "ABB Tmax"),
        (r'\b(T\d[HNSLV]?\s+)(\d{3,5})\b', "ABB Tmax"),
    ]

    # Filter out known false positive patterns
    FALSE_POSITIVE_PREFIXES = (
        "DSE", "dse",  # DSE generator controllers (DSE7320, DSE2548, etc.)
    )

    for pattern, mfr_type in abb_patterns:
        for match in re.finditer(pattern, text):
            model = match.group(1).strip()
            amps = match.group(2)
            desig = f"{model}{amps}"

            # Skip false positives: UL file numbers, DSE controllers, etc.
            preceding = text[max(0, match.start()-10):match.start()]
            if any(preceding.endswith(pfx) for pfx in FALSE_POSITIVE_PREFIXES):
                continue
            # Skip if amps is unrealistic (>6300A) or too small for this pattern (<10A)
            amp_val = int(amps)
            if amp_val > 6300 or amp_val < 10:
                continue
            # Skip UL file numbers: pattern like "E" followed by 5+ digits with no dot
            if re.match(r'^E\d{5,}$', desig):
                continue

            context = text_lower[max(0, match.start()-50):min(match.end()+150, len(text_lower))]

            eq = ExtractedEquipment(
                equipment_type="breaker",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-20):min(match.end()+80, len(text))],
                frame_size=f"{amps}A",
                manufacturer="ABB",
                model=desig,
            )

            # Trip rating (often same as frame for fixed, or specified separately)
            trip_match = re.search(r'(\d{2,5})\s*(?:at|a\s*trip)', context)
            if trip_match:
                eq.trip_rating = f"{trip_match.group(1)}A"
            else:
                eq.trip_rating = f"{amps}A"

            # Interrupting rating
            ir_match = re.search(r'(\d{2,3})\s*(?:ka|kaic)', context)
            if ir_match:
                eq.interrupting_rating = f"{ir_match.group(1)}kA"

            # Poles
            pole_match = re.search(r'(\d)\s*[pP](?:ole)?', context)
            if pole_match:
                eq.poles = pole_match.group(1)

            results.append(eq)

    # Generic format: "3P 1000A 65kA" or "4P 60A 65kA"
    for match in re.finditer(r'(\d)[pP]\s+(\d{2,5})\s*[aA]\s+(\d{2,3})\s*(?:ka|kaic|kA)', text):
        poles = match.group(1)
        amps = match.group(2)
        ir = match.group(3)

        eq = ExtractedEquipment(
            equipment_type="breaker",
            designation=f"BKR-{amps}A-{poles}P-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-20):min(match.end()+50, len(text))],
            frame_size=f"{amps}A",
            trip_rating=f"{amps}A",
            poles=poles,
            interrupting_rating=f"{ir}kA",
        )
        results.append(eq)

    # Standard format: "4000AF/4000AT" or "200A frame, 150A trip"
    for match in re.finditer(r'(\d{2,5})\s*[aA][fF]\s*/\s*(\d{2,5})\s*[aA][tT]', text):
        frame = match.group(1)
        trip = match.group(2)
        eq = ExtractedEquipment(
            equipment_type="breaker",
            designation=f"BKR-{frame}AF-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-20):min(match.end()+50, len(text))],
            frame_size=f"{frame}A",
            trip_rating=f"{trip}A",
        )
        results.append(eq)

    for match in re.finditer(r'(\d{2,5})\s*(?:amp|a)\s+frame\s*[,/]\s*(\d{2,5})\s*(?:amp|a)\s+trip', text_lower):
        frame = match.group(1)
        trip = match.group(2)
        eq = ExtractedEquipment(
            equipment_type="breaker",
            designation=f"BKR-{frame}AF-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-20):min(match.end()+50, len(text))],
            frame_size=f"{frame}A",
            trip_rating=f"{trip}A",
        )
        results.append(eq)

    # Eaton format: "NRX", "RD", "HFD", "FD", etc. with amps
    eaton_patterns = [
        (r'((?:NRX|MDS|RD|HFD|FDB|FD|JD|KD|LD|MD|ND|PD)\d*[A-Z]*)\s*(\d{2,5})\s*[aA]', "Eaton"),
    ]
    for pattern, mfr in eaton_patterns:
        for match in re.finditer(pattern, text):
            model = match.group(1)
            amps = match.group(2)
            eq = ExtractedEquipment(
                equipment_type="breaker",
                designation=f"{model}-{amps}A",
                page_number=page,
                raw_text=text[max(0, match.start()-10):min(match.end()+50, len(text))],
                frame_size=f"{amps}A",
                trip_rating=f"{amps}A",
                manufacturer=mfr,
                model=model,
            )
            results.append(eq)

    # Schneider format: NSX, NS, Compact etc.
    for match in re.finditer(r'((?:NSX|NS|Compact)\s*\d*[A-Z]*)\s*(\d{2,5})\s*[aA]', text):
        model = match.group(1).strip()
        amps = match.group(2)
        eq = ExtractedEquipment(
            equipment_type="breaker",
            designation=f"{model}-{amps}A",
            page_number=page,
            raw_text=text[max(0, match.start()-10):min(match.end()+50, len(text))],
            frame_size=f"{amps}A",
            trip_rating=f"{amps}A",
            manufacturer="Schneider",
            model=model,
        )
        results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Transformer extraction
# ---------------------------------------------------------------------------

def _extract_transformers(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    # "Sn=27.78[kVA]" (ABB style in SLDs) — but only if it's actually a transformer
    # Chillers, pumps, racks, fans also have Sn= for their apparent power DRAW, not transformer rating
    LOAD_KEYWORDS = ["chiller", "pump", "motor", "fan", "rack", "shelf", "coil", "compressor",
                      "power shelf", "powershelf", "supply", "load", "heater", "light", "recircpump"]

    for match in re.finditer(r'[Ss]n\s*=\s*(\d+\.?\d*)\s*\[?kva\]?', text_lower):
        kva_val = match.group(1)

        # Check context: is this a load or a transformer?
        context = text_lower[max(0, match.start()-80):min(match.end()+80, len(text_lower))]
        is_load = any(kw in context for kw in LOAD_KEYWORDS)

        if is_load:
            # It's a load rating, not a transformer — skip or categorize differently
            continue

        eq = ExtractedEquipment(
            equipment_type="transformer",
            designation=f"TX-{kva_val}kVA-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-30):min(match.end()+80, len(text))],
            kva=kva_val,
        )
        results.append(eq)

    # Standard patterns: "TX-1 300kVA", "300kVA transformer", etc.
    patterns = [
        r'((?:tx|xfmr|t|tr)[-\s]*\d+[a-z]?)\s*[:\-\s]+(\d+)\s*kva',
        r'(\d{2,5})\s*kva\s+(?:dry[- ]?type\s+)?(?:transformer|xfmr)',
        r'transformer\s*.*?(\d{2,5})\s*kva',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            desig = None
            kva_val = None
            for g in groups:
                if g and re.match(r'\d+$', g.strip()):
                    kva_val = g.strip()
                elif g and not g.strip().isdigit():
                    desig = g.strip().upper()

            if not desig:
                desig = f"TX-{kva_val}kVA-PG{page}" if kva_val else f"TX-PG{page}"

            eq = ExtractedEquipment(
                equipment_type="transformer",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-20):min(match.end()+80, len(text))],
                kva=kva_val,
            )

            context = text_lower[max(0, match.start()-100):min(match.end()+200, len(text_lower))]

            imp_match = re.search(r'(\d+\.?\d*)\s*%?\s*(?:impedance|z\b)', context)
            if imp_match:
                eq.impedance = imp_match.group(1)

            volt_match = re.findall(r'(\d{3,5})\s*(?:v|volt)', context)
            if len(volt_match) >= 2:
                eq.primary_voltage = volt_match[0]
                eq.secondary_voltage = volt_match[1]
            elif volt_match:
                eq.voltage = volt_match[0]

            results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Panel / Switchboard extraction — smarter filtering
# ---------------------------------------------------------------------------

def _extract_panels(text: str, text_lower: str, page: int, page_type: str) -> list[ExtractedEquipment]:
    results = []

    # Only extract panels from SLDs, panel schedules, and equipment schedules
    # Skip cut sheets and specs — too many false positives from marketing text
    if page_type in ("cut_sheet", "specification", "unknown", "general_notes"):
        return results

    # Named panels: "MAIN DISTRIBUTION PANEL", "MECH UPS DISTRIBUTION PANEL", etc.
    panel_patterns = [
        r'((?:main|mech|it|ups|utility|emergency)\s+(?:distribution\s+)?(?:panel|board|switchboard|mcc))',
        r'((?:mdp|msp|swbd|mcc|dp|lp|pp)[-\s]*[a-z0-9]{1,5})',
    ]

    for pattern in panel_patterns:
        for match in re.finditer(pattern, text_lower):
            desig = match.group(1).strip().upper().replace(" ", "_")
            if len(desig) < 3:
                continue

            context = text_lower[match.start():min(match.end()+200, len(text_lower))]

            eq = ExtractedEquipment(
                equipment_type="panel",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-10):min(match.end()+80, len(text))],
            )

            # Bus rating (look for "480V 4000A BUSBAR" style)
            bus_match = re.search(r'(\d{3,5})\s*v\s+(\d{2,5})\s*a\s*(?:bus)', context)
            if bus_match:
                eq.voltage = f"{bus_match.group(1)}V"
                eq.amperage = f"{bus_match.group(2)}A"
            else:
                amp_match = re.search(r'(\d{2,5})\s*(?:a|amp)\s*(?:bus|main|rating)', context)
                if amp_match:
                    eq.amperage = f"{amp_match.group(1)}A"

            results.append(eq)

    # "480V 4000A BUSBAR" patterns (common in ABB SLDs)
    for match in re.finditer(r'(\d{3,5})\s*v\s+(\d{3,5})\s*a\s*\n?\s*busbar', text_lower):
        voltage = match.group(1)
        amps = match.group(2)
        eq = ExtractedEquipment(
            equipment_type="panel",
            designation=f"BUS-{voltage}V-{amps}A-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-10):min(match.end()+30, len(text))],
            voltage=f"{voltage}V",
            amperage=f"{amps}A",
        )
        results.append(eq)

    return results


# ---------------------------------------------------------------------------
#  Cable extraction
# ---------------------------------------------------------------------------

def _extract_cables(text: str, text_lower: str, page: int) -> list[ExtractedEquipment]:
    results = []

    cable_patterns = [
        r'(\d+)\s*#\s*(\d{1,4})\s*(kcmil|awg)',
        r'(\d{1,4})\s*(awg|kcmil)\s+(copper|aluminum|cu|al)',
        r'((?:\d+[-/]\d+|\d{1,4})\s*(?:awg|kcmil)).*?(thhn|xhhw|thwn|mc|use)',
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

            if "copper" in context or " cu " in context:
                eq.conductor_material = "copper"
            elif "aluminum" in context or " al " in context:
                eq.conductor_material = "aluminum"

            for ins_type in ["thhn", "xhhw", "thwn", "use-2", "rhh", "rhw"]:
                if ins_type in context:
                    eq.insulation_type = ins_type.upper()
                    break

            conduit_match = re.search(r'(\d+[/.]?\d*)\s*["\u2033]?\s*(?:conduit|emt|imc|rmc|pvc)', context)
            if conduit_match:
                eq.conduit_size = conduit_match.group(1) + '"'

            results.append(eq)

    # Also catch "Rx1Cx300mm" style cable specs (metric, common in European/ABB submittals)
    for match in re.finditer(r'(\d+)[rR]x(\d+)[cC]x(\d+)\s*mm', text):
        runs = match.group(1)
        conductors = match.group(2)
        size_mm = match.group(3)
        eq = ExtractedEquipment(
            equipment_type="cable",
            designation=f"CABLE-{runs}Rx{conductors}Cx{size_mm}mm-PG{page}",
            page_number=page,
            raw_text=text[max(0, match.start()-10):min(match.end()+50, len(text))],
            conductor_size=f"{runs}x{conductors}x{size_mm}mm²",
            attributes={"runs": runs, "conductors": conductors, "size_mm2": size_mm},
        )
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
                raw_text=text[max(0, match.start()-10):min(match.end()+50, len(text))],
                kw=kw_val,
            )
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
                raw_text=text[max(0, match.start()-10):min(match.end()+50, len(text))],
                kva=kva_val,
            )
            results.append(eq)

    # "UPS Module" references
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
                raw_text=text[max(0, match.start()-10):min(match.end()+50, len(text))],
                amperage=f"{amp_val}A" if amp_val else None,
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
                if g and re.match(r'\d{2,4}$', g.strip()):
                    kva_val = g.strip()
                elif g and not g.strip().isdigit():
                    desig = g.strip().upper()

            if not desig:
                desig = f"PDU-PG{page}"

            eq = ExtractedEquipment(
                equipment_type="pdu",
                designation=desig,
                page_number=page,
                raw_text=text[max(0, match.start()-10):min(match.end()+50, len(text))],
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

        wire_match = re.search(r'#(\d{1,2})\s*(?:awg)?', context)
        if wire_match:
            eq.conductor_size = f"#{wire_match.group(1)} AWG"

        results.append(eq)

    return results
