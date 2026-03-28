"""Tests for the PDF parser service."""
from app.services.pdf_parser import extract_metadata


class TestExtractMetadata:
    def test_extracts_voltages(self):
        text = "System voltage: 480VAC, 208V output"
        meta = extract_metadata(text)
        assert "voltages_found" in meta
        assert 480 in meta["voltages_found"]
        assert 208 in meta["voltages_found"]

    def test_extracts_amperage(self):
        text = "Main breaker: 4000 Amp, branch: 200A"
        meta = extract_metadata(text)
        assert "amperage_found" in meta
        assert 4000 in meta["amperage_found"]
        assert 200 in meta["amperage_found"]

    def test_extracts_kva(self):
        text = "Transformer rated 2000kVA"
        meta = extract_metadata(text)
        assert "kva_found" in meta
        assert 2000 in meta["kva_found"]

    def test_extracts_kw(self):
        text = "Generator output: 2000kW standby"
        meta = extract_metadata(text)
        assert "kw_found" in meta
        assert 2000 in meta["kw_found"]

    def test_extracts_frequency(self):
        meta_60 = extract_metadata("Rated at 60Hz")
        assert meta_60.get("frequency") == 60

        meta_50 = extract_metadata("Rated at 50 Hz")
        assert meta_50.get("frequency") == 50

    def test_extracts_manufacturers(self):
        meta = extract_metadata("Eaton switchgear with Schneider PDUs")
        assert "manufacturers" in meta
        assert "eaton" in meta["manufacturers"]
        assert "schneider" in meta["manufacturers"]

    def test_extracts_standards(self):
        meta = extract_metadata("Per NEC 110.26 and IEEE 1584 requirements")
        assert "standards_referenced" in meta
        assert any("nec" in s for s in meta["standards_referenced"])

    def test_empty_text(self):
        meta = extract_metadata("")
        assert meta == {}

    def test_no_matches(self):
        meta = extract_metadata("This is just some random text with no technical data")
        # Should still return a dict, just empty or with few matches
        assert isinstance(meta, dict)
