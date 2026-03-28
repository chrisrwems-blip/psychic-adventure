"""Jurisdiction detection — determines NEC vs IEC applicability from submittal content.

Detects installation jurisdiction based on:
- Voltage system (480V/60Hz → NEC, 400V/50Hz → IEC)
- Standards referenced (UL → NEC, IEC/CE → IEC)
- Conductor sizing (AWG/kcmil → NEC, mm² → IEC)
"""
from dataclasses import dataclass


@dataclass
class JurisdictionResult:
    code: str            # "NEC" or "IEC" or "MIXED"
    confidence: float    # 0.0-1.0
    signals: list        # list of (signal, weight) tuples explaining the determination
    nec_edition: str     # "2020", "2023", or "unknown"
    warnings: list       # issues found (e.g., metric cables in NEC jurisdiction)


def detect_jurisdiction(pages: list[dict], global_metadata: dict) -> JurisdictionResult:
    """Analyze submittal content to determine applicable electrical code."""
    full_text = "\n".join(p.get("text_lower", "") for p in pages)

    nec_signals = []
    iec_signals = []
    warnings = []

    # --- Voltage/Frequency ---
    voltages = global_metadata.get("voltages_found", [])
    frequency = global_metadata.get("frequency")

    nec_voltages = {120, 208, 240, 277, 480}  # Distinctly NEC
    iec_voltages = {230, 400, 415}  # Distinctly IEC

    nec_v_count = sum(1 for v in set(voltages) if v in nec_voltages)
    iec_v_count = sum(1 for v in set(voltages) if v in iec_voltages)

    if 480 in voltages:
        nec_signals.append(("480V system voltage", 3))
    if 277 in voltages:
        nec_signals.append(("277V (480Y/277V system)", 2))
    if 208 in voltages:
        nec_signals.append(("208V system voltage", 2))
    if 400 in voltages:
        iec_signals.append(("400V system voltage (IEC standard)", 2))
    if 415 in voltages:
        iec_signals.append(("415V system voltage (IEC standard)", 2))
    if 230 in voltages and 400 not in voltages:
        iec_signals.append(("230V (IEC single-phase)", 1))

    if frequency == 60:
        nec_signals.append(("60Hz frequency (North America)", 3))
    elif frequency == 50:
        iec_signals.append(("50Hz frequency (IEC regions)", 3))

    # --- Standards Referenced ---
    standards = global_metadata.get("standards_referenced", [])
    standards_text = " ".join(standards)

    # UL standards → NEC market
    ul_refs = [s for s in standards if "ul" in s.lower()]
    if ul_refs:
        nec_signals.append((f"UL standards referenced ({len(ul_refs)} refs)", 3))

    # Specific UL listings
    if "ul 489" in full_text or "ul489" in full_text:
        nec_signals.append(("UL 489 (molded case circuit breakers — NEC market)", 2))
    if "ul 1558" in full_text:
        nec_signals.append(("UL 1558 (metal-enclosed switchgear — NEC market)", 2))
    if "ul 891" in full_text:
        nec_signals.append(("UL 891 (switchboards — NEC market)", 2))
    if "ul 67" in full_text:
        nec_signals.append(("UL 67 (panelboards — NEC market)", 2))
    if "ul 1778" in full_text:
        nec_signals.append(("UL 1778 (UPS — NEC market)", 2))

    # IEC standards → IEC market
    iec_refs = [s for s in standards if "iec" in s.lower()]
    if iec_refs:
        iec_signals.append((f"IEC standards referenced ({len(iec_refs)} refs)", 2))

    if "iec 61439" in full_text:
        iec_signals.append(("IEC 61439 (switchgear assemblies — IEC market)", 2))
    if "iec 60947" in full_text:
        iec_signals.append(("IEC 60947 (switching devices — IEC market)", 1))

    # CE marking
    if " ce " in full_text or "ce marking" in full_text or "ce mark" in full_text:
        iec_signals.append(("CE marking referenced", 1))

    # NEC articles explicitly cited
    nec_articles = [s for s in standards if "nec" in s.lower() or "nfpa 70" in s.lower()]
    if nec_articles:
        nec_signals.append((f"NEC/NFPA 70 articles cited ({len(nec_articles)} refs)", 3))

    # --- Conductor Sizing ---
    has_awg = "awg" in full_text or "kcmil" in full_text
    has_metric = "mm2" in full_text or "mm²" in full_text

    if has_awg:
        nec_signals.append(("AWG/kcmil conductor sizing (NEC system)", 2))
    if has_metric:
        iec_signals.append(("Metric (mm²) conductor sizing (IEC system)", 2))

    # --- Location Indicators ---
    if "usa" in full_text or "united states" in full_text:
        nec_signals.append(("USA location referenced", 2))
    if "canada" in full_text:
        nec_signals.append(("Canada location (CEC, similar to NEC)", 1))

    # --- Score ---
    nec_score = sum(w for _, w in nec_signals)
    iec_score = sum(w for _, w in iec_signals)
    total = nec_score + iec_score

    if total == 0:
        code = "NEC"  # Default to NEC if no signals
        confidence = 0.5
    elif nec_score > iec_score * 1.5:
        code = "NEC"
        confidence = min(nec_score / total, 0.95)
    elif iec_score > nec_score * 1.5:
        code = "IEC"
        confidence = min(iec_score / total, 0.95)
    else:
        code = "MIXED"
        confidence = 0.5

    # --- Warnings for mixed systems ---
    if code == "NEC" and has_metric:
        warnings.append(
            "METRIC CONDUCTORS IN NEC JURISDICTION: Submittal uses mm² conductor sizing "
            "but system voltage (480V/60Hz) and UL listings indicate NEC applies. "
            "Metric cable sizes do not directly correspond to NEC Table 310.16 entries. "
            "Manufacturer must provide NEC-equivalent ampacity data or the conductors "
            "must be re-evaluated per NEC 310.15 using actual conductor properties."
        )

    if code == "IEC" and has_awg:
        warnings.append(
            "AWG CONDUCTORS IN IEC JURISDICTION: Submittal uses AWG/kcmil sizing "
            "but system voltage (400V/50Hz) indicates IEC may apply. Verify applicable code."
        )

    # NEC edition detection
    nec_edition = "unknown"
    if "nfpa 70-2023" in full_text or "nec 2023" in full_text:
        nec_edition = "2023"
    elif "nfpa 70-2020" in full_text or "nec 2020" in full_text:
        nec_edition = "2020"
    elif "nfpa 70-2017" in full_text or "nec 2017" in full_text:
        nec_edition = "2017"

    return JurisdictionResult(
        code=code,
        confidence=round(confidence, 2),
        signals=[(s, w) for s, w in nec_signals] + [(s, -w) for s, w in iec_signals],
        nec_edition=nec_edition,
        warnings=warnings,
    )
