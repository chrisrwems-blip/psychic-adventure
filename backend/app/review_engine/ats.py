import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class ATSChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "ats"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Ratings
            CheckItem("ATS-001", "Ampere rating matches design load", "Ratings", "UL 1008", "critical"),
            CheckItem("ATS-002", "Voltage rating matches system", "Ratings", "UL 1008", "critical"),
            CheckItem("ATS-003", "Withstand and closing rating (WCR) adequate for fault current", "Ratings", "UL 1008, NEC 110.9", "critical"),
            CheckItem("ATS-004", "Number of poles (3-pole or 4-pole as required)", "Ratings", "NEC 700/701", "major"),
            CheckItem("ATS-005", "Frequency rating (60Hz)", "Ratings", "UL 1008", "major"),

            # Transfer Characteristics
            CheckItem("ATS-010", "Transfer type specified (open, closed, delayed)", "Transfer", "UL 1008", "critical"),
            CheckItem("ATS-011", "Transfer time specified (meets NFPA 110 requirements)", "Transfer", "NFPA 110", "critical"),
            CheckItem("ATS-012", "Retransfer time delay adjustable", "Transfer", "UL 1008", "major"),
            CheckItem("ATS-013", "Engine start signal timing", "Transfer", "NFPA 110", "major"),
            CheckItem("ATS-014", "Closed-transition transfer capability if specified (make-before-break)", "Transfer", "UL 1008", "major"),
            CheckItem("ATS-015", "In-phase monitor for closed transition", "Transfer", "UL 1008", "major"),

            # Bypass & Maintenance
            CheckItem("ATS-020", "Bypass isolation switch included", "Bypass", "Uptime Tier III, NFPA 110", "critical"),
            CheckItem("ATS-021", "Bypass rated for full load", "Bypass", "UL 1008", "critical"),
            CheckItem("ATS-022", "Drawout mechanism for maintenance without load interruption", "Bypass", "Uptime Tier III", "major"),
            CheckItem("ATS-023", "Kirk-key or mechanical interlock with bypass", "Bypass", "NFPA 70E", "major"),

            # Sensing & Controls
            CheckItem("ATS-030", "Voltage sensing thresholds adjustable", "Controls", "NFPA 110", "major"),
            CheckItem("ATS-031", "Frequency sensing thresholds adjustable", "Controls", "NFPA 110", "major"),
            CheckItem("ATS-032", "Time delay settings documented (start, transfer, retransfer, cooldown)", "Controls", "NFPA 110", "major"),
            CheckItem("ATS-033", "Load shedding contacts if required", "Controls", "NFPA 110", "minor"),
            CheckItem("ATS-034", "Exercise/test capability", "Controls", "NFPA 110", "minor"),

            # Monitoring
            CheckItem("ATS-040", "Source status indication (Source 1 Available, Source 2 Available)", "Monitoring", "Project Spec", "major"),
            CheckItem("ATS-041", "Communication protocol for BMS integration", "Monitoring", "Project Spec", "minor"),
            CheckItem("ATS-042", "Alarm outputs (transfer fail, source fail, etc.)", "Monitoring", "Project Spec", "minor"),

            # Physical & Standards
            CheckItem("ATS-050", "NEMA enclosure rating appropriate", "Physical", "NEMA 250", "major"),
            CheckItem("ATS-051", "Seismic certification if required", "Physical", "IBC/ASCE 7", "major"),
            CheckItem("ATS-052", "UL 1008 listing confirmed", "Standards", "UL 1008", "major"),
            CheckItem("ATS-053", "NEC 700/701/702 classification documented", "Standards", "NEC 700/701/702", "critical"),
            CheckItem("ATS-054", "NFPA 110 Type/Class/Level specified", "Standards", "NFPA 110", "critical"),

            # Redundancy
            CheckItem("ATS-060", "Redundancy path clearly identified in single-line", "Redundancy", "Uptime Tier III/IV", "major"),
            CheckItem("ATS-061", "Failure mode documented (fails to preferred source)", "Redundancy", "Project Spec", "major"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        check_id = item.id

        if check_id == "ATS-001":
            amps = re.findall(r'(\d{2,5})\s*(?:amp|a\b)', text)
            if amps:
                return self._pass(item, f"Amp ratings found: {amps}. Verify matches design load.")
            return self._fail(item, "No ampere rating found")

        if check_id == "ATS-003":
            if any(x in text for x in ["withstand", "wcr", "closing rating", "kaic"]):
                return self._pass(item, "Withstand/closing rating referenced. Verify >= available fault current.")
            return self._fail(item, "Withstand and closing rating not documented — critical")

        if check_id == "ATS-010":
            types = ["open transition", "closed transition", "delayed transition", "soft load"]
            found = [t for t in types if t in text]
            if found:
                return self._pass(item, f"Transfer type: {found[0]}. Verify matches spec.")
            return self._fail(item, "Transfer type not specified")

        if check_id == "ATS-020":
            if any(x in text for x in ["bypass", "isolation"]):
                return self._pass(item, "Bypass referenced. Verify includes bypass isolation switch.")
            return self._fail(item, "Bypass isolation not found — required for Tier III+")

        return super()._evaluate_check(item, text, metadata)
