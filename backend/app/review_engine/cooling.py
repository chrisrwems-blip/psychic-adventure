import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class CoolingChecker(BaseEquipmentChecker):
    """CRAC/CRAH/Chiller/In-row cooling for data centers."""
    def equipment_type(self) -> str:
        return "cooling"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Capacity
            CheckItem("CLG-001", "Cooling capacity (kW or tons) matches heat load calculations", "Capacity", "ASHRAE TC 9.9", "critical"),
            CheckItem("CLG-002", "Sensible cooling capacity documented (not just total)", "Capacity", "ASHRAE TC 9.9", "critical"),
            CheckItem("CLG-003", "Sensible heat ratio (SHR) appropriate for data center (>0.9)", "Capacity", "ASHRAE TC 9.9", "major"),
            CheckItem("CLG-004", "Return air temperature setpoint range", "Capacity", "ASHRAE A1/A2/A3/A4", "major"),
            CheckItem("CLG-005", "Supply air temperature specified", "Capacity", "ASHRAE TC 9.9", "major"),
            CheckItem("CLG-006", "Airflow (CFM) matches design requirements", "Capacity", "ASHRAE TC 9.9", "critical"),

            # Electrical
            CheckItem("CLG-010", "Electrical power input (kW) documented", "Electrical", "NEC 440", "critical"),
            CheckItem("CLG-011", "Voltage/phase configuration matches facility", "Electrical", "NEC 440", "critical"),
            CheckItem("CLG-012", "MCA (Minimum Circuit Ampacity) specified", "Electrical", "NEC 440.4", "critical"),
            CheckItem("CLG-013", "MOCP (Maximum Overcurrent Protection) specified", "Electrical", "NEC 440.22", "critical"),
            CheckItem("CLG-014", "Power factor documented", "Electrical", "Project Spec", "minor"),
            CheckItem("CLG-015", "PUE contribution / energy efficiency ratio (EER/COP)", "Electrical", "ASHRAE 90.4", "major"),

            # Refrigerant
            CheckItem("CLG-020", "Refrigerant type specified (R-410A, R-134a, R-1234ze, etc.)", "Refrigerant", "ASHRAE 15", "major"),
            CheckItem("CLG-021", "Refrigerant charge amount documented", "Refrigerant", "ASHRAE 15", "minor"),
            CheckItem("CLG-022", "Refrigerant leak detection provisions", "Refrigerant", "ASHRAE 15", "major"),
            CheckItem("CLG-023", "GWP compliance for current regulations", "Refrigerant", "EPA AIM Act", "major"),

            # Redundancy
            CheckItem("CLG-030", "N+1 or 2N redundancy matches tier requirements", "Redundancy", "Uptime Tier III/IV", "critical"),
            CheckItem("CLG-031", "Dual power feed / UPS-backed controls if required", "Redundancy", "Uptime Tier III", "major"),
            CheckItem("CLG-032", "Automatic failover capability", "Redundancy", "Uptime Tier III", "major"),

            # Controls & Monitoring
            CheckItem("CLG-040", "BMS/DCIM integration protocol (BACnet, Modbus, SNMP)", "Controls", "Project Spec", "major"),
            CheckItem("CLG-041", "Variable speed fan/compressor for efficiency", "Controls", "ASHRAE 90.4", "major"),
            CheckItem("CLG-042", "Humidity control capability", "Controls", "ASHRAE TC 9.9", "major"),
            CheckItem("CLG-043", "Temperature and humidity sensors included", "Controls", "ASHRAE TC 9.9", "major"),
            CheckItem("CLG-044", "High temperature alarm setpoints", "Controls", "Project Spec", "major"),

            # Physical
            CheckItem("CLG-050", "Dimensions fit allocated space", "Physical", "Project Spec", "major"),
            CheckItem("CLG-051", "Weight for structural loading", "Physical", "Project Spec", "major"),
            CheckItem("CLG-052", "Piping connection sizes documented", "Physical", "Project Spec", "major"),
            CheckItem("CLG-053", "Sound level (dBA) documented", "Physical", "Project Spec", "minor"),
            CheckItem("CLG-054", "Seismic rating if required", "Physical", "IBC/ASCE 7", "major"),

            # Standards
            CheckItem("CLG-060", "UL listed (UL 1995)", "Standards", "UL 1995", "major"),
            CheckItem("CLG-061", "ASHRAE 90.4 energy compliance", "Standards", "ASHRAE 90.4", "major"),
            CheckItem("CLG-062", "Factory performance test data provided", "Standards", "AHRI", "minor"),
        ]

    def _evaluate_check(self, item, text, metadata):
        check_id = item.id

        if check_id == "CLG-001":
            tons = re.findall(r'(\d{1,4})\s*ton', text)
            kw_cool = re.findall(r'(\d{2,4})\s*kw.*?cool', text)
            if tons or kw_cool:
                found = f"tons: {tons}" if tons else f"kW: {kw_cool}"
                return self._pass(item, f"Cooling capacity found: {found}")
            return self._fail(item, "No cooling capacity found in submittal")

        if check_id == "CLG-030":
            if any(x in text for x in ["n+1", "2n", "redundan"]):
                return self._pass(item, "Redundancy configuration referenced")
            return self._fail(item, "Cooling redundancy configuration not addressed")

        return super()._evaluate_check(item, text, metadata)
