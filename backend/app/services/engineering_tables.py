"""NEC and engineering reference tables — single source of truth for all calculations.

All data from NEC 2023 (NFPA 70-2023) unless otherwise noted.
"""

# =============================================================================
# NEC 310.16 — Ampacity of Insulated Conductors (Not More Than 3 Current-Carrying
# Conductors in Raceway, Cable, or Earth, Based on Ambient Temp of 30°C / 86°F)
# =============================================================================

# Key = conductor size (AWG or kcmil as string), Value = ampacity
# Copper conductors only

NEC_310_16_60C = {
    "14": 15, "12": 20, "10": 30, "8": 40, "6": 55, "4": 70, "3": 85,
    "2": 95, "1": 110, "1/0": 125, "2/0": 145, "3/0": 165, "4/0": 195,
    "250": 215, "300": 240, "350": 260, "400": 280, "500": 320,
    "600": 355, "700": 385, "750": 400, "800": 410, "900": 435,
    "1000": 455, "1250": 495, "1500": 520, "1750": 545, "2000": 560,
}

NEC_310_16_75C = {
    "14": 20, "12": 25, "10": 35, "8": 50, "6": 65, "4": 85, "3": 100,
    "2": 115, "1": 130, "1/0": 150, "2/0": 175, "3/0": 200, "4/0": 230,
    "250": 255, "300": 285, "350": 310, "400": 335, "500": 380,
    "600": 420, "700": 460, "750": 475, "800": 490, "900": 520,
    "1000": 545, "1250": 590, "1500": 625, "1750": 650, "2000": 665,
}

NEC_310_16_90C = {
    "14": 25, "12": 30, "10": 40, "8": 55, "6": 75, "4": 95, "3": 115,
    "2": 130, "1": 145, "1/0": 170, "2/0": 195, "3/0": 225, "4/0": 260,
    "250": 290, "300": 320, "350": 350, "400": 380, "500": 430,
    "600": 475, "700": 520, "750": 535, "800": 555, "900": 585,
    "1000": 615, "1250": 665, "1500": 705, "1750": 735, "2000": 750,
}

# Aluminum conductors at 75°C
NEC_310_16_75C_AL = {
    "12": 20, "10": 30, "8": 40, "6": 50, "4": 65, "3": 75,
    "2": 90, "1": 100, "1/0": 120, "2/0": 135, "3/0": 155, "4/0": 180,
    "250": 205, "300": 230, "350": 250, "400": 270, "500": 310,
    "600": 340, "700": 375, "750": 385, "800": 395, "900": 425,
    "1000": 445, "1250": 485, "1500": 520, "1750": 545, "2000": 560,
}


# =============================================================================
# Metric (mm²) to AWG/kcmil Conversion
# =============================================================================

# =============================================================================
# IEC 60364-5-52 — Ampacity for Metric Cables (Copper, PVC insulated)
# Installation method C (clipped direct to wall/tray) at 30°C ambient
# These are the ACTUAL IEC ratings — no conversion to AWG needed.
# =============================================================================

IEC_AMPACITY_3PHASE = {
    # mm² : amps (3-core cable or 3 single-core in trefoil, copper, PVC, 30°C)
    1.5: 15, 2.5: 21, 4: 28, 6: 36, 10: 50, 16: 66, 25: 84,
    35: 104, 50: 125, 70: 160, 95: 194, 120: 225, 150: 260,
    185: 297, 240: 346, 300: 394, 400: 456, 500: 528, 630: 612,
}

IEC_AMPACITY_XLPE_3PHASE = {
    # mm² : amps (3-core or trefoil, copper, XLPE/EPR, 30°C)
    1.5: 19, 2.5: 27, 4: 36, 6: 46, 10: 65, 16: 87, 25: 114,
    35: 141, 50: 182, 70: 226, 95: 275, 120: 321, 150: 372,
    185: 427, 240: 500, 300: 576, 400: 662, 500: 764, 630: 885,
}

