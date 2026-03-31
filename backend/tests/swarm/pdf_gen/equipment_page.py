"""Equipment schedule page generator — transformers, UPS, generators, etc.

Produces text matching the equipment extractor patterns in equipment_extractor.py.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TransformerEntry:
    designation: str       # e.g., "TX-1"
    kva: int               # e.g., 300
    primary_v: str = "480V"
    secondary_v: str = "208V"
    impedance: Optional[str] = "5.75%"
    type_: str = "Dry-Type"
    k_factor: Optional[str] = None  # e.g., "K-13"
    winding: str = "Delta-Wye"
    ul_listed: bool = True


@dataclass
class CableEntry:
    feeder_id: str         # e.g., "F-1"
    size: str              # e.g., "500 kcmil", "#6 AWG", "50mm2"
    quantity: int = 3      # Number of conductors per phase
    insulation: str = "THHN"
    material: str = "Copper"
    conduit: str = '4" EMT'
    length_ft: int = 150
    fed_from: str = ""
    feeds: str = ""
    breaker_amps: Optional[int] = None  # For cross-ref validation


def build_equipment_lines(transformers: list[TransformerEntry] = None,
                          extra_lines: list[str] = None) -> list[str]:
    """Build equipment schedule page text."""
    lines = []

    if transformers:
        lines.append("--- TRANSFORMER SCHEDULE ---")
        lines.append("")
        for tx in transformers:
            parts = [tx.designation, f"{tx.kva}kVA", tx.type_, "Transformer"]
            parts.append(f"{tx.primary_v}/{tx.secondary_v}")
            if tx.impedance:
                parts.append(f"{tx.impedance} Impedance")
            parts.append(tx.winding)
            if tx.k_factor:
                parts.append(tx.k_factor)
            if tx.ul_listed:
                parts.append("UL Listed")
            lines.append(" ".join(parts))
            lines.append("")

    if extra_lines:
        lines.extend(extra_lines)

    return lines


def build_cable_lines(cables: list[CableEntry]) -> list[str]:
    """Build cable schedule page text."""
    lines = []
    lines.append("--- FEEDER / CABLE SCHEDULE ---")
    lines.append("")

    for c in cables:
        size_str = f"{c.quantity}#{c.size}" if "#" not in c.size else f"{c.quantity}x{c.size}"
        parts = [f"FEEDER {c.feeder_id}:"]
        parts.append(f"{size_str} {c.insulation} {c.material}")
        parts.append(f"in {c.conduit}")
        parts.append(f"{c.length_ft}ft")
        if c.fed_from:
            parts.append(f"Fed from {c.fed_from}")
        if c.feeds:
            parts.append(f"Feeds {c.feeds}")
        if c.breaker_amps:
            parts.append(f"Breaker: {c.breaker_amps}A")
        lines.append(" ".join(parts))
        lines.append("")

    return lines
