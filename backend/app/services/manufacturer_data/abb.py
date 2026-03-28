"""ABB breaker product catalog — valid configurations for Emax 2 and Tmax XT series.

Data sourced from ABB low-voltage product catalogs.
Used to validate that extracted breaker configurations are real, orderable products.
"""

# =============================================================================
# ABB Emax 2 Air Circuit Breakers (ACBs)
# =============================================================================

EMAX2_CATALOG = {
    "E1.2": {
        "type": "ACB",
        "frames": [800, 1000, 1250, 1600],
        "icu_kA_480V": {"N": 42, "S": 50, "H": 65, "L": 85, "V": 100},
        "poles": [3, 4],
        "mounting": ["fixed", "drawout"],
        "trip_units": ["Ekip Touch", "Ekip Hi-Touch", "Ekip G Hi-Touch", "Ekip Synchrocheck"],
    },
    "E2.2": {
        "type": "ACB",
        "frames": [800, 1000, 1250, 1600, 2000, 2500],
        "icu_kA_480V": {"N": 50, "S": 65, "H": 85, "L": 100, "V": 130},
        "poles": [3, 4],
        "mounting": ["fixed", "drawout"],
        "trip_units": ["Ekip Touch", "Ekip Hi-Touch", "Ekip G Hi-Touch", "Ekip Synchrocheck"],
    },
    "E4.2": {
        "type": "ACB",
        "frames": [1600, 2000, 2500, 3200, 4000],
        "icu_kA_480V": {"N": 50, "S": 65, "H": 85, "L": 100, "V": 130},
        "poles": [3, 4],
        "mounting": ["fixed", "drawout"],
        "trip_units": ["Ekip Touch", "Ekip Hi-Touch", "Ekip G Hi-Touch", "Ekip Synchrocheck"],
    },
    "E6.2": {
        "type": "ACB",
        "frames": [3200, 4000, 5000, 6300],
        "icu_kA_480V": {"N": 50, "S": 65, "H": 85, "L": 100, "V": 130},
        "poles": [3, 4],
        "mounting": ["fixed", "drawout"],
        "trip_units": ["Ekip Touch", "Ekip Hi-Touch", "Ekip G Hi-Touch", "Ekip Synchrocheck"],
    },
}


# =============================================================================
# ABB Tmax XT Molded Case Circuit Breakers (MCCBs)
# =============================================================================

TMAX_XT_CATALOG = {
    "XT1": {
        "type": "MCCB",
        "frames": [15, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160],
        "icu_kA_480V": {"B": 18, "C": 25, "N": 36, "S": 50, "H": 65},
        "poles": [3, 4],
        "mounting": ["fixed"],
        "trip_units": ["TMD", "TMA", "Ekip LS/I", "Ekip Touch"],
    },
    "XT2": {
        "type": "MCCB",
        "frames": [15, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160],
        "icu_kA_480V": {"B": 18, "C": 25, "N": 36, "S": 50, "H": 65, "L": 100, "V": 150},
        "poles": [3, 4],
        "mounting": ["fixed", "plug-in"],
        "trip_units": ["TMD", "TMA", "TMF", "Ekip LS/I", "Ekip Touch", "Ekip Touch Measuring"],
    },
    "XT3": {
        "type": "MCCB",
        "frames": [250],
        "icu_kA_480V": {"N": 36},
        "poles": [3, 4],
        "mounting": ["fixed"],
        "trip_units": ["TMA"],
    },
    "XT4": {
        "type": "MCCB",
        "frames": [100, 125, 160, 200, 250],
        "icu_kA_480V": {"N": 36, "S": 50, "H": 65, "L": 100, "V": 150},
        "poles": [3, 4],
        "mounting": ["fixed", "plug-in"],
        "trip_units": ["TMD", "TMA", "Ekip LS/I", "Ekip Touch", "Ekip Touch Measuring"],
    },
    "XT5": {
        "type": "MCCB",
        "frames": [250, 320, 400, 500, 630],
        "icu_kA_480V": {"N": 36, "S": 50, "H": 65, "L": 100, "V": 150},
        "poles": [3, 4],
        "mounting": ["fixed", "plug-in"],
        "trip_units": ["Ekip LS/I", "Ekip Touch", "Ekip Touch Measuring"],
    },
    "XT6": {
        "type": "MCCB",
        "frames": [630, 800],
        "icu_kA_480V": {"N": 36, "S": 50, "H": 65, "L": 100},
        "poles": [3, 4],
        "mounting": ["fixed", "plug-in"],
        "trip_units": ["Ekip Touch", "Ekip Touch Measuring"],
    },
    "XT7": {
        "type": "MCCB",
        "frames": [630, 800, 1000, 1250, 1600],
        "icu_kA_480V": {"N": 36, "S": 50, "H": 65, "L": 100, "V": 150},
        "poles": [3, 4],
        "mounting": ["fixed", "plug-in", "drawout"],
        "trip_units": ["Ekip Touch", "Ekip Touch Measuring", "Ekip Hi-Touch"],
    },
}

