"""Smart full submittal package review — deduplicates, filters irrelevant checks, groups by issue.

Design principles:
1. Run the checklist for EVERY equipment type discovered in the document
2. Check the FULL document before declaring something missing
3. One finding per check per equipment type (not per page or per item)
4. No spec-dependent checks unless a spec is uploaded
5. No inapplicable checks (e.g., AFCI/GFCI in data center)
6. Focus on: NEC code compliance, life safety, constructability, actual mistakes
7. Comments only for actionable critical/major items
"""
from datetime import datetime, timezone
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, ReviewResult, ReviewComment, SubmittalStatus
from app.review_engine.registry import get_checker, CHECKER_REGISTRY
from app.services.pdf_parser import extract_text_by_page, extract_metadata_by_page, extract_metadata
from app.services.page_classifier import classify_all_pages, get_page_summary, PageType
from app.services.equipment_extractor import extract_all_equipment, ExtractedEquipment
from app.services.cross_reference import run_cross_reference, CrossRefFinding
from app.services.topology import build_topology
from app.services.jurisdiction import detect_jurisdiction
from app.services.sld_schedule_crosscheck import extract_schedule_entries, crosscheck_sld_vs_schedule
from app.services.naming_checker import check_naming_consistency


# Checks that don't apply to data center interiors
DC_IRRELEVANT_CHECK_IDS = {
    "PNL-040",  # Surface/flush mount — modular construction, not typical
    "PNL-042",  # Door-in-door — spec preference, not code
}

# Check IDs that require a project spec to be meaningful
SPEC_DEPENDENT_CHECK_IDS = {
    "PNL-012", "PNL-014", "PNL-022", "PNL-031", "PNL-050", "PNL-051",
    "SW-020", "SW-023", "SW-030", "SW-032", "SW-033", "SW-035",
    "SW-050", "SW-051", "SW-052", "SW-062",
    "UPS-032", "UPS-033", "UPS-034", "UPS-036",
    "UPS-041", "UPS-042", "UPS-043", "UPS-052",
    "GEN-009", "GEN-010", "GEN-021", "GEN-041", "GEN-047", "GEN-053",
    "ATS-033", "ATS-034", "ATS-042",
    "CLG-053", "CLG-054",
    "BD-032", "BD-042",
    "TX-032",
    "CBL-014", "CBL-015",
    "RPP-010", "RPP-013",
    "BAT-018",
}

# Page types where running equipment checks makes no sense
SKIP_PAGE_TYPES = {
    PageType.COVER_SHEET,
    PageType.TABLE_OF_CONTENTS,
}

# Map extracted equipment types to checker types
EQUIPMENT_TO_CHECKER = {
    "transformer": "transformer",
    "breaker": "switchgear",
    "circuit_breaker": "panelboard",
    "panel": "panelboard",
    "cable": "cable",
    "generator": "generator",
    "ups": "ups",
    "ats": "ats",
    "pdu": "pdu",
    "motor": "switchgear",
}


def _run_checker_against_full_doc(checker, pages, global_metadata, has_spec):
    """Run a single checker's full checklist against the entire document.

    Each check searches every page for relevance, uses the best-matching page,
    and falls back to full-text. Returns one finding per check item.
    """
    findings = []
    checklist = checker.get_checklist()
    full_text_lower = "\n".join(p["text_lower"] for p in pages)

    for item in checklist:
        if item.id in DC_IRRELEVANT_CHECK_IDS:
            continue
        if item.id in SPEC_DEPENDENT_CHECK_IDS and not has_spec:
            continue

        keywords = checker._extract_keywords(item.check)
        relevant = [kw for kw in keywords if len(kw) > 2]

        # Find which page has the most relevant content
        best_page = None
        best_score = 0
        for page_data in pages:
            if page_data.get("page_type") in SKIP_PAGE_TYPES:
                continue
            score = sum(1 for kw in relevant if kw in page_data["text_lower"])
            if score > best_score:
                best_score = score
                best_page = page_data

        if best_page and best_score > 0:
            finding = checker._evaluate_check(item, best_page["text_lower"], global_metadata)
            finding.page_number = best_page["page"]
            if finding.passed != 0 and "(Page" not in finding.details:
                finding.details = f"(Page {best_page['page']}) {finding.details}"
        else:
            # Fallback: check full document text
            finding = checker._evaluate_check(item, full_text_lower, global_metadata)
            if finding.passed == 1 and "(Found" not in finding.details:
                finding.details = f"(Found in document) {finding.details}"

        findings.append(finding)

    return findings


