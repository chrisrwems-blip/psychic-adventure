"""Unit tests for the equipment extractor — verifies it correctly identifies equipment from text."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.equipment_extractor import extract_all_equipment


def _make_page(page_num: int, text: str, page_type: str = "single_line_diagram"):
    return {
        "page": page_num,
        "text": text,
        "text_lower": text.lower(),
        "page_type": page_type,
    }


class TestABBBreakerExtraction:
    def test_e_series_acb(self):
        page = _make_page(1, "E6.2H 4000 EkipTouch LSIG 4000 SOURCE A INCOMER")
        equip = extract_all_equipment([page])
        e62 = [e for e in equip if "E6.2" in (e.designation or "")]
        assert len(e62) >= 1, f"Should find E6.2H 4000, got {[e.designation for e in equip]}"
        assert e62[0].frame_size == "4000A"
        assert e62[0].manufacturer == "ABB"

    def test_xt7_mccb(self):
        page = _make_page(1, "XT7H 1000 Ekip Touch Measuring LSI 1000 UPS UIB A")
        equip = extract_all_equipment([page])
        xt7 = [e for e in equip if "XT7H" in (e.designation or "")]
        assert len(xt7) >= 1, f"Should find XT7H 1000, got {[e.designation for e in equip]}"
        assert xt7[0].frame_size == "1000A"

    def test_xt2_mccb(self):
        page = _make_page(1, "XT2H 125 Ekip Touch MEASURING LSI 60 RACK PLUG")
        equip = extract_all_equipment([page])
        xt2 = [e for e in equip if "XT2H" in (e.designation or "")]
        assert len(xt2) >= 1, f"Should find XT2H 125, got {[e.designation for e in equip]}"
        assert xt2[0].frame_size == "125A"

    def test_does_not_match_ul_file_numbers(self):
        """UL file numbers like E230163 should NOT be extracted as breakers."""
        page = _make_page(1, "UL file number: E230163. UL file: E319777.", "cut_sheet")
        equip = extract_all_equipment([page])
        breakers = [e for e in equip if e.equipment_type == "breaker"]
        for b in breakers:
            assert "E230163" not in b.designation, f"E230163 is a UL file, not a breaker"
            assert "E319777" not in b.designation, f"E319777 is a UL file, not a breaker"

    def test_does_not_match_dse_controllers(self):
        """DSE controller numbers like DSE7320 should NOT be breakers."""
        page = _make_page(1, "DSE7320 MKII Auto Mains Failure Control Module DSE2548")
        equip = extract_all_equipment([page])
        breakers = [e for e in equip if e.equipment_type == "breaker"]
        for b in breakers:
            assert "7320" not in b.designation, f"DSE7320 is a controller, not a breaker"

    def test_generic_breaker_format(self):
        """Test extraction of '3P 1000A 65kA' generic format."""
        page = _make_page(1, "Q2\nOUTGOING\n3P 1000A 65kA\nFIXED\nXT7H 1000")
        equip = extract_all_equipment([page])
        breakers = [e for e in equip if e.equipment_type == "breaker"]
        assert any(b.interrupting_rating == "65kA" for b in breakers), \
            f"Should extract 65kA interrupting rating, got {[(b.designation, b.interrupting_rating) for b in breakers]}"


class TestTransformerExtraction:
    def test_sn_notation(self):
        """Test ABB Sn=25kVA notation."""
        page = _make_page(1, "-TM1\nUn=0.5/0.21kVDyn5\nSn=25kVA\n-B16")
        equip = extract_all_equipment([page])
        transformers = [e for e in equip if e.equipment_type == "transformer"]
        assert len(transformers) >= 1, "Should find 25kVA transformer from Sn= notation"
        assert transformers[0].kva == "25"

    def test_sn_not_load(self):
        """Sn= on a chiller/pump/rack should NOT be extracted as transformer."""
        page = _make_page(1, "CHILLER1\nSn=416.67[kVA]\nCHILLER2\nSn=416.67[kVA]")
        equip = extract_all_equipment([page])
        transformers = [e for e in equip if e.equipment_type == "transformer"]
        assert len(transformers) == 0, f"Chillers should not be transformers, got {[t.designation for t in transformers]}"

    def test_standard_transformer(self):
        page = _make_page(1, "TRANSFORMER 300 kVA 480V Primary (Input), 208V Secondary (Output) 60 Hz")
        equip = extract_all_equipment([page])
        transformers = [e for e in equip if e.equipment_type == "transformer"]
        assert len(transformers) >= 1, "Should find 300kVA transformer"
        assert transformers[0].kva == "300"


class TestMetricCableExtraction:
    def test_metric_cable(self):
        """Test extraction of metric cable format: 6Rx1Cx300mm."""
        page = _make_page(1, "6Rx1Cx300mm2/phase\n+6Rx1Cx150mm2 CPC")
        equip = extract_all_equipment([page])
        cables = [e for e in equip if e.equipment_type == "cable"]
        assert len(cables) >= 1, f"Should find metric cables, got {[e.designation for e in equip]}"
        # Check that runs are captured
        cable_300 = [c for c in cables if "300" in (c.conductor_size or "")]
        assert len(cable_300) >= 1, "Should find 300mm² cable"


class TestPanelExtraction:
    def test_named_panel(self):
        page = _make_page(1, "MAIN DISTRIBUTION PANEL\n480V 4000A BUSBAR", "single_line_diagram")
        equip = extract_all_equipment([page])
        panels = [e for e in equip if e.equipment_type == "panel"]
        assert len(panels) >= 1, f"Should find panel, got {[e.designation for e in equip]}"

    def test_no_panels_from_cut_sheets(self):
        """Cut sheet text about 'panel builders' should NOT create panel equipment."""
        page = _make_page(1, "worldwide to panel builders, who construct and offer complete panel systems", "cut_sheet")
        equip = extract_all_equipment([page])
        panels = [e for e in equip if e.equipment_type == "panel"]
        assert len(panels) == 0, f"Cut sheet marketing text should not create panels, got {[p.designation for p in panels]}"


class TestSourceTagging:
    def test_sld_source_tagged(self):
        page = _make_page(1, "E6.2H 4000 SOURCE A", "single_line_diagram")
        equip = extract_all_equipment([page])
        for e in equip:
            assert e.attributes.get("source_page_type") == "single_line_diagram"

    def test_cut_sheet_source_tagged(self):
        page = _make_page(1, "XT7H 1000 Ekip Touch", "cut_sheet")
        equip = extract_all_equipment([page])
        for e in equip:
            assert e.attributes.get("source_page_type") == "cut_sheet"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
