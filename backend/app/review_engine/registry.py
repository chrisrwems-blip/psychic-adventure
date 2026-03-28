from .base import BaseEquipmentChecker
from .switchgear import SwitchgearChecker
from .ups import UPSChecker
from .generator import GeneratorChecker
from .pdu import PDUChecker
from .transformer import TransformerChecker
from .ats import ATSChecker
from .cable import CableChecker
from .bus_duct import BusDuctChecker
from .panelboard import PanelboardChecker
from .rpp import RPPChecker
from .sts import STSChecker
from .battery import BatteryChecker
from .cooling import CoolingChecker

CHECKER_REGISTRY: dict[str, type[BaseEquipmentChecker]] = {
    "switchgear": SwitchgearChecker,
    "ups": UPSChecker,
    "generator": GeneratorChecker,
    "pdu": PDUChecker,
    "transformer": TransformerChecker,
    "ats": ATSChecker,
    "cable": CableChecker,
    "bus_duct": BusDuctChecker,
    "busway": BusDuctChecker,  # alias
    "panelboard": PanelboardChecker,
    "rpp": RPPChecker,
    "sts": STSChecker,
    "battery": BatteryChecker,
    "cooling": CoolingChecker,
    "crac": CoolingChecker,  # alias
    "crah": CoolingChecker,  # alias
    "chiller": CoolingChecker,  # alias
}


def get_checker(equipment_type: str) -> BaseEquipmentChecker:
    """Get the appropriate checker for an equipment type."""
    checker_class = CHECKER_REGISTRY.get(equipment_type.lower())
    if checker_class is None:
        raise ValueError(
            f"No checker for equipment type '{equipment_type}'. "
            f"Available: {list(CHECKER_REGISTRY.keys())}"
        )
    return checker_class()


def get_available_equipment_types() -> list[str]:
    """Return list of supported equipment types."""
    return sorted(set(CHECKER_REGISTRY.keys()))
