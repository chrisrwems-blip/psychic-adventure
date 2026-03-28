import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class RPPChecker(BaseEquipmentChecker):
    """Remote Power Panel checker."""
    def equipment_type(self) -> str:
        return "rpp"

    def get_checklist(self) -> list[CheckItem]:
        return [
            CheckItem("RPP-001", "Input ampere rating matches feeder design", "Ratings", "NEC 408", "critical"),
            CheckItem("RPP-002", "Input/output voltage configuration correct", "Ratings", "NEC 408", "critical"),
            CheckItem("RPP-003", "SCCR adequate for available fault current", "Ratings", "NEC 110.10", "critical"),
            CheckItem("RPP-004", "Number of output breakers matches rack count", "Distribution", "Project Spec", "critical"),
            CheckItem("RPP-005", "Breaker ratings match whip/cable ampacity", "Distribution", "NEC 240.4", "critical"),
            CheckItem("RPP-006", "Cam-lock or breaker input connection as specified", "Distribution", "Project Spec", "major"),
            CheckItem("RPP-007", "Output connector type (L6-20, L6-30, L21-30, etc.)", "Distribution", "Project Spec", "major"),
            CheckItem("RPP-008", "Per-circuit monitoring included", "Monitoring", "Project Spec", "major"),
            CheckItem("RPP-009", "Network monitoring (SNMP/Modbus) connectivity", "Monitoring", "Project Spec", "minor"),
            CheckItem("RPP-010", "Color coding for A/B path identification", "Physical", "Project Spec", "minor"),
            CheckItem("RPP-011", "Dimensions fit under raised floor or overhead", "Physical", "Project Spec", "major"),
            CheckItem("RPP-012", "UL 67 or UL 891 listing", "Standards", "UL 67/891", "major"),
            CheckItem("RPP-013", "Spare circuit positions per spec", "Distribution", "Project Spec", "minor"),
        ]

    def _evaluate_check(self, item, text, metadata):
        return super()._evaluate_check(item, text, metadata)