def run_full_review(db: Session, submittal_id: int, has_spec: bool = False) -> dict:
    """Run a smart, deduplicated review of the entire submittal package."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise ValueError(f"Submittal {submittal_id} not found")

    submittal.status = SubmittalStatus.REVIEWING
    db.commit()

    # --- Step 1: Extract and classify ---
    pages = extract_text_by_page(submittal.file_path)
    pages = extract_metadata_by_page(pages)
    pages = classify_all_pages(pages)
    page_summary = get_page_summary(pages)

    full_text = "\n".join(p["text"] for p in pages)
    global_metadata = extract_metadata(full_text)

    # --- Step 1b: Detect jurisdiction (NEC vs IEC) ---
    jurisdiction = detect_jurisdiction(pages, global_metadata)

    # --- Step 2: Extract all equipment ---
    all_equipment = extract_all_equipment(pages)

    # --- Step 3: Determine which checker types to run ---
    # Always run the user-selected type
    checker_types_to_run = {submittal.equipment_type}

    # Run checkers for every equipment type discovered in the document
    for eq in all_equipment:
        mapped = EQUIPMENT_TO_CHECKER.get(eq.equipment_type)
        if mapped and mapped in CHECKER_REGISTRY:
            checker_types_to_run.add(mapped)

    # For large submittals, auto-detect which checkers to run based on page classification
    # If there are panel schedules, run the panelboard checker. If SLDs, run switchgear. Etc.
    PAGE_TYPE_TO_CHECKERS = {
        "single_line_diagram": ["switchgear", "transformer", "cable", "panelboard"],
        "panel_schedule": ["panelboard"],
        "cable_schedule": ["cable"],
        "equipment_schedule": ["switchgear", "transformer", "ups", "generator", "ats"],
        "load_schedule": ["switchgear", "transformer"],
        "cut_sheet": [],  # Don't auto-add from cut sheets — too generic
    }
    for page_type, count in page_summary.items():
        if count > 0 and page_type in PAGE_TYPE_TO_CHECKERS:
            for ct in PAGE_TYPE_TO_CHECKERS[page_type]:
                if ct in CHECKER_REGISTRY:
                    checker_types_to_run.add(ct)

    # For any submittal over 50 pages, also check for common DC equipment
    if len(pages) > 50:
        for ct in ["switchgear", "panelboard", "cable", "transformer"]:
            checker_types_to_run.add(ct)

    # --- Step 4: Run each checker type ONCE against the full document ---
    all_findings = []
    checkers_run = []

    for checker_type in sorted(checker_types_to_run):
        try:
            checker = get_checker(checker_type)
        except ValueError:
            continue

        findings = _run_checker_against_full_doc(checker, pages, global_metadata, has_spec)
        all_findings.extend(findings)
        checkers_run.append(checker_type)

    # --- Step 4b: Build system topology ---
    topology = build_topology(all_equipment, pages)

    # --- Step 4c: SLD vs Schedule cross-check ---
    sld_entries, schedule_entries = extract_schedule_entries(pages)
    sld_xcheck_findings = crosscheck_sld_vs_schedule(sld_entries, schedule_entries)
    naming_findings = check_naming_consistency(pages)
    sld_xcheck_findings.extend(naming_findings)

    # --- Step 5: Cross-reference equipment (topology-aware) ---
    cross_ref_findings = run_cross_reference(all_equipment, topology, pages)
    cross_ref_findings.extend(sld_xcheck_findings)

    # Add jurisdiction warnings as findings
    for warning in jurisdiction.warnings:
        cross_ref_findings.append(CrossRefFinding(
            finding_type="jurisdiction_warning",
            severity="critical",
            equipment_1="System",
            equipment_2=None,
            page_number=0,
            description=warning,
            reference_code=f"{jurisdiction.code} jurisdiction detected ({jurisdiction.confidence:.0%} confidence)",
            recommendation="Verify all equipment is listed/certified for the installation jurisdiction.",
        ))

    # Check for IEC-only equipment in NEC jurisdiction
    if jurisdiction.code == "NEC":
        full_text_lower = full_text.lower()
        # Look for IEC-only certifications without corresponding UL
        for eq in all_equipment:
            raw = (eq.raw_text or "").lower()
            has_iec_only = ("iec" in raw or "ce " in raw) and "ul" not in raw
            # Only flag if this is a major piece of equipment (breaker, panel, transformer)
            if has_iec_only and eq.equipment_type in ("breaker", "panel", "transformer"):
                # Check if UL listing exists elsewhere for this equipment
                model_text = eq.model or eq.designation
                if model_text.lower() not in full_text_lower or "ul" not in full_text_lower:
                    continue  # Can't determine — skip
                cross_ref_findings.append(CrossRefFinding(
                    finding_type="listing_mismatch",
                    severity="critical",
                    equipment_1=eq.designation,
                    equipment_2=None,
                    page_number=eq.page_number,
                    description=(
                        f"Page {eq.page_number}: {eq.designation} — IEC certification referenced but "
                        f"no UL listing found for this specific equipment. System is 480V/60Hz (NEC jurisdiction). "
                        f"All equipment must be UL listed or recognized for installation in the United States."
                    ),
                    reference_code="NEC 110.2, 110.3",
                    recommendation="Verify UL listing for this equipment. IEC-only certification is not acceptable for NEC installations.",
                ))

    # Deduplicate cross-ref by core issue
    seen_xref = set()
    unique_xref = []
    for xref in cross_ref_findings:
        key = (xref.finding_type, xref.equipment_1, xref.severity)
        if key not in seen_xref:
            seen_xref.add(key)
            unique_xref.append(xref)
    cross_ref_findings = unique_xref

    # --- Step 6: Save to database ---
    db.query(ReviewResult).filter(ReviewResult.submittal_id == submittal_id).delete()
    db.query(ReviewComment).filter(
        ReviewComment.submittal_id == submittal_id,
        ReviewComment.category == "automated_review"
    ).delete()

    for finding in all_findings:
        result = ReviewResult(
            submittal_id=submittal_id,
            check_name=finding.check_name,
            check_category=finding.category,
            passed=finding.passed,
            details=finding.details,
            reference_standard=finding.reference_standard,
        )
        db.add(result)

        # Comments only for actionable issues
        should_comment = (
            (finding.passed == 0 and finding.severity in ("critical", "major"))
            or (finding.passed == -1 and finding.severity == "critical")
        )
        if should_comment:
            comment = ReviewComment(
                submittal_id=submittal_id,
                comment_text=f"[{finding.check_id}] {finding.details}",
                category="automated_review",
                severity=finding.severity,
                reference_code=finding.reference_standard,
                page_number=finding.page_number,
            )
            db.add(comment)

    for xref in cross_ref_findings:
        result = ReviewResult(
            submittal_id=submittal_id,
            check_name=xref.description[:255],
            check_category=f"Cross-Reference: {xref.finding_type}",
            passed=0 if xref.severity in ("critical", "major") else -1,
            details=f"{xref.description} | Recommendation: {xref.recommendation}",
            reference_standard=xref.reference_code,
        )
        db.add(result)

        if xref.severity in ("critical", "major"):
            comment = ReviewComment(
                submittal_id=submittal_id,
                comment_text=f"[XREF] {xref.description}",
                category="automated_review",
                severity=xref.severity,
                reference_code=xref.reference_code,
                page_number=xref.page_number if xref.page_number > 0 else None,
            )
            db.add(comment)

    submittal.status = SubmittalStatus.REVIEWED
    submittal.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # --- Build summary ---
    total_checks = len(all_findings) + len(cross_ref_findings)
    passed = sum(1 for f in all_findings if f.passed == 1)
    failed = (
        sum(1 for f in all_findings if f.passed == 0)
        + sum(1 for x in cross_ref_findings if x.severity in ("critical", "major"))
    )
    needs_review = (
        sum(1 for f in all_findings if f.passed == -1)
        + sum(1 for x in cross_ref_findings if x.severity not in ("critical", "major"))
    )
    critical = (
        sum(1 for f in all_findings if f.passed != 1 and f.severity == "critical")
        + sum(1 for x in cross_ref_findings if x.severity == "critical")
    )
    major = (
        sum(1 for f in all_findings if f.passed != 1 and f.severity == "major")
        + sum(1 for x in cross_ref_findings if x.severity == "major")
    )

    comment_count = db.query(ReviewComment).filter(
        ReviewComment.submittal_id == submittal_id,
        ReviewComment.category == "automated_review"
    ).count()

    if critical > 0:
        recommendation = "REVISE AND RESUBMIT — Critical issues found"
    elif failed > 10 or major > 5:
        recommendation = "REVISE AND RESUBMIT — Multiple significant issues"
    elif failed > 0:
        recommendation = "APPROVED AS NOTED — Address comments before fabrication"
    elif needs_review > total_checks * 0.5:
        recommendation = "REQUIRES MANUAL REVIEW — Insufficient data for automated review"
    else:
        recommendation = "APPROVED — No significant issues found"

    return {
        "submittal_id": submittal_id,
        "equipment_type": submittal.equipment_type,
        "review_type": "full_package",
        "jurisdiction": jurisdiction.code,
        "jurisdiction_confidence": jurisdiction.confidence,
        "jurisdiction_warnings": jurisdiction.warnings,
        "total_pages": len(pages),
        "page_breakdown": page_summary,
        "checkers_run": checkers_run,
        "equipment_found": [
            {
                "type": eq.equipment_type,
                "designation": eq.designation,
                "page": eq.page_number,
                "voltage": eq.voltage,
                "amperage": eq.amperage,
                "kva": eq.kva,
                "kw": eq.kw,
            }
            for eq in all_equipment
        ],
        "equipment_count": len(all_equipment),
        "sld_entries": len(sld_entries),
        "schedule_entries": len(schedule_entries),
        "sld_schedule_findings": len(sld_xcheck_findings),
        "topology_nodes": len(topology.nodes),
        "topology_relationships": len(topology.relationships),
        "topology_root_nodes": topology.root_nodes[:10],
        "total_checks": total_checks,
        "passed": passed,
        "failed": failed,
        "needs_review": needs_review,
        "critical_issues": critical,
        "major_issues": major,
        "comments_generated": comment_count,
        "cross_reference_findings": len(cross_ref_findings),
        "checks_skipped_no_spec": len(SPEC_DEPENDENT_CHECK_IDS) if not has_spec else 0,
        "recommendation": recommendation,
    }
