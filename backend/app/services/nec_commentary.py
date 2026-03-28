"""NEC code commentary — explains why each article matters in plain language.

Used to populate the "Code Reference" section when a finding is expanded.
"""

NEC_COMMENTARY = {
    "NEC 110.2": {
        "title": "Approval",
        "text": "Conductors and equipment required or permitted shall be acceptable only if approved. In practice, this means UL listed or recognized for US installations.",
        "why_it_matters": "Equipment without proper UL listing cannot be legally installed in the US.",
    },
    "NEC 110.3": {
        "title": "Examination, Identification, Installation, Use, and Product Listing",
        "text": "Listed or labeled equipment shall be installed and used in accordance with any instructions included in the listing or labeling.",
        "why_it_matters": "Using equipment outside its listed conditions voids the certification and may create safety hazards.",
    },
    "NEC 110.9": {
        "title": "Interrupting Rating",
        "text": "Equipment intended to interrupt current at fault levels shall have an interrupting rating not less than the nominal circuit voltage and the current that is available at the line terminals.",
        "why_it_matters": "A breaker that can't interrupt the available fault current may explode, causing arc flash, fire, and potentially fatal injuries.",
    },
    "NEC 110.10": {
        "title": "Circuit Impedance, Short-Circuit Current Ratings, and Other Characteristics",
        "text": "The overcurrent protective devices, the total impedance, the equipment short-circuit current ratings, and other characteristics of the circuit to be protected shall be coordinated to permit the circuit protective devices to clear a fault.",
        "why_it_matters": "The entire system from utility to load must be rated for the fault current. One weak link can cause cascading failure.",
    },
    "NEC 110.16": {
        "title": "Arc-Flash Hazard Warning",
        "text": "Electrical equipment that is likely to require examination, adjustment, servicing, or maintenance while energized shall be field marked to warn qualified persons of potential arc flash hazards.",
        "why_it_matters": "Workers need to know the arc flash risk before opening equipment. Missing labels can lead to inadequate PPE and severe burns.",
    },
    "NEC 110.24": {
        "title": "Available Fault Current",
        "text": "Service equipment in other than dwelling units shall be legibly marked in the field with the maximum available fault current, the date the calculation was performed, and be of sufficient durability.",
        "why_it_matters": "Field personnel need to know the fault current to verify equipment ratings and select proper PPE. Required since 2011 NEC.",
    },
    "NEC 110.26": {
        "title": "Spaces About Electrical Equipment",
        "text": "Access and working space shall be provided about all electrical equipment to permit ready and safe operation and maintenance. Minimum 36\" depth for 480V Condition 1, 42\" for Condition 2.",
        "why_it_matters": "Inadequate clearance prevents safe maintenance and creates arc flash risk. This is frequently the most contentious issue in modular data centers.",
    },
    "NEC 210.5": {
        "title": "Identification for Branch Circuits",
        "text": "The grounded conductor of a branch circuit shall be identified by a continuous white or gray outer finish. Ungrounded conductors shall be identified by phase.",
        "why_it_matters": "Proper phase identification prevents cross-phase connections that can cause equipment damage and create shock hazards.",
    },
    "NEC 230.95": {
        "title": "Ground-Fault Protection of Equipment",
        "text": "Ground-fault protection of equipment shall be provided for each service disconnect rated 1000A or more, on solidly grounded wye electrical services of more than 150V to ground but not exceeding 600V phase-to-phase.",
        "why_it_matters": "Arcing ground faults on 480Y/277V systems can persist at levels below overcurrent device pickup, causing fires. GFP detects these.",
    },
    "NEC 240.4": {
        "title": "Protection of Conductors",
        "text": "Conductors shall be protected against overcurrent in accordance with their ampacities. The next higher standard overcurrent device rating may be used if certain conditions are met.",
        "why_it_matters": "Undersized overcurrent protection can allow conductors to overheat, degrading insulation and potentially starting fires.",
    },
    "NEC 240.6": {
        "title": "Standard Ampere Ratings",
        "text": "Standard ampere ratings for fuses and inverse time circuit breakers: 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125, 150...",
        "why_it_matters": "Non-standard ratings indicate either an adjustable trip setting or an error. Verify with manufacturer data.",
    },
    "NEC 240.87": {
        "title": "Arc Energy Reduction",
        "text": "Where the highest continuous current trip setting for which the actual overcurrent device installed in a circuit breaker is rated or can be adjusted is 1200A or higher, one of several arc energy reduction methods shall be provided.",
        "why_it_matters": "Large breakers can sustain arcs long enough to cause catastrophic burns. ZSI, maintenance switches, or active mitigation systems reduce this risk.",
    },
    "NEC 250.30": {
        "title": "Grounding Separately Derived Systems",
        "text": "A separately derived system that has no direct electrical connection to supply conductors originating from another system shall have a grounding electrode conductor, system bonding jumper, and supply-side bonding jumper.",
        "why_it_matters": "Every transformer creates a separately derived system that must be independently grounded. Missing grounding creates shock hazards and can interfere with ground fault protection.",
    },
    "NEC 250.122": {
        "title": "Size of Equipment Grounding Conductors",
        "text": "Equipment grounding conductors shall not be smaller than given in Table 250.122, based on the rating of the overcurrent device ahead of the equipment.",
        "why_it_matters": "Undersized grounding conductors may not safely carry fault current back to the source, preventing overcurrent devices from operating and creating shock hazards.",
    },
    "NEC 310.16": {
        "title": "Ampacities of Insulated Conductors",
        "text": "Table 310.16 provides allowable ampacities for conductors rated 0 through 2000V in raceway, cable, or earth. Based on ambient temperature of 30°C.",
        "why_it_matters": "This is THE table for sizing conductors. Using the wrong column (60°C vs 75°C vs 90°C) or forgetting derating factors is a common error.",
    },
    "NEC 408.36": {
        "title": "Overcurrent Protection of Panelboards",
        "text": "Each panelboard shall be protected by an overcurrent protective device having a rating not greater than that of the panelboard.",
        "why_it_matters": "A breaker rated higher than the bus can push more current through the bus than it can handle, causing overheating and potential fire.",
    },
    "NEC 450.3": {
        "title": "Overcurrent Protection for Transformers",
        "text": "Overcurrent protection of transformers shall comply with 450.3(A) for over 600V and 450.3(B) for 600V and below. Primary OCPD generally limited to 125% of FLA.",
        "why_it_matters": "Transformer protection must balance between protecting the transformer and allowing inrush current. Too high allows damage; too low causes nuisance tripping.",
    },
    "NEC 700.32": {
        "title": "Selective Coordination — Emergency Systems",
        "text": "Emergency system(s) overcurrent devices shall be selectively coordinated with all supply-side overcurrent protective devices.",
        "why_it_matters": "A fault on one emergency branch must not trip upstream devices that feed other emergency loads. Loss of emergency power during a fire can be fatal.",
    },
    "NEC 701.27": {
        "title": "Selective Coordination — Legally Required Standby",
        "text": "Legally required standby system overcurrent devices shall be selectively coordinated with all supply-side overcurrent protective devices.",
        "why_it_matters": "Same principle as NEC 700.32 but for legally required standby loads like smoke control and elevators for firefighter use.",
    },
    "IEEE C57.110": {
        "title": "Recommended Practice for Establishing Liquid-Immersed and Dry-Type Power and Distribution Transformer Capability When Supplying Nonsinusoidal Load Currents",
        "text": "K-factor rated transformers are designed to handle additional heating from harmonic currents. K-13 is typical for data center IT loads.",
        "why_it_matters": "Standard transformers serving IT loads will overheat due to harmonic currents. K-factor transformers have additional capacity for this heating.",
    },
    "IEC 60364": {
        "title": "Low-Voltage Electrical Installations",
        "text": "IEC 60364-5-52 provides ampacity tables for metric cable sizes. These are the correct tables for cables sized in mm².",
        "why_it_matters": "Metric cables must use IEC ampacity tables, not NEC tables. Converting mm² to AWG for NEC lookup introduces errors because the sizes don't correspond exactly.",
    },
    "UL 489": {
        "title": "Molded-Case Circuit Breakers, Molded-Case Switches, and Circuit-Breaker Enclosures",
        "text": "UL 489 covers the safety requirements for MCCBs. Trip rating cannot exceed frame size — this is a fundamental product safety constraint.",
        "why_it_matters": "A breaker configuration where trip > frame is physically impossible and indicates a data error in the submittal.",
    },
}


def get_commentary(reference_code: str) -> dict:
    """Get NEC commentary for a given reference code. Returns empty dict if not found."""
    # Try exact match first
    if reference_code in NEC_COMMENTARY:
        return NEC_COMMENTARY[reference_code]

    # Try partial match (e.g., "NEC 110.9, Drawing Consistency" → "NEC 110.9")
    for key in NEC_COMMENTARY:
        if key in reference_code:
            return NEC_COMMENTARY[key]

    return {}
