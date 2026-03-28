import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class PanelboardChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "panelboard"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Ratings
            CheckItem("PNL-001", "Bus ampere rating matches design", "Ratings", "NEC 408", "critical"),
            CheckItem("PNL-002", "Voltage rating matches system", "Ratings", "NEC 408", "critical"),
            CheckItem("PNL-003", "SCCR (short-circuit current rating) adequate", "Ratings", "NEC 110.10, 408.36(A)", "critical"),
            CheckItem("PNL-004", "Main breaker or main lug only (MLO) as designed", "Ratings", "NEC 408.36", "major"),
            CheckItem("PNL-005", "Phase configuration (1-phase or 3-phase)", "Ratings", "NEC 408", "major"),

            # Branch Circuits
            CheckItem("PNL-010", "Branch breaker schedule matches design panel schedule", "Branch Circuits", "NEC 408.4", "critical"),
            CheckItem("PNL-011", "Breaker trip ratings match conductor ampacity", "Branch Circuits", "NEC 240.4", "critical"),
            CheckItem("PNL-012", "Number of spaces/circuits matches spec (with spares)", "Branch Circuits", "NEC 408", "major"),
            CheckItem("PNL-013", "AFCI/GFCI breakers provided where required (dwelling units, bathrooms, kitchens — IT spaces are exempt per NEC)", "Branch Circuits", "NEC 210.12, 210.8", "major"),
            CheckItem("PNL-014", "Spare breaker positions per spec (typically 20%)", "Branch Circuits", "Project Spec", "minor"),

            # Neutral & Ground
            CheckItem("PNL-020", "Neutral bus sizing adequate (200% for harmonic loads)", "Neutral & Ground", "NEC 408, IEEE C57.110", "major"),
            CheckItem("PNL-021", "Ground bus provided and properly sized", "Neutral & Ground", "NEC 250.122", "critical"),
            CheckItem("PNL-022", "Isolated ground bus if specified", "Neutral & Ground", "NEC 250.146(D)", "minor"),
            CheckItem("PNL-023", "Neutral-ground bond only at service entrance", "Neutral & Ground", "NEC 250.142", "critical"),

            # Surge Protection
            CheckItem("PNL-030", "SPD (Surge Protective Device) included if required", "Surge Protection", "NEC 242", "major"),
            CheckItem("PNL-031", "SPD kA rating per project spec", "Surge Protection", "UL 1449", "major"),

            # Physical
            CheckItem("PNL-040", "Surface or flush mount as designed", "Physical", "Project Spec", "minor"),
            CheckItem("PNL-041", "NEMA enclosure type matches environment", "Physical", "NEMA 250", "major"),
            CheckItem("PNL-042", "Door-in-door configuration if specified", "Physical", "Project Spec", "minor"),
            CheckItem("PNL-043", "Panel directory/circuit identification", "Physical", "NEC 408.4", "major"),

            # Monitoring
            CheckItem("PNL-050", "Branch circuit monitoring if specified", "Monitoring", "Project Spec", "major"),
            CheckItem("PNL-051", "Network connectivity for monitoring", "Monitoring", "Project Spec", "minor"),

            # Standards
            CheckItem("PNL-060", "UL 67 listing (panelboards)", "Standards", "UL 67", "major"),
            CheckItem("PNL-061", "NEC 408 compliance", "Standards", "NEC 408", "major"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        check_id = item.id

        if check_id == "PNL-001":
            amps = re.findall(r'(\d{2,5})\s*(?:amp|a\b)', text)
            if amps:
                return self._pass(item, f"Amp ratings found: {amps}. Verify matches design.")
            return self._fail(item, "No bus ampere rating found")

        if check_id == "PNL-003":
            if any(x in text for x in ["sccr", "short circuit", "kaic", "withstand"]):
                return self._pass(item, "SCCR referenced. Verify >= available fault current.")
            return self._fail(item, "SCCR not documented — required per NEC 110.10")

        return super()._evaluate_check(item, text, metadata)