# NOTE: mm² to AWG/kcmil is an APPROXIMATION — these are NOT exact equivalents.
# 300mm² ≈ 592 kcmil (NOT 600 kcmil). Using this for NEC ampacity lookup is
# DANGEROUS because the actual cross-section differs. Only use for display/reference.
# For NEC compliance, the actual conductor properties must be verified.
MM2_APPROXIMATE_AWG_LABEL = {
    1.5: "~16 AWG", 2.5: "~14 AWG", 4: "~12 AWG", 6: "~10 AWG",
    10: "~8 AWG", 16: "~6 AWG", 25: "~4 AWG", 35: "~2 AWG",
    50: "~1/0 AWG", 70: "~2/0 AWG", 95: "~3/0 AWG", 120: "~4/0 AWG",
    150: "~300 kcmil", 185: "~350 kcmil", 240: "~500 kcmil",
    300: "~600 kcmil", 400: "~750 kcmil", 500: "~1000 kcmil",
}


def mm2_ampacity(mm2: float, insulation: str = "pvc") -> int:
    """Get IEC 60364 ampacity for a metric cable size. Uses actual IEC tables, not NEC conversion."""
    table = IEC_AMPACITY_XLPE_3PHASE if insulation.lower() in ("xlpe", "epr", "xhhw") else IEC_AMPACITY_3PHASE
    if mm2 in table:
        return table[mm2]
    # Find closest standard size
    closest = min(table.keys(), key=lambda x: abs(x - mm2))
    return table[closest]


def mm2_to_approximate_label(mm2: float) -> str:
    """Get approximate AWG/kcmil label for display only — NOT for engineering calculations."""
    if mm2 in MM2_APPROXIMATE_AWG_LABEL:
        return MM2_APPROXIMATE_AWG_LABEL[mm2]
    closest = min(MM2_APPROXIMATE_AWG_LABEL.keys(), key=lambda x: abs(x - mm2))
    return MM2_APPROXIMATE_AWG_LABEL[closest]


# Keep these for backward compatibility but mark as approximate
def mm2_to_awg(mm2: float) -> str:
    """APPROXIMATE conversion — for display reference only, not NEC calculations."""
    label = mm2_to_approximate_label(mm2)
    return label.replace("~", "").strip()


def mm2_ampacity_75c(mm2: float) -> int:
    """Get ampacity for metric cable — uses IEC tables (not NEC approximation)."""
    return mm2_ampacity(mm2)


# =============================================================================
# NEC 240.6(A) — Standard Ampere Ratings for Fuses and Inverse Time Circuit Breakers
# =============================================================================

STANDARD_BREAKER_SIZES = [
    15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100,
    110, 125, 150, 175, 200, 225, 250, 300, 350, 400, 450,
    500, 600, 700, 800, 1000, 1200, 1600, 2000, 2500, 3000,
    4000, 5000, 6000,
]


def next_standard_size(amps: float) -> int:
    """Return the next standard breaker size at or above the given amperage."""
    for size in STANDARD_BREAKER_SIZES:
        if size >= amps:
            return size
    return STANDARD_BREAKER_SIZES[-1]


# =============================================================================
# NEC 240.4(D) — Small Conductors (max OCPD for #14, #12, #10)
# =============================================================================

NEC_240_4_D = {
    "14": 15,
    "12": 20,
    "10": 30,
}


# =============================================================================
# NEC 250.122 — Size of Equipment Grounding Conductors
# =============================================================================

# Key = OCPD rating (amps), Value = minimum EGC size (AWG/kcmil, copper)
NEC_250_122 = {
    15: "14", 20: "12", 30: "10", 40: "10", 50: "10", 60: "10",
    100: "8", 200: "6", 300: "4", 400: "3", 500: "2", 600: "1",
    800: "1/0", 1000: "2/0", 1200: "3/0", 1600: "4/0",
    2000: "250", 2500: "350", 3000: "400", 4000: "500",
    5000: "700", 6000: "800",
}


def min_egc_size(ocpd_amps: int) -> str:
    """Get minimum equipment grounding conductor size for a given OCPD rating."""
    for rating in sorted(NEC_250_122.keys()):
        if rating >= ocpd_amps:
            return NEC_250_122[rating]
    return "800"  # Maximum in table


# =============================================================================
# NEC 450.3(B) — Maximum Rating of Overcurrent Protection for Transformers
# (Over 600 Volts, Nominal — for dry-type transformers 600V and below)
# =============================================================================

# With secondary protection: primary max = 250% of primary FLA
# Without secondary protection: primary max = 125% of primary FLA (next standard up)
# Secondary protection: max 125% of secondary FLA (next standard up)

