import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class CableChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "cable"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Conductor
            CheckItem("CBL-001", "Conductor size (AWG/kcmil) matches ampacity requirements", "Conductor", "NEC 310", "critical"),
            CheckItem("CBL-002", "Conductor material specified (copper required for data center)", "Conductor", "NEC 310, Project Spec", "critical"),
            CheckItem("CBL-003", "Number of conductors per phase for parallel runs", "Conductor", "NEC 310.10(H)", "major"),
            CheckItem("CBL-004", "Neutral conductor sizing (full size or 200% for harmonics)", "Conductor", "NEC 310.15(E), IEEE C57.110", "critical"),
            CheckItem("CBL-005", "Ground conductor size per NEC 250.122", "Conductor", "NEC 250.122", "critical"),

            # Insulation
            CheckItem("CBL-010", "Insulation type specified (THHN, XHHW, etc.)", "Insulation", "NEC 310.104", "critical"),
            CheckItem("CBL-011", "Voltage rating matches system voltage", "Insulation", "NEC 310", "critical"),
            CheckItem("CBL-012", "Temperature rating appropriate (75C or 90C)", "Insulation", "NEC 310.15", "major"),
            CheckItem("CBL-013", "Plenum/riser rating if required (FEP, FPLP)", "Insulation", "NEC 300.21, 800.179", "major"),
            CheckItem("CBL-014", "Sunlight resistant if routed outdoors", "Insulation", "NEC 310.104", "minor"),
            CheckItem("CBL-015", "Low smoke zero halogen (LSZH) if required", "Insulation", "Project Spec", "minor"),

            # Installation
            CheckItem("CBL-020", "Raceway type specified (conduit, tray, ladder rack)", "Installation", "NEC 300", "major"),
            CheckItem("CBL-021", "Conduit fill calculations within 40% limit", "Installation", "NEC Chapter 9, Table 1", "major"),
            CheckItem("CBL-022", "Minimum bending radius maintained", "Installation", "NEC 300.34", "major"),
            CheckItem("CBL-023", "Derating for bundled cables or high ambient temp", "Installation", "NEC 310.15(C)", "critical"),
            CheckItem("CBL-024", "Fire stopping at penetrations", "Installation", "NEC 300.21", "critical"),
            CheckItem("CBL-025", "Cable tray fill calculations if applicable", "Installation", "NEC 392", "major"),

            # Medium Voltage (if applicable)
            CheckItem("CBL-030", "Shield type specified for MV cables", "Medium Voltage", "NEC 310, IEEE 575", "major"),
            CheckItem("CBL-031", "Termination/splice type specified", "Medium Voltage", "IEEE 48", "major"),
            CheckItem("CBL-032", "Jacket type (PVC, PE) specified for MV", "Medium Voltage", "ICEA", "minor"),

            # Ampacity
            CheckItem("CBL-040", "Ampacity calculation method documented (NEC 310.15)", "Ampacity", "NEC 310.15", "critical"),
            CheckItem("CBL-041", "Voltage drop calculation within limits (3% branch, 5% total)", "Ampacity", "NEC 210.19(A) FPN, 215.2(A) FPN", "major"),
            CheckItem("CBL-042", "Ambient temperature correction factors applied", "Ampacity", "NEC 310.15(B)", "major"),

            # Standards
            CheckItem("CBL-050", "UL listed cable", "Standards", "UL 44/83/854", "major"),
            CheckItem("CBL-051", "NEC Article 310 compliance", "Standards", "NEC 310", "major"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        check_id = item.id

        if check_id == "CBL-001":
            awg = re.findall(r'(\d{1,2})\s*awg', text)
            kcmil = re.findall(r'(\d{3,4})\s*kcmil', text)
            if awg or kcmil:
                found = f"AWG: {awg}" if awg else f"kcmil: {kcmil}"
                return self._pass(item, f"Conductor sizes found: {found}. Verify ampacity.")
            return self._fail(item, "No conductor size found")

        if check_id == "CBL-002":
            if "copper" in text or "cu" in text:
                return self._pass(item, "Copper conductor referenced. Confirm copper required per spec.")
            if "aluminum" in text or "al " in text:
                return self._fail(item, "Aluminum conductor found — verify if acceptable for data center application")
            return self._fail(item, "Conductor material not specified")

        if check_id == "CBL-041":
            if "voltage drop" in text or "volt drop" in text:
                return self._pass(item, "Voltage drop referenced. Verify within 3%/5% limits.")
            return self._fail(item, "Voltage drop not addressed")

        return super()._evaluate_check(item, text, metadata)
