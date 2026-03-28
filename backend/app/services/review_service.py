"""Orchestrates the submittal review process."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, ReviewResult, ReviewComment, SubmittalStatus
from app.review_engine.registry import get_checker
from app.services.pdf_parser import extract_text_from_pdf, extract_metadata, extract_text_by_page, extract_metadata_by_page


def run_review(db: Session, submittal_id: int) -> dict:
    """Run automated review on a submittal."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise ValueError(f"Submittal {submittal_id} not found")

    # Update status
    submittal.status = SubmittalStatus.REVIEWING
    db.commit()

    # Extract text page-by-page
    pages = extract_text_by_page(submittal.file_path)
    pages = extract_metadata_by_page(pages)

    # Also get full text for global metadata
    full_text = "\n".join(p["text"] for p in pages)
    global_metadata = extract_metadata(full_text)

    # Get appropriate checker and run
    try:
        checker = get_checker(submittal.equipment_type)
    except ValueError:
        submittal.status = SubmittalStatus.UPLOADED
        db.commit()
        raise

    # Run page-aware checks
    findings = checker.run_checks_by_page(pages, global_metadata)

    # Clear old results
    db.query(ReviewResult).filter(ReviewResult.submittal_id == submittal_id).delete()
    db.query(ReviewComment).filter(
        ReviewComment.submittal_id == submittal_id,
        ReviewComment.category == "automated_review"
    ).delete()

    # Save results and auto-generate comments for failures
    for finding in findings:
        result = ReviewResult(
            submittal_id=submittal_id,
            check_name=finding.check_name,
            check_category=finding.category,
            passed=finding.passed,
            details=finding.details,
            reference_standard=finding.reference_standard,
        )
        db.add(result)

        # Auto-create comments for failures and critical needs-review items
        if finding.passed == 0 or (finding.passed == -1 and finding.severity in ("critical", "major")):
            comment = ReviewComment(
                submittal_id=submittal_id,
                comment_text=f"[{finding.check_id}] {finding.details}",
                category="automated_review",
                severity=finding.severity,
                reference_code=finding.reference_standard,
                page_number=finding.page_number,  # Now includes the actual page!
            )
            db.add(comment)

    # Update submittal status
    submittal.status = SubmittalStatus.REVIEWED
    submittal.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # Build summary
    total = len(findings)
    passed = sum(1 for f in findings if f.passed == 1)
    failed = sum(1 for f in findings if f.passed == 0)
    needs_review = sum(1 for f in findings if f.passed == -1)
    critical = sum(1 for f in findings if f.passed != 1 and f.severity == "critical")
    major = sum(1 for f in findings if f.passed != 1 and f.severity == "major")

    if critical > 0:
        recommendation = "REVISE AND RESUBMIT — Critical issues found"
    elif failed > 5 or major > 3:
        recommendation = "REVISE AND RESUBMIT — Multiple significant issues"
    elif failed > 0:
        recommendation = "APPROVED AS NOTED — Address comments before fabrication"
    elif needs_review > total * 0.5:
        recommendation = "REQUIRES MANUAL REVIEW — Insufficient data for automated review"
    else:
        recommendation = "APPROVED — No significant issues found"

    return {
        "submittal_id": submittal_id,
        "equipment_type": submittal.equipment_type,
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "needs_review": needs_review,
        "critical_issues": critical,
        "major_issues": major,
        "recommendation": recommendation,
        "findings": [
            {
                "check_id": f.check_id,
                "check_name": f.check_name,
                "category": f.category,
                "passed": f.passed,
                "details": f.details,
                "severity": f.severity,
                "reference": f.reference_standard,
                "page_number": f.page_number,
            }
            for f in findings
        ],
    }
