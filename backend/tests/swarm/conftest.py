"""Shared fixtures and pipeline runner for swarm error tests.

The pipeline runner bypasses the database and calls review services directly,
making tests fast and self-contained.
"""
import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Optional

import pytest

# Ensure the backend app is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.pdf_parser import extract_text_by_page, extract_metadata_by_page, extract_metadata
from app.services.page_classifier import classify_all_pages, get_page_summary
from app.services.equipment_extractor import extract_all_equipment
from app.services.cross_reference import run_cross_reference
from app.services.sld_schedule_crosscheck import extract_schedule_entries, crosscheck_sld_vs_schedule
from app.services.deep_checks import run_deep_equipment_checks
from app.services.naming_checker import check_naming_consistency
from app.services.topology import build_topology
from app.review_engine.registry import get_checker, CHECKER_REGISTRY
from app.services.full_review_service import _run_checker_against_full_doc


@dataclass
class ExpectedFinding:
    """Describes an error we expect the review engine to catch."""
    source: str              # "checklist", "xref", "sld_xcheck", "deep", "naming"
    finding_type: str        # e.g., "frame_mismatch", "cable_undersized"
    severity: str            # "critical", "major", "minor"
    equipment_ref: str       # partial match against equipment designation or description
    description_contains: str = ""  # substring that should appear in finding text


def run_review_pipeline(pdf_path: str) -> dict:
    """Run the full review pipeline on a PDF without database involvement.

    Returns a dict with all result categories for assertion.
    """
    # Step 1: Extract and classify pages
    pages = extract_text_by_page(pdf_path)
    pages = extract_metadata_by_page(pages)
    pages = classify_all_pages(pages)
    page_summary = get_page_summary(pages)

    # Global metadata
    full_text = "\n".join(p["text"] for p in pages)
    global_metadata = extract_metadata(full_text)

    # Step 2: Extract equipment
    equipment = extract_all_equipment(pages)

    # Step 3: Build topology
    topology = build_topology(equipment, pages)

    # Step 4: SLD/schedule extraction
    sld_entries, schedule_entries = extract_schedule_entries(pages)

    # Step 5: Run all checkers
    checklist_findings = []
    for checker_type in sorted(set(CHECKER_REGISTRY.keys())):
        # Skip aliases (busway->bus_duct, crac/crah/chiller->cooling)
        try:
            checker = get_checker(checker_type)
        except ValueError:
            continue
        findings = _run_checker_against_full_doc(checker, pages, global_metadata, False)
        checklist_findings.extend(findings)

    # Step 6: Cross-reference checks
    xref_findings = run_cross_reference(equipment, topology, pages)

    # Step 7: SLD vs schedule cross-check
    sld_xcheck_findings = crosscheck_sld_vs_schedule(sld_entries, schedule_entries)

    # Step 8: Naming consistency
    naming_findings = check_naming_consistency(pages)

    # Step 9: Deep equipment checks
    deep_findings = run_deep_equipment_checks(equipment, sld_entries, schedule_entries, pages)

    return {
        "pages": pages,
        "page_summary": page_summary,
        "equipment": equipment,
        "topology": topology,
        "sld_entries": sld_entries,
        "schedule_entries": schedule_entries,
        "global_metadata": global_metadata,
        "checklist_findings": checklist_findings,
        "xref_findings": xref_findings,
        "sld_xcheck_findings": sld_xcheck_findings,
        "naming_findings": naming_findings,
        "deep_findings": deep_findings,
    }


def assert_finding_present(results: dict, expected: ExpectedFinding) -> bool:
    """Assert that an expected finding exists in the review results.

    Searches the appropriate result list based on expected.source.
    Returns True if found, raises AssertionError if not.
    """
    source_map = {
        "checklist": "checklist_findings",
        "xref": "xref_findings",
        "sld_xcheck": "sld_xcheck_findings",
        "naming": "naming_findings",
        "deep": "deep_findings",
    }

    findings_key = source_map.get(expected.source)
    if not findings_key:
        raise ValueError(f"Unknown source: {expected.source}")

    findings = results[findings_key]
    ref_lower = expected.equipment_ref.lower()
    desc_lower = expected.description_contains.lower() if expected.description_contains else ""

    for f in findings:
        # Get the text to search in based on finding type
        if expected.source == "checklist":
            f_text = f"{f.check_id} {f.check_name} {f.details}".lower()
            f_severity = f.severity
            f_type = f.check_id if hasattr(f, "check_id") else ""
            f_passed = f.passed
        else:
            # CrossRefFinding
            f_text = f"{f.finding_type} {f.equipment_1 or ''} {f.equipment_2 or ''} {f.description}".lower()
            f_severity = f.severity
            f_type = f.finding_type
            f_passed = None

        # For checklist findings, only match failures (passed=0) or needs_review (passed=-1)
        if expected.source == "checklist" and f_passed == 1:
            continue

        # Match criteria
        type_match = (not expected.finding_type) or (expected.finding_type.lower() in f_type.lower())
        severity_match = (not expected.severity) or (f_severity == expected.severity)
        ref_match = (not ref_lower) or (ref_lower in f_text)
        desc_match = (not desc_lower) or (desc_lower in f_text)

        if type_match and severity_match and ref_match and desc_match:
            return True

    # Build helpful error message
    all_texts = []
    for f in findings:
        if expected.source == "checklist":
            if f.passed != 1:
                all_texts.append(f"  [{f.severity}] {f.check_id}: {f.details[:100]}")
        else:
            all_texts.append(f"  [{f.severity}] {f.finding_type}: {f.equipment_1} - {f.description[:100]}")

    findings_str = "\n".join(all_texts[:20]) or "  (none)"
    raise AssertionError(
        f"Expected finding not found:\n"
        f"  source={expected.source}, type={expected.finding_type}, "
        f"severity={expected.severity}, ref={expected.equipment_ref}\n"
        f"  description_contains={expected.description_contains}\n"
        f"Actual {expected.source} findings:\n{findings_str}"
    )


def assert_finding_absent(results: dict, source: str, finding_type: str,
                          equipment_ref: str) -> bool:
    """Assert that a specific finding does NOT exist (no false positive)."""
    try:
        assert_finding_present(results, ExpectedFinding(
            source=source, finding_type=finding_type,
            severity="", equipment_ref=equipment_ref,
        ))
    except AssertionError:
        return True  # Good — not found
    raise AssertionError(
        f"False positive: found unexpected {source}/{finding_type} for {equipment_ref}"
    )


@pytest.fixture
def tmp_pdf_dir():
    """Provide a temporary directory for generated PDFs."""
    with tempfile.TemporaryDirectory(prefix="swarm_test_") as tmpdir:
        yield tmpdir
