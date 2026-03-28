"""Full submittal package review — scans every page, finds every equipment, runs every check."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, ReviewResult, ReviewComment, SubmittalStatus
from app.review_engine.registry import get_checker, CHECKER_REGISTRY
from app.services.pdf_parser import extract_text_by_page, extract_metadata_by_page, extract_metadata
from app.services.page_classifier import classify_all_pages, get_page_summary, PageType
from app.services.equipment_extractor import extract_all_equipment, ExtractedEquipment
from app.services.cross_reference import run_cross_reference, CrossRefFinding


def run_full_review(db: Session, submittal_id: int) -> dict:
    """Run a comprehensive review of the entire submittal package.

    1. Extract text from every page
    2. Classify every page (SLD, panel schedule, cut sheet, etc.)
    3. Extract every piece of equipment from every page
    4. Run the appropriate checklist for each equipment type found
    5. Cross-reference equipment against each other
    6. Generate findings with accurate page numbers
    """
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise ValueError(f"Submittal {submittal_id} not found")

    submittal.status = SubmittalStatus.REVIEWING
    db.commit()

    # --- Step 1: Extract text page by page ---
    pages = extract_text_by_page(submittal.file_path)
    pages = extract_metadata_by_page(pages)
    full_text = "\n".join(p["text"] for p in pages)
    global_metadata = extract_metadata(full_text)

    # --- Step 2: Classify every page ---
    pages = classify_all_pages(pages)
    page_summary = get_page_summary(pages)

    # --- Step 3: Extract all equipment ---
    all_equipment = extract_all_equipment(pages)

    # --- Step 4: Run checklists per equipment type ---
    # Group equipment by type
    equipment_by_type: dict[str, list[ExtractedEquipment]] = {}
    for eq in all_equipment:
        equipment_by_type.setdefault(eq.equipment_type, [])
        equipment_by_type[eq.equipment_type].append(eq)

    # Map extracted types to checker types
    TYPE_TO_CHECKER = {
        "transformer": "transformer",
        "breaker": "switchgear",
        "circuit_breaker": "panelboard",
        "panel": "panelboard",
        "cable": "cable",
        "generator": "generator",
        "ups": "ups",
        "ats": "ats",
        "pdu": "pdu",
        "motor": "switchgear",  # motors checked under switchgear/MCC
    }

    all_findings = []

    # Run equipment-specific checklists
    for eq_type, items in equipment_by_type.items():
        checker_type = TYPE_TO_CHECKER.get(eq_type)
        if not checker_type or checker_type not in CHECKER_REGISTRY:
            continue

        checker = get_checker(checker_type)

        for equipment_item in items:
            # Build context: the page text where this equipment was found
            eq_pages = [p for p in pages if p["page"] == equipment_item.page_number]
            if not eq_pages:
                continue

            # Run checks against the equipment's page
            item_findings = checker.run_checks_by_page(eq_pages, global_metadata)

            # Tag each finding with the equipment designation
            for f in item_findings:
                f.page_number = equipment_item.page_number
                # Prefix details with equipment designation
                f.details = f"[{equipment_item.designation}] {f.details}"

            all_findings.extend(item_findings)

    # Also run the user-selected equipment type checker against the full document
    # (this catches things the equipment extractor might miss)
    try:
        main_checker = get_checker(submittal.equipment_type)
        main_findings = main_checker.run_checks_by_page(pages, global_metadata)
        # Tag these as "general" review
        for f in main_findings:
            if not any(ef.check_id == f.check_id and ef.page_number == f.page_number for ef in all_findings):
                f.details = f"[General Review] {f.details}"
                all_findings.append(f)
    except ValueError:
        pass

    # --- Step 5: Cross-reference checks ---
    cross_ref_findings = run_cross_reference(all_equipment)

    # --- Step 6: Save everything to database ---
    # Clear old results
    db.query(ReviewResult).filter(ReviewResult.submittal_id == submittal_id).delete()
    db.query(ReviewComment).filter(
        ReviewComment.submittal_id == submittal_id,
        ReviewComment.category == "automated_review"
    ).delete()

    # Save checklist findings
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

        if finding.passed == 0 or (finding.passed == -1 and finding.severity in ("critical", "major")):
            comment = ReviewComment(
                submittal_id=submittal_id,
                comment_text=f"[{finding.check_id}] {finding.details}",
                category="automated_review",
                severity=finding.severity,
                reference_code=finding.reference_standard,
                page_number=finding.page_number,
            )
            db.add(comment)

    # Save cross-reference findings
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

    # Update status
    submittal.status = SubmittalStatus.REVIEWED
    submittal.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # --- Build summary ---
    total_checks = len(all_findings) + len(cross_ref_findings)
    passed = sum(1 for f in all_findings if f.passed == 1)
    failed = sum(1 for f in all_findings if f.passed == 0) + sum(1 for x in cross_ref_findings if x.severity in ("critical", "major"))
    needs_review = sum(1 for f in all_findings if f.passed == -1) + sum(1 for x in cross_ref_findings if x.severity not in ("critical", "major"))
    critical = (
        sum(1 for f in all_findings if f.passed != 1 and f.severity == "critical")
        + sum(1 for x in cross_ref_findings if x.severity == "critical")
    )
    major = (
        sum(1 for f in all_findings if f.passed != 1 and f.severity == "major")
        + sum(1 for x in cross_ref_findings if x.severity == "major")
    )

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
        "total_pages": len(pages),
        "page_breakdown": page_summary,
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
        "total_checks": total_checks,
        "passed": passed,
        "failed": failed,
        "needs_review": needs_review,
        "critical_issues": critical,
        "major_issues": major,
        "cross_reference_findings": len(cross_ref_findings),
        "recommendation": recommendation,
    }
