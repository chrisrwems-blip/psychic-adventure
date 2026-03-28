import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class TransformerChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "transformer"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Ratings
            CheckItem("TX-001", "kVA rating matches design requirements", "Ratings", "NEC 450, IEEE C57", "critical"),
            CheckItem("TX-002", "Primary voltage and configuration (delta/wye)", "Ratings", "NEC 450", "critical"),
            CheckItem("TX-003", "Secondary voltage and configuration (delta/wye)", "Ratings", "NEC 450", "critical"),
            CheckItem("TX-004", "Impedance percentage specified", "Ratings", "IEEE C57.12", "critical"),
            CheckItem("TX-005", "Frequency (60Hz) confirmed", "Ratings", "NEC 450", "major"),
            CheckItem("TX-006", "BIL rating for primary and secondary", "Ratings", "IEEE C57.12", "major"),
            CheckItem("TX-007", "Tap range and tap positions (FCBN typically +/-2.5%x2)", "Ratings", "IEEE C57.12", "major"),

            # Construction
            CheckItem("TX-010", "Type: dry-type or liquid-filled as specified", "Construction", "NEC 450", "critical"),
            CheckItem("TX-011", "Insulation class (H: 180C, F: 155C typical)", "Construction", "IEEE C57.12.01", "major"),
            CheckItem("TX-012", "Temperature rise class (80C, 115C, 150C)", "Construction", "IEEE C57.12.01", "major"),
            CheckItem("TX-013", "K-factor rating for harmonic loads if applicable", "Construction", "IEEE C57.110", "major"),
            CheckItem("TX-014", "Copper or aluminum windings as specified", "Construction", "Project Spec", "major"),
            CheckItem("TX-015", "Electrostatic shield between windings", "Construction", "IEEE C57.12.01", "minor"),

            # Efficiency & DOE
            CheckItem("TX-020", "DOE 2016 efficiency compliance", "Efficiency", "10 CFR 431", "critical"),
            CheckItem("TX-021", "No-load losses documented", "Efficiency", "IEEE C57.12.01", "major"),
            CheckItem("TX-022", "Full-load losses documented", "Efficiency", "IEEE C57.12.01", "major"),
            CheckItem("TX-023", "Efficiency at 35% and 50% loading", "Efficiency", "DOE/ENERGY STAR", "minor"),

            # Physical
            CheckItem("TX-030", "Dimensions and clearances per NEC 450", "Physical", "NEC 450.21/22", "major"),
            CheckItem("TX-031", "Weight for structural considerations", "Physical", "Project Spec", "major"),
            CheckItem("TX-032", "Sound level (dBA) documented", "Physical", "NEMA ST-20", "minor"),
            CheckItem("TX-033", "Ventilation requirements specified", "Physical", "NEC 450.9", "major"),
            CheckItem("TX-034", "Seismic rating if required", "Physical", "IBC/ASCE 7", "major"),

            # Protection
            CheckItem("TX-040", "Primary overcurrent protection per NEC 450.3", "Protection", "NEC 450.3", "critical"),
            CheckItem("TX-041", "Secondary overcurrent protection per NEC 450.3", "Protection", "NEC 450.3", "critical"),
            CheckItem("TX-042", "Temperature monitoring (winding and ambient)", "Protection", "IEEE C57.12", "major"),
            CheckItem("TX-043", "Surge arresters if required", "Protection", "IEEE C62.11", "minor"),

            # Standards
            CheckItem("TX-050", "UL listed (UL 1561 dry-type, UL 1562 >600V)", "Standards", "UL 1561/1562", "major"),
            CheckItem("TX-051", "IEEE C57.12.01 (dry) or C57.12.00 (liquid) compliance", "Standards", "IEEE C57", "major"),
            CheckItem("TX-052", "Factory test report included (routine tests)", "Standards", "IEEE C57.12.01", "minor"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        check_id = item.id

        if check_id == "TX-001":
            kva = re.findall(r'(\d{2,5})\s*kva', text)
            if kva:
                return self._pass(item, f"kVA found: {kva}. Verify matches design.")
            return self._fail(item, "No kVA rating found")

        if check_id == "TX-004":
            imp = re.search(r'(\d+\.?\d*)\s*%?\s*impedance', text)
            if imp:
                return self._pass(item, f"Impedance {imp.group(1)}% found. Verify for fault current calcs.")
            return self._fail(item, "Impedance not specified — critical for coordination study")

        if check_id == "TX-020":
            if any(x in text for x in ["doe", "efficiency", "10 cfr", "energy star"]):
                return self._pass(item, "Efficiency/DOE compliance referenced. Verify meets DOE 2016.")
            return self._fail(item, "DOE 2016 efficiency compliance not documented")

        return super()._evaluate_check(item, text, metadata)
