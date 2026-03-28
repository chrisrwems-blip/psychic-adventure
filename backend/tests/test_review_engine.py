"""Tests for the review engine checkers."""
import pytest
from app.review_engine.registry import get_checker, get_available_equipment_types
from app.review_engine.base import BaseEquipmentChecker, ReviewFinding


class TestRegistry:
    def test_all_equipment_types_available(self):
        types = get_available_equipment_types()
        assert "switchgear" in types
        assert "ups" in types
        assert "generator" in types
        assert "pdu" in types
        assert "transformer" in types
        assert "ats" in types
        assert "cable" in types
        assert "bus_duct" in types
        assert "panelboard" in types
        assert "rpp" in types
        assert "sts" in types
        assert "battery" in types
        assert "cooling" in types

    def test_aliases_resolve(self):
        busway = get_checker("busway")
        bus_duct = get_checker("bus_duct")
        assert type(busway) == type(bus_duct)

        crac = get_checker("crac")
        cooling = get_checker("cooling")
        assert type(crac) == type(cooling)

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="No checker"):
            get_checker("nonexistent_equipment")

    def test_get_checker_returns_instance(self):
        checker = get_checker("switchgear")
        assert isinstance(checker, BaseEquipmentChecker)
        assert checker.equipment_type() == "switchgear"


class TestSwitchgearChecker:
    def setup_method(self):
        self.checker = get_checker("switchgear")

    def test_has_checklist(self):
        checklist = self.checker.get_checklist()
        assert len(checklist) > 20  # Switchgear should have many checks

    def test_checklist_ids_unique(self):
        checklist = self.checker.get_checklist()
        ids = [c.id for c in checklist]
        assert len(ids) == len(set(ids)), "Duplicate check IDs found"

    def test_all_checks_have_required_fields(self):
        for item in self.checker.get_checklist():
            assert item.id
            assert item.check
            assert item.category
            assert item.standard
            assert item.severity in ("critical", "major", "minor", "info")

    def test_review_with_voltage_data(self):
        text = "The switchgear is rated at 480V, 3-phase, 60Hz with 65kA short-circuit rating."
        findings = self.checker.run_checks(text, {})
        assert len(findings) > 0
        assert all(isinstance(f, ReviewFinding) for f in findings)

        # Should find voltage
        voltage_finding = next((f for f in findings if f.check_id == "SW-001"), None)
        assert voltage_finding is not None
        assert voltage_finding.passed == 1  # needs review (found but needs human verification)

    def test_review_with_empty_text(self):
        findings = self.checker.run_checks("", {})
        assert len(findings) > 0
        # Most should be failed when text is empty
        failed = [f for f in findings if f.passed == 0]
        assert len(failed) > 5

    def test_sccr_detection(self):
        text = "Short-circuit current rating: 65kA. Bus bracing: 65kA."
        findings = self.checker.run_checks(text, {})
        sccr = next((f for f in findings if f.check_id == "SW-002"), None)
        assert sccr is not None
        assert sccr.passed == 1  # found, needs review

    def test_arc_flash_detection(self):
        text = "Arc flash calculations per IEEE 1584. Incident energy: 8 cal/cm2."
        findings = self.checker.run_checks(text, {})
        arc = next((f for f in findings if f.check_id == "SW-040"), None)
        assert arc is not None
        assert arc.passed == 1

    def test_ground_fault_missing(self):
        text = "Standard switchgear lineup with main breaker."
        findings = self.checker.run_checks(text, {})
        gf = next((f for f in findings if f.check_id == "SW-012"), None)
        assert gf is not None
        assert gf.passed == 0  # fail - not found


class TestUPSChecker:
    def setup_method(self):
        self.checker = get_checker("ups")

    def test_has_checklist(self):
        assert len(self.checker.get_checklist()) > 15

    def test_topology_detection(self):
        text = "Online double-conversion UPS, 500kVA, N+1 redundancy"
        findings = self.checker.run_checks(text, {})
        topology = next((f for f in findings if f.check_id == "UPS-020"), None)
        assert topology is not None
        assert topology.passed == 1  # found

    def test_missing_runtime(self):
        text = "UPS system specifications. Voltage: 480V."
        findings = self.checker.run_checks(text, {})
        runtime = next((f for f in findings if f.check_id == "UPS-010"), None)
        assert runtime is not None
        assert runtime.passed == 0  # fail


class TestGeneratorChecker:
    def setup_method(self):
        self.checker = get_checker("generator")

    def test_kw_detection(self):
        text = "Standby rated 2000kW diesel generator set. EPA Tier 4 Final."
        findings = self.checker.run_checks(text, {})
        kw = next((f for f in findings if f.check_id == "GEN-001"), None)
        assert kw is not None
        assert kw.passed == 1

    def test_emissions_detection(self):
        text = "EPA Tier 4 Final emissions compliant"
        findings = self.checker.run_checks(text, {})
        epa = next((f for f in findings if f.check_id == "GEN-019"), None)
        assert epa is not None
        assert epa.passed == 1


class TestATSChecker:
    def setup_method(self):
        self.checker = get_checker("ats")

    def test_bypass_detection(self):
        text = "ATS with bypass isolation switch included."
        findings = self.checker.run_checks(text, {})
        bypass = next((f for f in findings if f.check_id == "ATS-020"), None)
        assert bypass is not None
        assert bypass.passed == 1


class TestTransformerChecker:
    def setup_method(self):
        self.checker = get_checker("transformer")

    def test_impedance_detection(self):
        text = "Transformer 2000kVA, 5.75% impedance, DOE 2016 compliant"
        findings = self.checker.run_checks(text, {})
        imp = next((f for f in findings if f.check_id == "TX-004"), None)
        assert imp is not None
        assert imp.passed == 1


class TestCableChecker:
    def setup_method(self):
        self.checker = get_checker("cable")

    def test_conductor_detection(self):
        text = "4/0 AWG copper THHN conductors, 500kcmil feeders"
        findings = self.checker.run_checks(text, {})
        cond = next((f for f in findings if f.check_id == "CBL-001"), None)
        assert cond is not None
        assert cond.passed == 1

    def test_copper_detection(self):
        text = "All conductors shall be copper."
        findings = self.checker.run_checks(text, {})
        mat = next((f for f in findings if f.check_id == "CBL-002"), None)
        assert mat is not None
        assert mat.passed == 1


class TestSTSChecker:
    def setup_method(self):
        self.checker = get_checker("sts")

    def test_transfer_time_detection(self):
        text = "Transfer time less than 4ms, quarter cycle operation"
        findings = self.checker.run_checks(text, {})
        xfer = next((f for f in findings if f.check_id == "STS-003"), None)
        assert xfer is not None
        assert xfer.passed == 1


class TestBatteryChecker:
    def setup_method(self):
        self.checker = get_checker("battery")

    def test_chemistry_detection(self):
        text = "Lithium-ion battery system with integrated BMS"
        findings = self.checker.run_checks(text, {})
        chem = next((f for f in findings if f.check_id == "BAT-001"), None)
        assert chem is not None
        assert chem.passed == 1


class TestCoolingChecker:
    def setup_method(self):
        self.checker = get_checker("cooling")

    def test_has_checklist(self):
        assert len(self.checker.get_checklist()) > 15

    def test_capacity_detection(self):
        text = "CRAH unit rated for 200 tons cooling capacity, N+1 redundancy"
        findings = self.checker.run_checks(text, {})
        cap = next((f for f in findings if f.check_id == "CLG-001"), None)
        assert cap is not None
        assert cap.passed == 1
