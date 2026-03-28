"""Eaton breaker product catalog — valid configurations for major product lines.

Covers: NRX, Magnum, Digitrip, Series C, Series G, HFD, FD, JD, KD, LD, MD, ND
"""

EATON_BREAKER_CATALOG = {
    # Magnum DS Low-Voltage Power Circuit Breakers
    "Magnum DS": {
        "type": "LVCB",
        "frames": [800, 1200, 1600, 2000, 2500, 3000, 3200, 4000, 5000, 6000],
        "icu_kA_480V": {"standard": 65, "high": 100, "extra_high": 200},
        "poles": [3, 4],
        "mounting": ["fixed", "drawout"],
    },
    # NRX Low-Voltage Power Circuit Breakers
    "NRX": {
        "type": "LVCB",
        "frames": [400, 600, 800, 1200, 1600, 2000, 2500, 3000, 3200, 4000],
        "icu_kA_480V": {"standard": 65, "high": 100},
        "poles": [3, 4],
        "mounting": ["fixed", "drawout"],
    },
    # Series C Industrial MCCBs
    "HFD": {"type": "MCCB", "frames": [15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100], "icu_kA_480V": {"standard": 100}},
    "FD": {"type": "MCCB", "frames": [15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 125, 150], "icu_kA_480V": {"standard": 35}},
    "FDB": {"type": "MCCB", "frames": [15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 125, 150], "icu_kA_480V": {"standard": 65}},
    "JD": {"type": "MCCB", "frames": [70, 80, 90, 100, 125, 150, 175, 200, 225, 250], "icu_kA_480V": {"standard": 35}},
    "JDB": {"type": "MCCB", "frames": [70, 80, 90, 100, 125, 150, 175, 200, 225, 250], "icu_kA_480V": {"standard": 65}},
    "KD": {"type": "MCCB", "frames": [125, 150, 175, 200, 225, 250, 300, 350, 400], "icu_kA_480V": {"standard": 35}},
    "KDB": {"type": "MCCB", "frames": [125, 150, 175, 200, 225, 250, 300, 350, 400], "icu_kA_480V": {"standard": 65}},
    "LD": {"type": "MCCB", "frames": [300, 350, 400, 500, 600], "icu_kA_480V": {"standard": 35}},
    "LDB": {"type": "MCCB", "frames": [300, 350, 400, 500, 600], "icu_kA_480V": {"standard": 65}},
    "MD": {"type": "MCCB", "frames": [500, 600, 700, 800], "icu_kA_480V": {"standard": 50}},
    "MDB": {"type": "MCCB", "frames": [500, 600, 700, 800], "icu_kA_480V": {"standard": 65}},
    "ND": {"type": "MCCB", "frames": [600, 700, 800, 1000, 1200], "icu_kA_480V": {"standard": 50}},
    "NDB": {"type": "MCCB", "frames": [600, 700, 800, 1000, 1200], "icu_kA_480V": {"standard": 65}},
    "PD": {"type": "MCCB", "frames": [1200, 1600, 2000], "icu_kA_480V": {"standard": 50}},
    "PDB": {"type": "MCCB", "frames": [1200, 1600, 2000], "icu_kA_480V": {"standard": 65}},
    "RD": {"type": "MCCB", "frames": [1600, 2000, 2500, 3000], "icu_kA_480V": {"standard": 65}},
}


def validate_eaton_breaker(model: str, frame: int) -> dict:
    """Validate an Eaton breaker configuration."""
    if model not in EATON_BREAKER_CATALOG:
        return {"valid": False, "issues": [f"Unknown Eaton model '{model}'"]}

    catalog = EATON_BREAKER_CATALOG[model]
    issues = []

    if frame not in catalog["frames"]:
        issues.append(
            f"Eaton {model} frame range is {min(catalog['frames'])}-{max(catalog['frames'])}A. "
            f"{frame}A is not a valid frame size."
        )

    return {"valid": len(issues) == 0, "issues": issues}
