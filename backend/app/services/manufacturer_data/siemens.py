"""Siemens breaker product catalog — valid configurations.

Covers: 3WL (ACB), 3VA (MCCB), SENTRON 3VL
"""

SIEMENS_BREAKER_CATALOG = {
    # 3WL Air Circuit Breakers
    "3WL1106": {"type": "ACB", "frames": [630], "icu_kA_480V": {"N": 65, "H": 85, "L": 100}},
    "3WL1108": {"type": "ACB", "frames": [800], "icu_kA_480V": {"N": 65, "H": 85, "L": 100}},
    "3WL1110": {"type": "ACB", "frames": [1000], "icu_kA_480V": {"N": 65, "H": 85, "L": 100}},
    "3WL1112": {"type": "ACB", "frames": [1250], "icu_kA_480V": {"N": 65, "H": 85, "L": 100}},
    "3WL1116": {"type": "ACB", "frames": [1600], "icu_kA_480V": {"N": 65, "H": 85, "L": 100}},
    "3WL1120": {"type": "ACB", "frames": [2000], "icu_kA_480V": {"N": 65, "H": 100, "L": 150}},
    "3WL1125": {"type": "ACB", "frames": [2500], "icu_kA_480V": {"N": 65, "H": 100, "L": 150}},
    "3WL1132": {"type": "ACB", "frames": [3200], "icu_kA_480V": {"N": 65, "H": 100, "L": 150}},
    "3WL1140": {"type": "ACB", "frames": [4000], "icu_kA_480V": {"N": 65, "H": 100, "L": 150}},
    "3WL1150": {"type": "ACB", "frames": [5000], "icu_kA_480V": {"H": 100, "L": 150}},
    "3WL1163": {"type": "ACB", "frames": [6300], "icu_kA_480V": {"H": 100, "L": 150}},

    # 3VA Molded Case Circuit Breakers
    "3VA1": {"type": "MCCB", "frames": [16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160], "icu_kA_480V": {"1": 25, "2": 55, "5": 65}},
    "3VA2": {"type": "MCCB", "frames": [100, 125, 160, 200, 250], "icu_kA_480V": {"1": 55, "2": 65, "5": 85, "7": 100}},
    "3VA5": {"type": "MCCB", "frames": [250, 320, 400], "icu_kA_480V": {"2": 65, "5": 85, "7": 100}},
    "3VA6": {"type": "MCCB", "frames": [400, 500, 630], "icu_kA_480V": {"2": 65, "5": 85, "7": 100}},
    "3VA7": {"type": "MCCB", "frames": [630, 800, 1000, 1250, 1600], "icu_kA_480V": {"2": 65, "5": 85, "7": 100}},

    # SENTRON 3VL (legacy but still common)
    "3VL1": {"type": "MCCB", "frames": [16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160], "icu_kA_480V": {"standard": 65}},
    "3VL2": {"type": "MCCB", "frames": [100, 125, 160, 200, 250], "icu_kA_480V": {"standard": 65}},
    "3VL3": {"type": "MCCB", "frames": [250, 320, 400], "icu_kA_480V": {"standard": 65}},
    "3VL4": {"type": "MCCB", "frames": [400, 500, 630], "icu_kA_480V": {"standard": 65}},
    "3VL5": {"type": "MCCB", "frames": [630, 800], "icu_kA_480V": {"standard": 65}},
    "3VL6": {"type": "MCCB", "frames": [800, 1000, 1200, 1600], "icu_kA_480V": {"standard": 65}},
}


def validate_siemens_breaker(model: str, frame: int) -> dict:
    """Validate a Siemens breaker configuration."""
    if model not in SIEMENS_BREAKER_CATALOG:
        return {"valid": False, "issues": [f"Unknown Siemens model '{model}'"]}

    catalog = SIEMENS_BREAKER_CATALOG[model]
    issues = []

    if frame not in catalog["frames"]:
        issues.append(
            f"Siemens {model} frame range is {min(catalog['frames'])}-{max(catalog['frames'])}A. "
            f"{frame}A is not a valid frame size."
        )

    return {"valid": len(issues) == 0, "issues": issues}
