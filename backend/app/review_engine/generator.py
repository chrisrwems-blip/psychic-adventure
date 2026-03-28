import re
from .base import BaseEquipmentChecker, CheckItem, ReviewFinding


class GeneratorChecker(BaseEquipmentChecker):
    def equipment_type(self) -> str:
        return "generator"

    def get_checklist(self) -> list[CheckItem]:
        return [
            # Ratings & Performance
            CheckItem("GEN-001", "Standby kW rating matches design load requirements", "Ratings", "NFPA 110, ISO 8528", "critical"),
            CheckItem("GEN-002", "Prime vs standby rating clearly identified", "Ratings", "ISO 8528", "critical"),
            CheckItem("GEN-003", "Output voltage and phase configuration correct", "Ratings", "NEC 445", "critical"),
            CheckItem("GEN-004", "Frequency regulation specified (+/- 0.5% steady state)", "Ratings", "NFPA 110", "major"),
            CheckItem("GEN-005", "Voltage regulation specified (+/- 1% steady state)", "Ratings", "NFPA 110", "major"),
            CheckItem("GEN-006", "Transient voltage dip on block load specified", "Ratings", "ISO 8528-5", "major"),
            CheckItem("GEN-007", "Transient frequency dip on block load specified", "Ratings", "ISO 8528-5", "major"),
            CheckItem("GEN-008", "Recovery time to rated voltage/frequency specified", "Ratings", "ISO 8528-5", "major"),
            CheckItem("GEN-009", "Altitude derating addressed for site elevation", "Ratings", "ISO 8528", "major"),
            CheckItem("GEN-010", "Ambient temperature derating addressed", "Ratings", "ISO 8528", "major"),

            # Engine
            CheckItem("GEN-015", "Engine manufacturer and model specified", "Engine", "Project Spec", "major"),
            CheckItem("GEN-016", "Fuel type specified (diesel, natural gas, bi-fuel)", "Engine", "NFPA 110", "critical"),
            CheckItem("GEN-017", "Fuel consumption rate at 100% and 75% load", "Engine", "Project Spec", "major"),
            CheckItem("GEN-018", "Fuel storage tank capacity and runtime at full load", "Engine", "NFPA 110 (48hr+ for data center)", "critical"),
            CheckItem("GEN-019", "EPA emissions tier compliance (Tier 4 Final typically required)", "Engine", "EPA 40 CFR 60/89", "critical"),
            CheckItem("GEN-020", "Cooling system type (radiator, remote radiator)", "Engine", "Project Spec", "major"),
            CheckItem("GEN-021", "Lube oil capacity and change interval", "Engine", "Project Spec", "minor"),

            # Alternator
            CheckItem("GEN-025", "Alternator type (brushless, PMG excitation)", "Alternator", "NEMA MG 1", "major"),
            CheckItem("GEN-026", "Winding pitch factor for harmonic mitigation", "Alternator", "NEMA MG 1", "minor"),
            CheckItem("GEN-027", "Insulation class (H typical for data center)", "Alternator", "NEMA MG 1", "major"),
            CheckItem("GEN-028", "Temperature rise class documented", "Alternator", "NEMA MG 1", "major"),

            # Controls & Paralleling
            CheckItem("GEN-030", "Generator controller make/model specified", "Controls", "NFPA 110", "major"),
            CheckItem("GEN-031", "Auto-start capability on utility failure", "Controls", "NFPA 110", "critical"),
            CheckItem("GEN-032", "Start time within 10 seconds (NFPA 110 Level 1)", "Controls", "NFPA 110", "critical"),
            CheckItem("GEN-033", "Paralleling switchgear/controls for multiple generator operation", "Controls", "IEEE 1547, NFPA 110", "critical"),
            CheckItem("GEN-034", "Load sharing (isochronous or droop) specified for paralleling", "Controls", "IEEE 1547", "major"),
            CheckItem("GEN-035", "Dead bus and live bus paralleling capability", "Controls", "Project Spec", "major"),

            # Fuel System
            CheckItem("GEN-040", "Day tank with automatic fill from bulk storage", "Fuel System", "NFPA 110", "critical"),
            CheckItem("GEN-041", "Fuel polishing/filtration system if required", "Fuel System", "Project Spec", "minor"),
            CheckItem("GEN-042", "Secondary containment for fuel storage", "Fuel System", "EPA/Local Code", "critical"),
            CheckItem("GEN-043", "Fuel transfer pumps redundancy", "Fuel System", "NFPA 110", "major"),

            # Exhaust & Sound
            CheckItem("GEN-045", "Exhaust system back-pressure within limits", "Exhaust", "Engine Mfr Spec", "major"),
            CheckItem("GEN-046", "Sound attenuation level specified (dBA at distance)", "Exhaust", "Local Ordinance", "major"),
            CheckItem("GEN-047", "Critical/hospital grade silencer if required", "Exhaust", "Project Spec", "minor"),

            # Physical & Compliance
            CheckItem("GEN-050", "Seismic certification (IBC essential facility)", "Physical", "IBC/ASCE 7", "major"),
            CheckItem("GEN-051", "Enclosure rating (weather-protective or indoor)", "Physical", "NEMA 250", "major"),
            CheckItem("GEN-052", "Dimensions and weight for foundation design", "Physical", "Project Spec", "major"),
            CheckItem("GEN-053", "Vibration isolators specified", "Physical", "Project Spec", "minor"),

            # Redundancy
            CheckItem("GEN-060", "N+1 or 2N redundancy matches tier requirements", "Redundancy", "Uptime Tier III/IV", "critical"),
            CheckItem("GEN-061", "Black start capability without utility", "Redundancy", "NFPA 110", "critical"),
            CheckItem("GEN-062", "Load shedding scheme documented", "Redundancy", "NFPA 110", "major"),

            # Testing
            CheckItem("GEN-070", "Factory load bank test at rated load", "Testing", "NFPA 110", "major"),
            CheckItem("GEN-071", "UL 2200 listing", "Testing", "UL 2200", "major"),
        ]

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        check_id = item.id

        if check_id == "GEN-001":
            kw = re.findall(r'(\d{3,5})\s*kw', text)
            if kw:
                return self._needs_review(item, f"kW ratings found: {kw}. Verify matches design load.")
            return self._fail(item, "No kW rating found in submittal")

        if check_id == "GEN-016":
            fuels = ["diesel", "natural gas", "bi-fuel", "bi fuel"]
            found = [f for f in fuels if f in text]
            if found:
                return self._needs_review(item, f"Fuel type: {found[0]}. Verify matches project spec.")
            return self._fail(item, "Fuel type not specified")

        if check_id == "GEN-019":
            if any(x in text for x in ["tier 4", "tier4", "epa", "emission"]):
                return self._needs_review(item, "Emissions compliance referenced. Verify Tier 4 Final.")
            return self._fail(item, "EPA emissions tier not found — verify compliance")

        if check_id == "GEN-032":
            if any(x in text for x in ["start time", "10 sec", "10sec", "startup"]):
                return self._needs_review(item, "Start time info found. Verify <= 10 seconds for NFPA 110 Level 1.")
            return self._fail(item, "Start time not documented — must be <=10s for data center")

        if check_id == "GEN-060":
            if any(x in text for x in ["n+1", "2n", "redundan", "parallel"]):
                return self._needs_review(item, "Redundancy/paralleling referenced. Verify matches tier.")
            return self._fail(item, "Generator redundancy configuration not addressed")

        return super()._evaluate_check(item, text, metadata)

    def _pass(self, item, details):
        return ReviewFinding(item.id, item.check, item.category, 1, details, item.standard, item.severity)

    def _fail(self, item, details):
        return ReviewFinding(item.id, item.check, item.category, 0, details, item.standard, item.severity)

    def _needs_review(self, item, details):
        return ReviewFinding(item.id, item.check, item.category, -1, details, item.standard, item.severity)
