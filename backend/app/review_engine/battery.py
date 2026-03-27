from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class BatteryChecker(BaseEquipmentChecker):
    """Battery system checker (standalone BESS or UPS batteries)."""
    def equipment_type(self) -> str:
        return "battery"

    def get_checklist(self) -> list[CheckItem]:
        return [
            CheckItem("BAT-001", "Battery chemistry specified (VRLA, Li-ion, NiCd)", "Chemistry", "IEEE 1188/1189/1187", "critical"),
            CheckItem("BAT-002", "Capacity (Ah) matches runtime requirements", "Ratings", "IEEE 485", "critical"),
            CheckItem("BAT-003", "Voltage (string voltage) matches UPS/inverter requirements", "Ratings", "IEEE 485", "critical"),
            CheckItem("BAT-004", "Number of strings and parallel configuration", "Configuration", "IEEE 485", "critical"),
            CheckItem("BAT-005", "Runtime at full load documented", "Ratings", "IEEE 485", "critical"),
            CheckItem("BAT-006", "End-of-discharge voltage specified", "Ratings", "IEEE 485", "major"),
            CheckItem("BAT-007", "Design life vs service life documented", "Ratings", "IEEE 1188", "major"),
            CheckItem("BAT-010", "Battery management system (BMS) for Li-ion", "Monitoring", "UL 1973, NFPA 855", "critical"),
            CheckItem("BAT-011", "Cell/jar monitoring system", "Monitoring", "IEEE 1491", "major"),
            CheckItem("BAT-012", "Temperature monitoring per string", "Monitoring", "IEEE 1188", "major"),
            CheckItem("BAT-013", "Thermal runaway detection for Li-ion", "Safety", "NFPA 855", "critical"),
            CheckItem("BAT-014", "Fire suppression requirements for Li-ion", "Safety", "NFPA 855", "critical"),
            CheckItem("BAT-015", "Ventilation/hydrogen detection for VRLA/wet cell", "Safety", "NEC 480.9, NFPA 1", "critical"),
            CheckItem("BAT-016", "Seismic rack/cabinet rating", "Physical", "IBC/ASCE 7", "major"),
            CheckItem("BAT-017", "Weight loading for structural design", "Physical", "Project Spec", "major"),
            CheckItem("BAT-018", "Operating temperature range", "Physical", "IEEE 1188", "major"),
            CheckItem("BAT-019", "Battery disconnect switch provided", "Safety", "NEC 480.7", "critical"),
            CheckItem("BAT-020", "Spill containment for wet cell/VRLA", "Safety", "NEC 480.9", "major"),
            CheckItem("BAT-021", "UL 1973 listing (Li-ion) or UL certification", "Standards", "UL 1973", "major"),
            CheckItem("BAT-022", "NFPA 855 compliance for energy storage", "Standards", "NFPA 855", "critical"),
            CheckItem("BAT-023", "Recharge time to 80% and 100%", "Ratings", "Project Spec", "major"),
        ]

    def _evaluate_check(self, item, text, metadata):
        check_id = item.id

        if check_id == "BAT-001":
            chems = ["vrla", "lithium", "li-ion", "lion", "lead acid", "nickel cadmium", "nicd"]
            found = [c for c in chems if c in text]
            if found:
                return self._needs_review(item, f"Battery chemistry: {found[0]}. Verify matches spec.")
            return self._fail(item, "Battery chemistry not specified")

        if check_id == "BAT-013":
            if any(x in text for x in ["thermal runaway", "thermal management", "nfpa 855"]):
                return self._needs_review(item, "Thermal runaway protection referenced. Verify adequacy for Li-ion.")
            if "li" in text or "lithium" in text:
                return self._fail(item, "Li-ion battery but thermal runaway protection not documented")
            return self._needs_review(item, "Verify if Li-ion — if so, thermal runaway protection required")

        return super()._evaluate_check(item, text, metadata)

    def _pass(self, item, d):
        return ReviewFinding(item.id, item.check, item.category, 1, d, item.standard, item.severity)
    def _fail(self, item, d):
        return ReviewFinding(item.id, item.check, item.category, 0, d, item.standard, item.severity)
    def _needs_review(self, item, d):
        return ReviewFinding(item.id, item.check, item.category, -1, d, item.standard, item.severity)
