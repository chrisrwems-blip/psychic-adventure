from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class STSChecker(BaseEquipmentChecker):
    """Static Transfer Switch checker."""
    def equipment_type(self) -> str:
        return "sts"

    def get_checklist(self) -> list[CheckItem]:
        return [
            CheckItem("STS-001", "Ampere rating matches design load", "Ratings", "UL 1008", "critical"),
            CheckItem("STS-002", "Voltage rating matches system", "Ratings", "UL 1008", "critical"),
            CheckItem("STS-003", "Transfer time (< 4ms for IT loads, quarter-cycle)", "Transfer", "ITIC/CBEMA Curve", "critical"),
            CheckItem("STS-004", "Withstand/fault current rating adequate", "Ratings", "NEC 110.10", "critical"),
            CheckItem("STS-005", "Preferred source selection logic documented", "Controls", "Project Spec", "major"),
            CheckItem("STS-006", "Retransfer criteria and timing", "Controls", "Project Spec", "major"),
            CheckItem("STS-007", "SCR (thyristor) vs contactor-based technology", "Construction", "Project Spec", "major"),
            CheckItem("STS-008", "Backfeed protection between sources", "Protection", "NEC 700", "critical"),
            CheckItem("STS-009", "Maintenance bypass included", "Bypass", "Uptime Tier III", "critical"),
            CheckItem("STS-010", "Internal bypass for SCR failure", "Protection", "Project Spec", "major"),
            CheckItem("STS-011", "Overload and short-circuit protection", "Protection", "UL 1008", "critical"),
            CheckItem("STS-012", "Heat dissipation (BTU/hr) documented", "Physical", "Project Spec", "major"),
            CheckItem("STS-013", "Source synchronization monitoring", "Controls", "Project Spec", "major"),
            CheckItem("STS-014", "SNMP/network monitoring capability", "Monitoring", "Project Spec", "minor"),
            CheckItem("STS-015", "UL 1008 listing", "Standards", "UL 1008", "major"),
            CheckItem("STS-016", "ITIC/CBEMA curve compliance documentation", "Standards", "ITIC/CBEMA", "major"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        check_id = item.id

        if check_id == "STS-003":
            if any(x in text for x in ["4ms", "4 ms", "quarter cycle", "1/4 cycle", "transfer time"]):
                return self._pass(item, "Transfer time referenced. Verify < 4ms for IT load protection.")
            return self._fail(item, "Transfer time not documented — must be < 4ms for data center IT loads")

        return super()._evaluate_check(item, text, metadata)
