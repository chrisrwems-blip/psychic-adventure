import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class PDUChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "pdu"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Ratings
            CheckItem("PDU-001", "Input voltage and phase configuration correct", "Ratings", "NEC 210/215", "critical"),
            CheckItem("PDU-002", "Output voltage(s) specified (208V, 120V as required)", "Ratings", "NEC 210", "critical"),
            CheckItem("PDU-003", "kVA capacity matches design load", "Ratings", "NEC 215", "critical"),
            CheckItem("PDU-004", "Input amperage rating and breaker size", "Ratings", "NEC 215", "critical"),
            CheckItem("PDU-005", "Number and rating of output breakers matches panel schedule", "Ratings", "NEC 408", "critical"),

            # Transformer
            CheckItem("PDU-010", "Transformer type specified (K-rated for harmonics)", "Transformer", "IEEE C57.110", "critical"),
            CheckItem("PDU-011", "K-factor rating (K-13 or K-20 typical for data center)", "Transformer", "IEEE C57.110", "major"),
            CheckItem("PDU-012", "Transformer impedance specified", "Transformer", "IEEE C57", "major"),
            CheckItem("PDU-013", "Electrostatic shield between primary and secondary", "Transformer", "Project Spec", "minor"),
            CheckItem("PDU-014", "Temperature rise class (115C or 150C)", "Transformer", "IEEE C57", "major"),
            CheckItem("PDU-015", "200% neutral rated for harmonic currents", "Transformer", "IEEE C57.110", "critical"),

            # Output Distribution
            CheckItem("PDU-020", "Output panelboard breaker schedule provided", "Distribution", "NEC 408", "major"),
            CheckItem("PDU-021", "Subfeed breaker provisions if required", "Distribution", "NEC 408", "minor"),
            CheckItem("PDU-022", "Output whip lengths and connector types specified", "Distribution", "Project Spec", "major"),
            CheckItem("PDU-023", "Color coding for A/B distribution paths", "Distribution", "Project Spec", "minor"),

            # Monitoring
            CheckItem("PDU-030", "Per-breaker monitoring (branch circuit monitoring)", "Monitoring", "Project Spec", "major"),
            CheckItem("PDU-031", "Input power metering (V, A, kW, kWh, PF)", "Monitoring", "Project Spec", "major"),
            CheckItem("PDU-032", "Network connectivity (SNMP, Modbus, BACnet)", "Monitoring", "Project Spec", "minor"),
            CheckItem("PDU-033", "Environmental sensors (temp, humidity) supported", "Monitoring", "Project Spec", "minor"),
            CheckItem("PDU-034", "Alarm thresholds configurable", "Monitoring", "Project Spec", "minor"),

            # Physical
            CheckItem("PDU-040", "Dimensions fit row-end or overhead installation", "Physical", "Project Spec", "major"),
            CheckItem("PDU-041", "Weight for structural/seismic considerations", "Physical", "Project Spec", "major"),
            CheckItem("PDU-042", "Top/bottom cable entry as designed", "Physical", "Project Spec", "minor"),
            CheckItem("PDU-043", "Color/finish matches project standard", "Physical", "Project Spec", "minor"),

            # Safety & Standards
            CheckItem("PDU-050", "UL 891 or UL 67 listing", "Standards", "UL 891/67", "major"),
            CheckItem("PDU-051", "SCCR rating adequate", "Standards", "NEC 110.10", "critical"),
            CheckItem("PDU-052", "Ground fault protection if required", "Standards", "NEC 210.13", "major"),

            # Redundancy
            CheckItem("PDU-060", "Dual-input (ATS type) if required by topology", "Redundancy", "Uptime Tier III", "major"),
            CheckItem("PDU-061", "Maintenance bypass provisions", "Redundancy", "Uptime Tier III", "major"),
        ]

    def _evaluate_check(self, item, text, metadata):
        check_id = item.id

        if check_id == "PDU-003":
            kva = re.findall(r'(\d{2,4})\s*kva', text)
            if kva:
                return self._needs_review(item, f"kVA found: {kva}. Verify matches design load.")
            return self._fail(item, "No kVA capacity found")

        if check_id == "PDU-011":
            if re.search(r'k-?\s*(\d{1,2})', text):
                return self._needs_review(item, "K-factor rating found. Verify K-13 or K-20 for DC loads.")
            return self._fail(item, "K-factor rating not specified — critical for data center harmonic loads")

        if check_id == "PDU-015":
            if any(x in text for x in ["200%", "200 %", "double neutral", "oversized neutral"]):
                return self._needs_review(item, "Oversized neutral referenced. Verify 200% rated.")
            return self._fail(item, "200% neutral rating not found — required for harmonic-rich DC loads")

        return super()._evaluate_check(item, text, metadata)

    def _pass(self, item, d):
        return ReviewFinding(item.id, item.check, item.category, 1, d, item.standard, item.severity)
    def _fail(self, item, d):
        return ReviewFinding(item.id, item.check, item.category, 0, d, item.standard, item.severity)
    def _needs_review(self, item, d):
        return ReviewFinding(item.id, item.check, item.category, -1, d, item.standard, item.severity)