NEC_450_3_PRIMARY_WITH_SECONDARY = 2.50  # 250%
NEC_450_3_PRIMARY_WITHOUT_SECONDARY = 1.25  # 125%
NEC_450_3_SECONDARY = 1.25  # 125%


def transformer_fla(kva: float, voltage: float, phases: int = 3) -> float:
    """Calculate transformer full-load amps."""
    if phases == 3:
        return (kva * 1000) / (voltage * 1.732)
    else:
        return (kva * 1000) / voltage


def transformer_max_primary_ocpd(kva: float, primary_voltage: float, has_secondary_protection: bool = True) -> int:
    """Calculate maximum primary overcurrent protection per NEC 450.3(B)."""
    fla = transformer_fla(kva, primary_voltage)
    if has_secondary_protection:
        max_amps = fla * NEC_450_3_PRIMARY_WITH_SECONDARY
    else:
        max_amps = fla * NEC_450_3_PRIMARY_WITHOUT_SECONDARY
    return next_standard_size(max_amps)


def transformer_max_secondary_ocpd(kva: float, secondary_voltage: float) -> int:
    """Calculate maximum secondary overcurrent protection per NEC 450.3(B)."""
    fla = transformer_fla(kva, secondary_voltage)
    max_amps = fla * NEC_450_3_SECONDARY
    return next_standard_size(max_amps)


# =============================================================================
# NEC 110.26(A)(1) — Working Space Clearances
# =============================================================================

# Key = (voltage_range, condition), Value = minimum clearance in inches
# Conditions: 1 = live parts one side only, 2 = live parts one side + grounded other,
#             3 = live parts both sides
NEC_110_26_CLEARANCES = {
    # 0-150V
    ("0-150", 1): 36, ("0-150", 2): 36, ("0-150", 3): 36,
    # 151-600V
    ("151-600", 1): 36, ("151-600", 2): 42, ("151-600", 3): 48,
    # 601-2500V
    ("601-2500", 1): 36, ("601-2500", 2): 48, ("601-2500", 3): 60,
}

# Width: 30" or width of equipment, whichever is greater
NEC_110_26_MIN_WIDTH = 30  # inches
# Headroom: 6'-6" or height of equipment, whichever is greater
NEC_110_26_MIN_HEADROOM = 78  # inches (6.5 feet)


def required_clearance(voltage: int, condition: int = 2) -> int:
    """Get required working space clearance in inches per NEC 110.26."""
    if voltage <= 150:
        vrange = "0-150"
    elif voltage <= 600:
        vrange = "151-600"
    else:
        vrange = "601-2500"
    return NEC_110_26_CLEARANCES.get((vrange, condition), 48)


# =============================================================================
# NEC Chapter 9 Table 4 — Conduit Cross-Section Areas (in²)
# =============================================================================

# Trade size → internal area in square inches
CONDUIT_AREA_EMT = {
    "1/2": 0.304, "3/4": 0.533, "1": 0.864, "1-1/4": 1.496, "1-1/2": 2.036,
    "2": 3.356, "2-1/2": 5.858, "3": 8.846, "3-1/2": 11.545, "4": 14.753,
}

CONDUIT_AREA_IMC = {
    "1/2": 0.342, "3/4": 0.586, "1": 0.959, "1-1/4": 1.647, "1-1/2": 2.225,
    "2": 3.630, "2-1/2": 5.135, "3": 7.922, "3-1/2": 10.584, "4": 13.631,
}

CONDUIT_AREA_RMC = {
    "1/2": 0.314, "3/4": 0.549, "1": 0.887, "1-1/4": 1.526, "1-1/2": 2.071,
    "2": 3.408, "2-1/2": 4.866, "3": 7.499, "3-1/2": 10.010, "4": 12.882,
}

# NEC Chapter 9 Table 1 — Conduit fill percentages
CONDUIT_FILL_PERCENT = {
    1: 0.53,  # 53% for 1 conductor
    2: 0.31,  # 31% for 2 conductors
    3: 0.40,  # 40% for 3 or more
}


