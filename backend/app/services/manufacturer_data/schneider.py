"""Schneider Electric breaker product catalog — valid configurations.

Covers: Masterpact, Compact NSX, Compact NS, PowerPact
"""

SCHNEIDER_BREAKER_CATALOG = {
    # Masterpact MTZ ACBs
    "MTZ1": {
        "type": "ACB",
        "frames": [630, 800, 1000, 1250, 1600],
        "icu_kA_480V": {"N": 42, "H": 65, "L": 100, "HL": 150},
        "poles": [3, 4],
    },
    "MTZ2": {
        "type": "ACB",
        "frames": [800, 1000, 1250, 1600, 2000, 2500, 3200, 4000],
        "icu_kA_480V": {"N": 65, "H": 85, "L": 100, "HL": 150},
        "poles": [3, 4],
    },
    "MTZ3": {
        "type": "ACB",
        "frames": [4000, 5000, 6300],
        "icu_kA_480V": {"H": 85, "L": 100, "HL": 150},
        "poles": [3, 4],
    },
    # Compact NSX MCCBs
    "NSX100": {"type": "MCCB", "frames": [16, 25, 32, 40, 50, 63, 80, 100], "icu_kA_480V": {"B": 25, "F": 36, "N": 50, "H": 70, "S": 100, "L": 150}},
    "NSX160": {"type": "MCCB", "frames": [80, 100, 125, 160], "icu_kA_480V": {"B": 25, "F": 36, "N": 50, "H": 70, "S": 100, "L": 150}},
    "NSX250": {"type": "MCCB", "frames": [100, 125, 160, 200, 250], "icu_kA_480V": {"B": 25, "F": 36, "N": 50, "H": 70, "S": 100, "L": 150}},
    "NSX400": {"type": "MCCB", "frames": [250, 320, 400], "icu_kA_480V": {"N": 50, "H": 70, "S": 100, "L": 150}},
    "NSX630": {"type": "MCCB", "frames": [400, 500, 630], "icu_kA_480V": {"N": 50, "H": 70, "S": 100, "L": 150}},
    # Compact NS MCCBs (legacy but still common)
    "NS630": {"type": "MCCB", "frames": [400, 500, 630], "icu_kA_480V": {"N": 50, "H": 70, "L": 150}},
    "NS800": {"type": "MCCB", "frames": [630, 700, 800], "icu_kA_480V": {"N": 50, "H": 70, "L": 150}},
    "NS1250": {"type": "MCCB", "frames": [800, 1000, 1250], "icu_kA_480V": {"N": 50, "H": 70, "L": 150}},
    "NS1600": {"type": "MCCB", "frames": [1250, 1600], "icu_kA_480V": {"N": 50, "H": 70, "L": 150}},
    # PowerPact (North America)
    "PowerPact H": {"type": "MCCB", "frames": [15, 20, 25, 30, 40, 50, 60, 70, 80, 100, 125, 150], "icu_kA_480V": {"standard": 65}},
    "PowerPact J": {"type": "MCCB", "frames": [150, 175, 200, 225, 250], "icu_kA_480V": {"standard": 65}},
    "PowerPact L": {"type": "MCCB", "frames": [250, 300, 350, 400, 500, 600], "icu_kA_480V": {"standard": 65}},
    "PowerPact M": {"type": "MCCB", "frames": [400, 500, 600, 700, 800], "icu_kA_480V": {"standard": 50}},
    "PowerPact P": {"type": "MCCB", "frames": [600, 800, 1000, 1200], "icu_kA_480V": {"standard": 50}},
    "PowerPact R": {"type": "MCCB", "frames": [1200, 1600, 2000, 2500], "icu_kA_480V": {"standard": 65}},
}


def validate_schneider_breaker(model: str, frame: int) -> dict:
    """Validate a Schneider Electric breaker configuration."""
    if model not in SCHNEIDER_BREAKER_CATALOG:
        return {"valid": False, "issues": [f"Unknown Schneider model '{model}'"]}

    catalog = SCHNEIDER_BREAKER_CATALOG[model]
    issues = []

    if frame not in catalog["frames"]:
        issues.append(
            f"Schneider {model} frame range is {min(catalog['frames'])}-{max(catalog['frames'])}A. "
            f"{frame}A is not a valid frame size."
        )

    return {"valid": len(issues) == 0, "issues": issues}
