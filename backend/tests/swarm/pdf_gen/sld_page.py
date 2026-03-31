"""SLD page text generator — produces text matching the ABB extraction patterns.

The SLD extractor in sld_schedule_crosscheck.py expects:
  Pattern 1 (ABB): -QF{n}/Q{n} followed by model+amps, poles, kA, description
  Pattern 2 (Generic): CB-{n}, BR-{n}, etc.

This module generates ABB-format SLD entries.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SLDBreaker:
    """A single breaker entry on an SLD page."""
    qf_num: int          # QF number (ABB internal)
    q_num: str           # Q number (e.g., "1", "8", "14A")
    model: str           # e.g., "E6.2H", "XT7H", "XT5H"
    frame_amps: int      # e.g., 4000, 1000, 630
    poles: int = 3
    kaic: Optional[int] = None  # e.g., 85, 65
    description: str = ""       # e.g., "MECHANICAL UPS", "IT UPS A"
    trip_amps: Optional[int] = None  # If different from frame


def sld_breaker_line(b: SLDBreaker) -> str:
    """Generate a single SLD breaker text line in ABB format.

    Output format: -QF{n}/Q{n} {model} {amps} {poles}P {kA}kA {description}
    This matches the regex: r'-QF(\\d+)/Q(\\d+[A-Z]?)' in _extract_from_sld
    """
    parts = [f"-QF{b.qf_num}/Q{b.q_num}"]
    parts.append(f"{b.model} {b.frame_amps}")
    parts.append(f"{b.poles}P")
    if b.kaic:
        parts.append(f"{b.kaic}kA")
    if b.description:
        parts.append(b.description)
    return "  ".join(parts)


def build_sld_lines(breakers: list[SLDBreaker], system_voltage: str = "480V",
                    frequency: str = "60Hz", include_gfp: bool = True,
                    include_afc_label: bool = True,
                    include_arc_flash: bool = True) -> list[str]:
    """Build complete SLD page text lines from a list of breakers.

    Includes system-level keywords that the review engine checks for.
    """
    lines = []
    lines.append(f"SYSTEM VOLTAGE: {system_voltage}  FREQUENCY: {frequency}")
    lines.append(f"3-PHASE 4-WIRE SYSTEM")
    lines.append("")

    if include_afc_label:
        lines.append("AVAILABLE FAULT CURRENT: 42kA AT MAIN BUS")
        lines.append("AFC LABEL PER NEC 110.24")
        lines.append("")

    if include_gfp:
        lines.append("GROUND FAULT PROTECTION PROVIDED PER NEC 230.95")
        lines.append("GFP SETTINGS: PICKUP 1200A, DELAY 0.5s")
        lines.append("")

    if include_arc_flash:
        lines.append("ARC FLASH ANALYSIS PER IEEE 1584")
        lines.append("ARC FLASH LABELS INSTALLED PER NFPA 70E")
        lines.append("")

    lines.append("--- SWITCHGEAR BREAKER SCHEDULE ---")
    lines.append("")

    for b in breakers:
        lines.append(sld_breaker_line(b))
        lines.append("")

    return lines


def default_sld_breakers() -> list[SLDBreaker]:
    """Return a realistic set of SLD breakers for a data center MDB."""
    return [
        SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
        SLDBreaker(2, "2", "E2.2H", 1600, 3, 85, "MECHANICAL UPS"),
        SLDBreaker(3, "3", "XT7H", 1000, 3, 65, "IT UPS A"),
        SLDBreaker(4, "4", "XT7H", 1000, 3, 65, "IT UPS B"),
        SLDBreaker(5, "5", "XT5H", 630, 3, 65, "NETWORK RACKS"),
        SLDBreaker(6, "6", "XT5H", 400, 3, 65, "CHILLER PLANT"),
        SLDBreaker(7, "7", "XT5H", 250, 3, 65, "BYPASS PANEL"),
        SLDBreaker(8, "8", "XT7H", 1000, 3, 65, "IT RACK DISTRIBUTION"),
    ]