def max_conduit_fill(conduit_size: str, conduit_type: str = "EMT", num_conductors: int = 3) -> float:
    """Get maximum allowable fill area in square inches."""
    areas = {"EMT": CONDUIT_AREA_EMT, "IMC": CONDUIT_AREA_IMC, "RMC": CONDUIT_AREA_RMC}
    conduit_area = areas.get(conduit_type, CONDUIT_AREA_EMT).get(conduit_size, 0)
    fill_pct = CONDUIT_FILL_PERCENT.get(min(num_conductors, 3), 0.40)
    return conduit_area * fill_pct


# =============================================================================
# NEC Chapter 9 Table 5 — Conductor Cross-Section Areas (in²)
# For THHN/THWN-2 (most common in commercial/industrial)
# =============================================================================

CONDUCTOR_AREA_THHN = {
    "14": 0.0097, "12": 0.0133, "10": 0.0211, "8": 0.0366,
    "6": 0.0507, "4": 0.0824, "3": 0.0973, "2": 0.1158,
    "1": 0.1562, "1/0": 0.1855, "2/0": 0.2223, "3/0": 0.2679,
    "4/0": 0.3237, "250": 0.3970, "300": 0.4608, "350": 0.5242,
    "400": 0.5863, "500": 0.7073, "600": 0.8676, "700": 0.9887,
    "750": 1.0496, "800": 1.1085, "900": 1.2311, "1000": 1.3478,
}

CONDUCTOR_AREA_XHHW = {
    "14": 0.0097, "12": 0.0133, "10": 0.0211, "8": 0.0437,
    "6": 0.0590, "4": 0.0814, "3": 0.0962, "2": 0.1146,
    "1": 0.1534, "1/0": 0.1825, "2/0": 0.2190, "3/0": 0.2642,
    "4/0": 0.3197, "250": 0.3904, "300": 0.4536, "350": 0.5166,
    "400": 0.5782, "500": 0.6984, "600": 0.8709, "700": 0.9923,
    "750": 1.0532, "800": 1.1122, "900": 1.2351, "1000": 1.3519,
}


# =============================================================================
# NEC Chapter 9 Table 9 — Conductor AC Resistance at 75°C (ohms per 1000ft)
# Copper, in steel conduit
# =============================================================================

CONDUCTOR_RESISTANCE_CU_STEEL = {
    "14": 3.140, "12": 1.980, "10": 1.240, "8": 0.786,
    "6": 0.510, "4": 0.321, "3": 0.254, "2": 0.201,
    "1": 0.160, "1/0": 0.128, "2/0": 0.102, "3/0": 0.0817,
    "4/0": 0.0651, "250": 0.0552, "300": 0.0464, "350": 0.0399,
    "400": 0.0353, "500": 0.0293, "600": 0.0252, "700": 0.0224,
    "750": 0.0214, "800": 0.0206, "900": 0.0191, "1000": 0.0180,
}


def voltage_drop_3ph(length_ft: float, current_amps: float, conductor_size: str, voltage: int = 480) -> float:
    """Calculate 3-phase voltage drop percentage.

    Formula: Vd% = (1.732 × L × I × R) / (V × 1000) × 100
    Where L = one-way length in feet, R = resistance per 1000ft
    """
    r = CONDUCTOR_RESISTANCE_CU_STEEL.get(conductor_size, 0)
    if r == 0 or voltage == 0:
        return 0.0
    vd = (1.732 * length_ft * current_amps * r) / (voltage * 1000) * 100
    return round(vd, 2)


def voltage_drop_1ph(length_ft: float, current_amps: float, conductor_size: str, voltage: int = 208) -> float:
    """Calculate single-phase voltage drop percentage."""
    r = CONDUCTOR_RESISTANCE_CU_STEEL.get(conductor_size, 0)
    if r == 0 or voltage == 0:
        return 0.0
    vd = (2 * length_ft * current_amps * r) / (voltage * 1000) * 100
    return round(vd, 2)


# =============================================================================
# Fault Current Estimation
# =============================================================================

def transformer_secondary_fault_current(kva: float, secondary_voltage: float,
                                          impedance_pct: float, phases: int = 3) -> float:
    """Estimate available fault current on transformer secondary.

    AFC = FLA / (Z% / 100)
    """
    fla = transformer_fla(kva, secondary_voltage, phases)
    if impedance_pct <= 0:
        return 0.0
    return fla / (impedance_pct / 100)
