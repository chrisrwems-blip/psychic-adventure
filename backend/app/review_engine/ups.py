import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class UPSChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "ups"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Ratings & Capacity
            CheckItem("UPS-001", "kVA/kW rating matches design load requirements", "Ratings", "IEEE 446", "critical"),
            CheckItem("UPS-002", "Input voltage and phase configuration correct", "Ratings", "NEC 480", "critical"),
            CheckItem("UPS-003", "Output voltage regulation within spec (+/- 1% typical)", "Ratings", "IEEE 446", "critical"),
            CheckItem("UPS-004", "Frequency regulation specified (60Hz +/- 0.5%)", "Ratings", "IEEE 446", "major"),
            CheckItem("UPS-005", "Power factor rating specified (0.9 or unity)", "Ratings", "IEEE 446", "major"),
            CheckItem("UPS-006", "Efficiency at 25%, 50%, 75%, 100% load documented", "Ratings", "ENERGY STAR", "minor"),
            CheckItem("UPS-007", "Overload capability specified (125% for 10 min, 150% for 1 min typical)", "Ratings", "IEEE 446", "major"),
            CheckItem("UPS-008", "Input current THD documented (< 5% typical)", "Ratings", "IEEE 519", "major"),
            CheckItem("UPS-009", "Output voltage THD documented (< 3% typical)", "Ratings", "IEEE 519", "major"),

            # Battery System
            CheckItem("UPS-010", "Battery runtime at full load specified", "Battery", "IEEE 1188/1189", "critical"),
            CheckItem("UPS-011", "Battery type specified (VRLA, Li-ion, wet cell)", "Battery", "IEEE 1188", "major"),
            CheckItem("UPS-012", "Battery recharge time specified", "Battery", "IEEE 1188", "minor"),
            CheckItem("UPS-013", "Battery monitoring system included", "Battery", "Project Spec", "major"),
            CheckItem("UPS-014", "Battery cabinet/rack seismic rating if required", "Battery", "IBC/ASCE 7", "major"),
            CheckItem("UPS-015", "Battery room ventilation requirements addressed (for VRLA/wet cell)", "Battery", "NEC 480.9, NFPA 1", "critical"),
            CheckItem("UPS-016", "Battery disconnect provided", "Battery", "NEC 480.7", "major"),
            CheckItem("UPS-017", "Battery string configuration (parallel strings) documented", "Battery", "IEEE 1188", "major"),

            # Redundancy & Topology
            CheckItem("UPS-020", "UPS topology specified (online double-conversion, line-interactive, etc.)", "Topology", "IEEE 446", "critical"),
            CheckItem("UPS-021", "Redundancy level matches tier (N+1, 2N, 2N+1)", "Topology", "Uptime Tier III/IV", "critical"),
            CheckItem("UPS-022", "Static bypass switch included", "Topology", "IEEE 446", "critical"),
            CheckItem("UPS-023", "Maintenance bypass provisions (wrap-around bypass)", "Topology", "Uptime Tier III", "critical"),
            CheckItem("UPS-024", "Parallel capability for redundant configurations", "Topology", "IEEE 446", "major"),
            CheckItem("UPS-025", "Automatic load transfer on UPS failure", "Topology", "IEEE 446", "critical"),

            # Physical & Environmental
            CheckItem("UPS-030", "Dimensions and weight for structural loading", "Physical", "Project Spec", "major"),
            CheckItem("UPS-031", "Heat rejection (BTU/hr or kW) at rated load", "Physical", "Project Spec", "critical"),
            CheckItem("UPS-032", "Airflow requirements (CFM) and direction", "Physical", "Project Spec", "major"),
            CheckItem("UPS-033", "Operating temperature range", "Physical", "Project Spec", "minor"),
            CheckItem("UPS-034", "Noise level (dBA) at rated load", "Physical", "Project Spec", "minor"),
            CheckItem("UPS-035", "Seismic rating per project requirements", "Physical", "IBC/ASCE 7", "major"),
            CheckItem("UPS-036", "IP/NEMA enclosure rating", "Physical", "NEMA 250", "minor"),

            # Monitoring & Communications
            CheckItem("UPS-040", "SNMP card/network monitoring included", "Monitoring", "Project Spec", "major"),
            CheckItem("UPS-041", "Dry contact alarm outputs specified", "Monitoring", "Project Spec", "minor"),
            CheckItem("UPS-042", "BMS/DCIM integration protocol specified", "Monitoring", "Project Spec", "minor"),
            CheckItem("UPS-043", "Front panel display with status indicators", "Monitoring", "Project Spec", "minor"),

            # Standards & Testing
            CheckItem("UPS-050", "UL 1778 listing", "Standards", "UL 1778", "major"),
            CheckItem("UPS-051", "Factory acceptance test (FAT) procedures", "Standards", "IEEE 446", "minor"),
            CheckItem("UPS-052", "Warranty terms documented", "Standards", "Project Spec", "minor"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        check_id = item.id

        if check_id == "UPS-001":
            kva = re.findall(r'(\d{2,5})\s*kva', text)
            kw = re.findall(r'(\d{2,5})\s*kw', text)
            if kva or kw:
                found = f"kVA: {kva}" if kva else f"kW: {kw}"
                return self._pass(item, f"Capacity found: {found}")
            return self._fail(item, "No kVA/kW rating found in submittal")

        if check_id == "UPS-010":
            runtime_patterns = [r'(\d+)\s*min', r'runtime', r'backup\s*time', r'battery\s*time']
            for p in runtime_patterns:
                if re.search(p, text):
                    return self._pass(item, "Battery runtime information found")
            return self._fail(item, "Battery runtime at full load not found — critical for data center")

        if check_id == "UPS-020":
            topologies = ["double.?conversion", "online", "line.?interactive", "delta.?conversion"]
            for t in topologies:
                if re.search(t, text):
                    return self._pass(item, "UPS topology specified")
            return self._fail(item, "UPS topology not specified")

        if check_id == "UPS-021":
            if any(x in text for x in ["n+1", "2n", "n + 1", "2 n", "redundan"]):
                return self._pass(item, "Redundancy configuration referenced")
            return self._fail(item, "Redundancy configuration not addressed")

        if check_id == "UPS-031":
            if any(x in text for x in ["btu", "heat", "thermal", "dissipat", "rejection"]):
                return self._pass(item, "Thermal/heat rejection data found")
            return self._fail(item, "Heat rejection data not found — critical for cooling design")

        return super()._evaluate_check(item, text, metadata)
