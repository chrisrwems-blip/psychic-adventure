"""Unit tests for engineering tables, manufacturer data, and NEC calculations."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestNECAmpacity:
    def test_common_sizes_75c(self):
        from app.services.engineering_tables import NEC_310_16_75C
        assert NEC_310_16_75C["14"] == 20
        assert NEC_310_16_75C["12"] == 25
        assert NEC_310_16_75C["10"] == 35
        assert NEC_310_16_75C["4/0"] == 230
        assert NEC_310_16_75C["500"] == 380
        assert NEC_310_16_75C["1000"] == 545

    def test_all_sizes_positive(self):
        from app.services.engineering_tables import NEC_310_16_75C
        for size, amps in NEC_310_16_75C.items():
            assert amps > 0, f"Size {size} has non-positive ampacity"

    def test_ampacity_increases_with_size(self):
        from app.services.engineering_tables import NEC_310_16_75C
        ordered = ["14", "12", "10", "8", "6", "4", "3", "2", "1",
                    "1/0", "2/0", "3/0", "4/0", "250", "300", "500", "1000"]
        for i in range(len(ordered) - 1):
            assert NEC_310_16_75C[ordered[i]] < NEC_310_16_75C[ordered[i + 1]], \
                f"{ordered[i]} ({NEC_310_16_75C[ordered[i]]}) should be less than {ordered[i+1]} ({NEC_310_16_75C[ordered[i+1]]})"


class TestMetricConversion:
    def test_common_sizes(self):
        from app.services.engineering_tables import mm2_to_approximate_label
        assert "600" in mm2_to_approximate_label(300)  # 300mm² ≈ 600 kcmil
        assert "300" in mm2_to_approximate_label(150)
        assert "4/0" in mm2_to_approximate_label(120)

    def test_iec_ampacity(self):
        from app.services.engineering_tables import mm2_ampacity, IEC_AMPACITY_3PHASE
        # 300mm² PVC should be 394A per IEC
        assert mm2_ampacity(300, "pvc") == 394
        # 150mm² PVC should be 260A
        assert mm2_ampacity(150, "pvc") == 260
        # XLPE should be higher than PVC
        assert mm2_ampacity(300, "xlpe") > mm2_ampacity(300, "pvc")

    def test_iec_ampacity_all_positive(self):
        from app.services.engineering_tables import IEC_AMPACITY_3PHASE
        for size, amps in IEC_AMPACITY_3PHASE.items():
            assert amps > 0, f"{size}mm² has non-positive ampacity"


class TestStandardBreakerSizes:
    def test_next_standard_size(self):
        from app.services.engineering_tables import next_standard_size
        assert next_standard_size(15) == 15
        assert next_standard_size(16) == 20
        assert next_standard_size(100) == 100
        assert next_standard_size(101) == 110
        assert next_standard_size(361) == 400  # 300kVA transformer at 480V
        assert next_standard_size(451) == 500  # 125% of 361A
        assert next_standard_size(6000) == 6000
        assert next_standard_size(1) == 15  # Below minimum

    def test_small_wire_rule(self):
        from app.services.engineering_tables import NEC_240_4_D
        assert NEC_240_4_D["14"] == 15
        assert NEC_240_4_D["12"] == 20
        assert NEC_240_4_D["10"] == 30


class TestTransformerCalculations:
    def test_fla_3phase_480v(self):
        from app.services.engineering_tables import transformer_fla
        # 300kVA at 480V 3-phase: FLA = 300000 / (480 * 1.732) = 361A
        fla = transformer_fla(300, 480)
        assert abs(fla - 361) < 1

    def test_fla_3phase_208v(self):
        from app.services.engineering_tables import transformer_fla
        # 300kVA at 208V 3-phase: FLA = 300000 / (208 * 1.732) = 833A
        fla = transformer_fla(300, 208)
        assert abs(fla - 833) < 1

    def test_fla_1phase(self):
        from app.services.engineering_tables import transformer_fla
        # 25kVA at 240V 1-phase: FLA = 25000 / 240 = 104A
        fla = transformer_fla(25, 240, phases=1)
        assert abs(fla - 104) < 1

    def test_max_primary_ocpd_without_secondary(self):
        from app.services.engineering_tables import transformer_max_primary_ocpd
        # 300kVA at 480V: FLA=361A, 125% = 451A, next standard = 500A
        result = transformer_max_primary_ocpd(300, 480, has_secondary_protection=False)
        assert result == 500

    def test_max_primary_ocpd_with_secondary(self):
        from app.services.engineering_tables import transformer_max_primary_ocpd
        # 300kVA at 480V: FLA=361A, 250% = 902A, next standard = 1000A
        result = transformer_max_primary_ocpd(300, 480, has_secondary_protection=True)
        assert result == 1000

    def test_max_secondary_ocpd(self):
        from app.services.engineering_tables import transformer_max_secondary_ocpd
        # 300kVA at 208V: FLA=833A, 125% = 1041A, next standard = 1200A
        result = transformer_max_secondary_ocpd(300, 208)
        assert result == 1200

    def test_secondary_fault_current(self):
        from app.services.engineering_tables import transformer_secondary_fault_current
        # 2000kVA, 480V, 5.75% Z: AFC = FLA / (Z/100)
        # FLA = 2000000 / (480 * 1.732) = 2406A
        # AFC = 2406 / 0.0575 = 41,843A = ~42kA
        afc = transformer_secondary_fault_current(2000, 480, 5.75)
        assert abs(afc - 41843) < 100

    def test_small_transformer_fault_current(self):
        from app.services.engineering_tables import transformer_secondary_fault_current
        # 25kVA, 208V, 5.75% Z
        afc = transformer_secondary_fault_current(25, 208, 5.75)
        assert afc > 0
        assert afc < 5000  # Should be modest for a small transformer


class TestGroundingConductor:
    def test_min_egc_sizes(self):
        from app.services.engineering_tables import min_egc_size
        assert min_egc_size(15) == "14"
        assert min_egc_size(20) == "12"
        assert min_egc_size(60) == "10"
        assert min_egc_size(100) == "8"
        assert min_egc_size(200) == "6"
        assert min_egc_size(400) == "3"
        assert min_egc_size(1000) == "2/0"
        assert min_egc_size(4000) == "500"

    def test_egc_between_sizes(self):
        from app.services.engineering_tables import min_egc_size
        # 150A is between 100 and 200 in the table — should return for 200
        result = min_egc_size(150)
        assert result == "6"


class TestClearances:
    def test_480v_condition_2(self):
        from app.services.engineering_tables import required_clearance
        assert required_clearance(480, condition=2) == 42

    def test_480v_condition_1(self):
        from app.services.engineering_tables import required_clearance
        assert required_clearance(480, condition=1) == 36

    def test_120v(self):
        from app.services.engineering_tables import required_clearance
        assert required_clearance(120) == 36  # All conditions are 36" for 0-150V


class TestVoltageDrop:
    def test_voltage_drop_3ph(self):
        from app.services.engineering_tables import voltage_drop_3ph
        # 100ft, 200A, #4/0 AWG, 480V — should be small
        vd = voltage_drop_3ph(100, 200, "4/0", 480)
        assert vd > 0
        assert vd < 3  # Should be well under 3%

    def test_voltage_drop_long_run(self):
        from app.services.engineering_tables import voltage_drop_3ph
        # 500ft, 100A, #4 AWG, 480V — should be significant
        vd = voltage_drop_3ph(500, 100, "4", 480)
        assert vd > 2  # Should be noticeable


class TestABBValidation:
    def test_valid_e_series(self):
        from app.services.manufacturer_data.abb import validate_abb_breaker
        r = validate_abb_breaker("E6.2H4000")
        assert r["valid"], f"E6.2H4000 should be valid: {r}"

    def test_valid_xt_series(self):
        from app.services.manufacturer_data.abb import validate_abb_breaker
        r = validate_abb_breaker("XT7H1000")
        assert r["valid"], f"XT7H1000 should be valid: {r}"

    def test_invalid_frame_too_big(self):
        from app.services.manufacturer_data.abb import validate_abb_breaker
        r = validate_abb_breaker("XT5H800")
        assert not r["valid"], "XT5H800 should be invalid (max frame 630A)"
        assert "630" in r["issues"][0]

    def test_invalid_frame_too_small(self):
        from app.services.manufacturer_data.abb import validate_abb_breaker
        r = validate_abb_breaker("E6.2H1000")
        assert not r["valid"], "E6.2H1000 should be invalid (min frame 3200A)"

    def test_unparseable(self):
        from app.services.manufacturer_data.abb import validate_abb_breaker
        r = validate_abb_breaker("GARBAGE123")
        assert not r["valid"]

    def test_icu_lookup(self):
        from app.services.manufacturer_data.abb import get_abb_icu
        assert get_abb_icu("E6.2", "H") == 85
        assert get_abb_icu("XT7", "L") == 100
        assert get_abb_icu("E6.2", "Z") is None  # Invalid suffix


class TestNECCommentary:
    def test_exact_match(self):
        from app.services.nec_commentary import get_commentary
        c = get_commentary("NEC 110.9")
        assert c["title"] == "Interrupting Rating"
        assert "fault" in c["why_it_matters"].lower()

    def test_partial_match(self):
        from app.services.nec_commentary import get_commentary
        c = get_commentary("NEC 240.87, NEC 240.12")
        assert c["title"] == "Arc Energy Reduction"

    def test_no_match(self):
        from app.services.nec_commentary import get_commentary
        c = get_commentary("totally fake code")
        assert c == {}

    def test_all_entries_have_fields(self):
        from app.services.nec_commentary import NEC_COMMENTARY
        for code, entry in NEC_COMMENTARY.items():
            assert "title" in entry, f"{code} missing title"
            assert "text" in entry, f"{code} missing text"
            assert "why_it_matters" in entry, f"{code} missing why_it_matters"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
