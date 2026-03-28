import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class BusDuctChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "bus_duct"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Ratings
            CheckItem("BD-001", "Ampacity rating matches design load", "Ratings", "NEC 368", "critical"),
            CheckItem("BD-002", "Voltage rating matches system", "Ratings", "NEC 368", "critical"),
            CheckItem("BD-003", "Short-circuit withstand rating adequate", "Ratings", "NEC 368.17, UL 857", "critical"),
            CheckItem("BD-004", "Number of poles and configuration", "Ratings", "NEC 368", "major"),
            CheckItem("BD-005", "Frequency rating (60Hz)", "Ratings", "NEC 368", "major"),

            # Construction
            CheckItem("BD-010", "Bus conductor material (copper or aluminum)", "Construction", "NEC 368, Project Spec", "major"),
            CheckItem("BD-011", "Insulation type and class", "Construction", "UL 857", "major"),
            CheckItem("BD-012", "IP/NEMA enclosure rating", "Construction", "NEMA 250", "major"),
            CheckItem("BD-013", "Ventilated or non-ventilated housing as required", "Construction", "Project Spec", "minor"),
            CheckItem("BD-014", "Ground bus included and properly sized", "Construction", "NEC 250.122", "critical"),
            CheckItem("BD-015", "Neutral bus sizing (100% or 200% for harmonics)", "Construction", "NEC 368, IEEE C57.110", "major"),

            # Layout & Installation
            CheckItem("BD-020", "Routing layout matches design drawings", "Layout", "Project Spec", "major"),
            CheckItem("BD-021", "Tap-off box locations match PDU/panel locations", "Layout", "Project Spec", "critical"),
            CheckItem("BD-022", "Expansion joints provided for thermal expansion", "Layout", "UL 857", "major"),
            CheckItem("BD-023", "Support/hanger spacing per manufacturer requirements", "Layout", "NEC 368.30", "major"),
            CheckItem("BD-024", "Fire barrier penetration provisions", "Layout", "NEC 300.21", "critical"),
            CheckItem("BD-025", "Voltage drop within acceptable limits over bus run length", "Layout", "NEC 210.19 FPN", "major"),

            # Tap-Off Provisions
            CheckItem("BD-030", "Tap-off box ampere ratings match connected loads", "Tap-Off", "NEC 368", "critical"),
            CheckItem("BD-031", "Tap-off can be installed/removed under load (hot-swappable)", "Tap-Off", "Uptime Tier III", "major"),
            CheckItem("BD-032", "Spare tap-off positions for future growth", "Tap-Off", "Project Spec", "minor"),
            CheckItem("BD-033", "Tap-off fusible or circuit breaker type as specified", "Tap-Off", "NEC 368", "major"),

            # Standards
            CheckItem("BD-040", "UL 857 listing", "Standards", "UL 857", "major"),
            CheckItem("BD-041", "Seismic rating if required", "Standards", "IBC/ASCE 7", "major"),
            CheckItem("BD-042", "Temperature rise test data", "Standards", "UL 857", "minor"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        check_id = item.id

        if check_id == "BD-001":
            amps = re.findall(r'(\d{3,5})\s*(?:amp|a\b)', text)
            if amps:
                return self._pass(item, f"Ampacity found: {amps}A. Verify matches design load.")
            return self._fail(item, "No ampacity rating found")

        if check_id == "BD-031":
            if any(x in text for x in ["hot swap", "hot-swap", "under load", "live"]):
                return self._pass(item, "Hot-swappable capability referenced. Verify for Tier III.")
            return self._fail(item, "Hot-swap tap-off capability not confirmed — needed for Tier III+")

        return super()._evaluate_check(item, text, metadata)
