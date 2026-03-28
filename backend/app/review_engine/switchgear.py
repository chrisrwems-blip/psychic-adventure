import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class SwitchgearChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "switchgear"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Nameplate & Ratings
            CheckItem("SW-001", "Voltage rating matches spec (480V, 4160V, or as specified)", "Nameplate & Ratings", "NEC 408.4", "critical"),
            CheckItem("SW-002", "Short-circuit current rating (SCCR) meets or exceeds available fault current", "Nameplate & Ratings", "NEC 110.10, IEEE C37.20", "critical"),
            CheckItem("SW-003", "Continuous current rating matches load calculations", "Nameplate & Ratings", "NEC 408.4", "critical"),
            CheckItem("SW-004", "BIL (Basic Impulse Level) rating appropriate for system voltage class", "Nameplate & Ratings", "IEEE C37.20.2", "major"),
            CheckItem("SW-005", "Bus bracing rating >= available fault current", "Nameplate & Ratings", "IEEE C37.20.7", "critical"),
            CheckItem("SW-006", "Frequency rating confirmed (60Hz)", "Nameplate & Ratings", "NEC 408.4", "major"),
            CheckItem("SW-007", "Number of phases confirmed (3-phase)", "Nameplate & Ratings", "NEC 408.4", "major"),

            # Protection & Coordination
            CheckItem("SW-010", "Main breaker trip ratings specified and match coordination study", "Protection", "NEC 240.12, IEEE C37.010", "critical"),
            CheckItem("SW-011", "Protective relay types specified (overcurrent, ground fault, differential)", "Protection", "NEC 240, IEEE C37.90", "critical"),
            CheckItem("SW-012", "Ground fault protection provided per NEC requirements", "Protection", "NEC 230.95, 215.10", "critical"),
            CheckItem("SW-013", "Current transformer (CT) ratios specified for metering and protection", "Protection", "IEEE C57.13", "major"),
            CheckItem("SW-014", "Breaker interrupting ratings adequate for available fault current", "Protection", "NEC 110.9", "critical"),
            CheckItem("SW-015", "Zone selective interlocking (ZSI) provided if specified", "Protection", "NEC 240.12", "major"),

            # Uptime / Redundancy
            CheckItem("SW-020", "Redundancy path (A/B feed) clearly identified", "Uptime Compliance", "Uptime Tier III/IV", "major"),
            CheckItem("SW-021", "Maintenance bypass provisions for concurrent maintainability", "Uptime Compliance", "Uptime Tier III", "major"),
            CheckItem("SW-022", "Kirk-key interlock scheme documented", "Uptime Compliance", "NFPA 70E", "critical"),
            CheckItem("SW-023", "Automatic transfer capability if required by topology", "Uptime Compliance", "Uptime Tier III/IV", "major"),
            CheckItem("SW-024", "Single point of failure analysis addressed", "Uptime Compliance", "Uptime Tier III/IV", "critical"),

            # Physical & Environmental
            CheckItem("SW-030", "Seismic rating specified per project requirements", "Physical", "IBC/ASCE 7", "major"),
            CheckItem("SW-031", "NEMA/IP enclosure rating appropriate for environment", "Physical", "NEMA 250", "major"),
            CheckItem("SW-032", "Dimensions fit allocated space in modular layout", "Physical", "Project Spec", "major"),
            CheckItem("SW-033", "Weight confirmed for structural loading", "Physical", "Project Spec", "minor"),
            CheckItem("SW-034", "Front and rear access clearances per NEC", "Physical", "NEC 110.26", "critical"),
            CheckItem("SW-035", "Cable entry (top/bottom) matches design", "Physical", "Project Spec", "minor"),

            # Arc Flash & Safety
            CheckItem("SW-040", "Arc flash energy calculations referenced", "Safety", "NFPA 70E, IEEE 1584", "critical"),
            CheckItem("SW-041", "Arc-resistant construction if specified", "Safety", "IEEE C37.20.7", "major"),
            CheckItem("SW-042", "PPE category labels specified", "Safety", "NFPA 70E 130.5", "major"),

            # Metering & Monitoring
            CheckItem("SW-050", "Metering provisions (voltage, current, power, energy)", "Monitoring", "Project Spec", "minor"),
            CheckItem("SW-051", "Communication protocol specified (Modbus, BACnet, SNMP)", "Monitoring", "Project Spec", "minor"),
            CheckItem("SW-052", "Integration with BMS/EPMS addressed", "Monitoring", "Project Spec", "minor"),

            # Testing & Standards
            CheckItem("SW-060", "UL 1558 listing confirmed", "Standards", "UL 1558", "major"),
            CheckItem("SW-061", "Factory test procedures outlined", "Standards", "IEEE C37.20", "minor"),
            CheckItem("SW-062", "Third-party witness testing if required", "Standards", "Project Spec", "minor"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        """Enhanced switchgear-specific checks."""
        check_id = item.id

        # Voltage rating check
        if check_id == "SW-001":
            voltage_match = re.findall(r'(\d{3,5})\s*(?:v|volt)', text)
            if voltage_match:
                voltages = [int(v) for v in voltage_match]
                return self._pass(item, f"Voltage rating(s) found: {voltages}V")
            return self._fail(item, "No voltage rating found in submittal")

        # SCCR check
        if check_id == "SW-002":
            sccr_patterns = [r'(\d{2,3})\s*(?:ka|kaic)', r'short.?circuit.*?(\d{2,3})', r'withstand.*?(\d{2,3})']
            for pattern in sccr_patterns:
                match = re.search(pattern, text)
                if match:
                    sccr = int(match.group(1))
                    return self._pass(item, f"SCCR found: {sccr}kA. Verify >= available fault current.")
            return self._fail(item, "SCCR/withstand rating not found")

        # Bus bracing
        if check_id == "SW-005":
            bus_patterns = [r'bus\s*brac.*?(\d{2,3})', r'bracing.*?(\d{2,3})\s*ka']
            for pattern in bus_patterns:
                match = re.search(pattern, text)
                if match:
                    return self._pass(item, f"Bus bracing found: {match.group(1)}kA")
            return self._fail(item, "Bus bracing rating not found in submittal")

        # Ground fault
        if check_id == "SW-012":
            if "ground fault" in text or "gfp" in text or "gfi" in text:
                return self._pass(item, "Ground fault protection referenced")
            return self._fail(item, "No ground fault protection information found")

        # Arc flash
        if check_id == "SW-040":
            if "arc flash" in text or "arc-flash" in text or "incident energy" in text or "ieee 1584" in text:
                return self._pass(item, "Arc flash data referenced in submittal")
            return self._fail(item, "No arc flash information found — critical safety concern")

        # NEC clearances
        if check_id == "SW-034":
            if "110.26" in text or "working space" in text or "clearance" in text:
                return self._pass(item, "Clearance/working space information found")
            return self._fail(item, "Working space clearances not addressed")

        # Frequency
        if check_id == "SW-006":
            if "60hz" in text or "60 hz" in text:
                return self._pass(item, "60Hz frequency confirmed")
            if "50hz" in text or "50 hz" in text:
                return self._needs_review(item, "50Hz found — verify correct for this project")
            return self._fail(item, "Frequency not specified")

        # 3-phase
        if check_id == "SW-007":
            if "3-phase" in text or "3 phase" in text or "three phase" in text or "3ph" in text:
                return self._pass(item, "3-phase configuration confirmed")
            return self._fail(item, "Phase configuration not specified")

        # Default to base class behavior
        return super()._evaluate_check(item, text, metadata)
