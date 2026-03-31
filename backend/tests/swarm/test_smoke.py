"""Smoke tests — verify PDF generation and text extraction roundtrip.

These tests validate that:
1. ReportLab PDFs are readable by PyPDF2
2. Text extraction returns expected content
3. Page classifier identifies SLD and schedule pages correctly
4. Equipment extractor finds expected entries
5. The full pipeline runs without crashes
"""
import os
import pytest

from tests.swarm.pdf_gen.base_builder import SubmittalBuilder
from tests.swarm.pdf_gen.sld_page import default_sld_breakers, build_sld_lines, SLDBreaker
from tests.swarm.pdf_gen.schedule_page import sld_to_schedule_breakers, build_schedule_lines
from tests.swarm.conftest import run_review_pipeline


def _build_clean_submittal(tmpdir: str) -> str:
    """Build a clean submittal PDF with no errors."""
    pdf_path = os.path.join(tmpdir, "clean_submittal.pdf")
    builder = SubmittalBuilder()

    sld_breakers = default_sld_breakers()
    sld_lines = build_sld_lines(sld_breakers)
    builder.add_sld_page("MDB-A", sld_lines)

    schedule_breakers = sld_to_schedule_breakers(sld_breakers)
    schedule_lines = build_schedule_lines(schedule_breakers)
    builder.add_schedule_page("MDB-A", schedule_lines)

    builder.build(pdf_path)
    return pdf_path


class TestPDFGeneration:
    def test_pdf_created(self, tmp_pdf_dir):
        pdf_path = _build_clean_submittal(tmp_pdf_dir)
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0

    def test_text_extraction(self, tmp_pdf_dir):
        from app.services.pdf_parser import extract_text_by_page

        pdf_path = _build_clean_submittal(tmp_pdf_dir)
        pages = extract_text_by_page(pdf_path)

        assert len(pages) >= 2
        # Page 1: SLD
        sld_text = pages[0]["text"].lower()
        assert "single line diagram" in sld_text
        assert "-qf1/q1" in sld_text.replace(" ", "").lower() or "qf1/q1" in sld_text
        # Page 2+: Schedule (may overflow to multiple pages)
        sched_text = pages[1]["text"].lower()
        assert "panel schedule" in sched_text or "breaker details" in sched_text


class TestPageClassification:
    def test_sld_classified(self, tmp_pdf_dir):
        from app.services.pdf_parser import extract_text_by_page, extract_metadata_by_page
        from app.services.page_classifier import classify_all_pages

        pdf_path = _build_clean_submittal(tmp_pdf_dir)
        pages = extract_text_by_page(pdf_path)
        pages = extract_metadata_by_page(pages)
        pages = classify_all_pages(pages)

        assert pages[0].get("page_type") == "single_line_diagram"
        assert pages[1].get("page_type") in ("panel_schedule", "equipment_schedule")


class TestEquipmentExtraction:
    def test_breakers_extracted(self, tmp_pdf_dir):
        from app.services.pdf_parser import extract_text_by_page, extract_metadata_by_page
        from app.services.page_classifier import classify_all_pages
        from app.services.equipment_extractor import extract_all_equipment

        pdf_path = _build_clean_submittal(tmp_pdf_dir)
        pages = extract_text_by_page(pdf_path)
        pages = extract_metadata_by_page(pages)
        pages = classify_all_pages(pages)
        equipment = extract_all_equipment(pages)

        # Should find breakers from the SLD
        breaker_types = [eq for eq in equipment if eq.equipment_type == "breaker"]
        assert len(breaker_types) >= 3, f"Expected at least 3 breakers, got {len(breaker_types)}"


class TestSLDScheduleExtraction:
    def test_sld_entries_extracted(self, tmp_pdf_dir):
        from app.services.pdf_parser import extract_text_by_page, extract_metadata_by_page
        from app.services.page_classifier import classify_all_pages
        from app.services.sld_schedule_crosscheck import extract_schedule_entries

        pdf_path = _build_clean_submittal(tmp_pdf_dir)
        pages = extract_text_by_page(pdf_path)
        pages = extract_metadata_by_page(pages)
        pages = classify_all_pages(pages)
        sld_entries, schedule_entries = extract_schedule_entries(pages)

        assert len(sld_entries) >= 5, f"Expected >= 5 SLD entries, got {len(sld_entries)}"
        assert len(schedule_entries) >= 5, f"Expected >= 5 schedule entries, got {len(schedule_entries)}"

        # Verify Q-designations match
        sld_qs = {e.q_designation for e in sld_entries}
        sched_qs = {e.q_designation for e in schedule_entries}
        assert "Q1" in sld_qs, f"Q1 not found in SLD entries: {sld_qs}"
        assert "Q1" in sched_qs, f"Q1 not found in schedule entries: {sched_qs}"


class TestFullPipeline:
    def test_pipeline_runs_without_crash(self, tmp_pdf_dir):
        pdf_path = _build_clean_submittal(tmp_pdf_dir)
        results = run_review_pipeline(pdf_path)

        assert "checklist_findings" in results
        assert "xref_findings" in results
        assert "sld_xcheck_findings" in results
        assert len(results["checklist_findings"]) > 0
        assert len(results["pages"]) >= 2
