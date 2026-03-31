"""Panel schedule page text generator — produces text matching schedule extraction patterns.

The schedule extractor in sld_schedule_crosscheck.py expects blocks starting with
Q{n} designation, followed by INCOMING/OUTGOING, poles+amps+kA pattern, model, etc.

Format:
    Q{n}
    INCOMING/OUTGOING
    {poles}P {amps}A {kA}kA
    FIXED/PLUGIN/WITHDRAWABLE
    {model}
    {description}
"""
from dataclasses import dataclass
from typing import Optional

from .sld_page import SLDBreaker


@dataclass
class ScheduleBreaker:
    """A single breaker entry in a panel schedule."""
    q_num: str           # e.g., "1", "8"
    model: str           # e.g., "E6.2H", "XT7H"
    frame_amps: int
    poles: int = 3
    kaic: Optional[int] = None
    feed_type: str = "OUTGOING"  # INCOMING or OUTGOING
    mounting: str = "WITHDRAWABLE"
    trip_unit: str = "EKIP TOUCH MEASURING LSI"
    description: str = ""
    trip_amps: Optional[int] = None  # If different from frame


def schedule_breaker_block(b: ScheduleBreaker) -> list[str]:
    """Generate a schedule breaker text block.

    Output matches the pattern: Q{n} ... {poles}P {amps}A {kA}kA ... {model}
    """
    lines = []
    lines.append(f"Q{b.q_num}")
    lines.append(f"{b.feed_type}")
    ka_str = f" {b.kaic}kA" if b.kaic else ""
    lines.append(f"{b.poles}P {b.frame_amps}A{ka_str}")
    lines.append(f"{b.mounting}")
    lines.append(f"{b.model} {b.frame_amps}")
    lines.append(f"TRIP UNIT: {b.trip_unit}")
    if b.description:
        lines.append(f"{b.description}")
    lines.append("")
    return lines


def build_schedule_lines(breakers: list[ScheduleBreaker]) -> list[str]:
    """Build complete schedule page text from a list of breakers."""
    lines = []
    lines.append("BREAKER DETAILS")
    lines.append("CUBICLE NO / Q-DESIGNATION / BREAKER TYPE / RATING")
    lines.append("")

    for b in breakers:
        lines.extend(schedule_breaker_block(b))

    return lines


def sld_to_schedule_breakers(sld_breakers: list[SLDBreaker]) -> list[ScheduleBreaker]:
    """Convert SLD breakers to matching schedule breakers (no errors).

    Use this as a baseline, then inject errors for specific breakers.
    """
    result = []
    for s in sld_breakers:
        feed = "INCOMING" if "INCOMING" in s.description.upper() else "OUTGOING"
        result.append(ScheduleBreaker(
            q_num=s.q_num,
            model=s.model,
            frame_amps=s.frame_amps,
            poles=s.poles,
            kaic=s.kaic,
            feed_type=feed,
            description=s.description,
            trip_amps=s.trip_amps,
        ))
    return result