# Combined catalog for lookups
ABB_BREAKER_CATALOG = {**EMAX2_CATALOG, **TMAX_XT_CATALOG}


# =============================================================================
# Interrupting capacity suffix meanings
# =============================================================================

ICU_SUFFIX_MAP = {
    "B": "Basic",
    "C": "Standard",
    "N": "Normal",
    "S": "High (Standard)",
    "H": "High",
    "L": "Very High (Limiting)",
    "V": "Ultra High",
}


# =============================================================================
# Validation Functions
# =============================================================================

def parse_abb_model(designation: str) -> dict | None:
    """Parse an ABB breaker designation into series, suffix, and frame size.

    Examples:
        "E6.2H4000" -> {"series": "E6.2", "suffix": "H", "frame": 4000}
        "XT7H 1000" -> {"series": "XT7", "suffix": "H", "frame": 1000}
        "XT2N125"   -> {"series": "XT2", "suffix": "N", "frame": 125}
    """
    import re

    # E-series: E1.2, E2.2, E4.2, E6.2
    m = re.match(r'(E\d\.\d)\s*([BNCSHLV])?\s*(\d+)', designation)
    if m:
        return {"series": m.group(1), "suffix": m.group(2) or "", "frame": int(m.group(3))}

    # XT-series
    m = re.match(r'(XT\d)\s*([BNCSHLV])?\s*(\d+)', designation)
    if m:
        return {"series": m.group(1), "suffix": m.group(2) or "", "frame": int(m.group(3))}

    return None


def validate_abb_breaker(designation: str) -> dict:
    """Validate an ABB breaker designation against the product catalog.

    Returns: {
        "valid": bool,
        "issues": [str],  # list of problems found
        "info": {str},    # additional product info
    }
    """
    parsed = parse_abb_model(designation)
    if not parsed:
        return {"valid": False, "issues": [f"Cannot parse '{designation}' as ABB breaker model"], "info": {}}

    series = parsed["series"]
    suffix = parsed["suffix"]
    frame = parsed["frame"]

    if series not in ABB_BREAKER_CATALOG:
        return {"valid": False, "issues": [f"Unknown ABB series '{series}'"], "info": {}}

    catalog = ABB_BREAKER_CATALOG[series]
    issues = []
    info = {"type": catalog["type"], "series": series}

    # Check frame size
    if frame not in catalog["frames"]:
        valid_frames = catalog["frames"]
        # Find the correct series for this frame
        suggested_series = None
        for s, c in ABB_BREAKER_CATALOG.items():
            if frame in c["frames"] and c["type"] == catalog["type"]:
                suggested_series = s
                break

        issues.append(
            f"{series} frame range is {min(valid_frames)}-{max(valid_frames)}A. "
            f"{frame}A is not a valid {series} frame size."
            + (f" Did you mean {suggested_series}?" if suggested_series else "")
        )

    # Check interrupting suffix
    if suffix and suffix in catalog["icu_kA_480V"]:
        info["icu_kA"] = catalog["icu_kA_480V"][suffix]
        info["icu_suffix"] = ICU_SUFFIX_MAP.get(suffix, suffix)
    elif suffix:
        valid_suffixes = list(catalog["icu_kA_480V"].keys())
        issues.append(f"Suffix '{suffix}' not valid for {series}. Valid: {valid_suffixes}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "info": info,
    }


def get_abb_icu(series: str, suffix: str) -> int | None:
    """Get the interrupting capacity in kA at 480V for a given series and suffix."""
    if series in ABB_BREAKER_CATALOG:
        return ABB_BREAKER_CATALOG[series]["icu_kA_480V"].get(suffix)
    return None
