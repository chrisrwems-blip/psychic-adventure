"""Smart verification — uses Claude Vision to validate text engine findings.

After the text engine produces FAIL and NEEDS REVIEW findings, this service
sends Claude the relevant page image plus the finding details, and asks
Claude to verify whether the finding is correct.

This eliminates false positives and converts ambiguous NEEDS REVIEW items
into definitive PASS or FAIL verdicts.

Cost: ~$0.01-0.03 per finding verified (only image + short prompt).
Typical review: 30-80 findings to verify = $0.30-$2.40.
"""
import logging
import time
from sqlalchemy.orm import Session

from app.models.database_models import ReviewResult, Submittal
from app.services.vision_analyzer import _page_to_image, _ask_claude, _get_backend

logger = logging.getLogger(__name__)


def verify_findings(db: Session, submittal_id: int) -> dict:
    """Run Claude verification on FAIL and NEEDS REVIEW findings."""
    backend, api_key = _get_backend()
    if backend != "claude":
        return {"error": "Claude API required for smart verification. Set ANTHROPIC_API_KEY."}

    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        return {"error": "Submittal not found"}

    # Get findings that need verification (FAIL and NEEDS REVIEW only)
    findings = (
        db.query(ReviewResult)
        .filter(
            ReviewResult.submittal_id == submittal_id,
            ReviewResult.passed.in_([0, -1]),
            ReviewResult.check_category != "AI Vision Analysis",  # don't re-verify vision findings
        )
        .all()
    )

    if not findings:
        return {"verified": 0, "message": "No findings to verify"}

    print(f"[verify] Starting verification of {len(findings)} findings")

    verified = 0
    upgraded = 0
    downgraded = 0
    confirmed = 0
    consecutive_failures = 0

    for finding in findings:
        # Extract page number from finding details
        page_num = _extract_page_number(finding.details or finding.check_name)
        if not page_num:
            print(f"[verify] Skipping finding {finding.id}: no page number found")
            continue

        print(f"[verify] Verifying finding {finding.id} on page {page_num}: {finding.check_name[:60]}")

        # Convert page to image
        image_bytes = _page_to_image(submittal.file_path, page_num)
        if not image_bytes:
            print(f"[verify] Skipping finding {finding.id}: image conversion failed for page {page_num}")
            logger.warning("[verify] Could not convert page %d to image", page_num)
            continue

        # Build verification prompt
        status_word = "FAILED" if finding.passed == 0 else "NEEDS REVIEW"
        prompt = f"""You are a senior electrical engineer verifying an automated review finding.

The automated tool flagged this on Page {page_num}:

CHECK: {finding.check_name}
STATUS: {status_word}
DETAILS: {finding.details}
STANDARD: {finding.reference_standard}

Look at the drawing/document page carefully and answer:

1. Is this finding CORRECT? Does the page actually show the issue described?
2. If the finding is WRONG (false positive), explain what the page actually shows.
3. If the finding is CORRECT, confirm it and note any additional details visible.

Respond with one of these verdicts on the FIRST LINE:
- VERIFIED CORRECT — the finding is accurate
- FALSE POSITIVE — the finding is wrong, here's what the page actually shows
- PARTIALLY CORRECT — the finding has merit but needs qualification
- CANNOT DETERMINE — the page doesn't contain enough information to verify

Then explain your reasoning in 2-3 sentences."""

        # Rate limit: wait between API calls to stay under token limits
        time.sleep(3)

        answer = _ask_claude(image_bytes, prompt, api_key)
        if not answer:
            print(f"[verify] No Claude response for finding {finding.id}")
            consecutive_failures += 1
            if consecutive_failures >= 5:
                print("[verify] 5 consecutive failures — stopping (likely out of credits or rate limited)")
                break
            logger.warning("[verify] No response for finding %d on page %d", finding.id, page_num)
            continue

        verified += 1
        consecutive_failures = 0  # reset on success
        first_line = answer.strip().split("\n")[0].upper()
        print(f"[verify] Finding {finding.id} verdict: {first_line[:80]}")

        # Update finding based on Claude's verdict
        if "FALSE POSITIVE" in first_line:
            # Upgrade to PASS — the text engine was wrong
            finding.passed = 1
            finding.details = (finding.details or "") + f" | AI Verification: FALSE POSITIVE — {answer.strip()}"
            upgraded += 1
            logger.info("[verify] Finding %d UPGRADED to PASS (false positive)", finding.id)

        elif "VERIFIED CORRECT" in first_line:
            # Confirmed — keep as FAIL
            finding.details = (finding.details or "") + f" | AI Verification: CONFIRMED — {answer.strip()}"
            confirmed += 1
            logger.info("[verify] Finding %d CONFIRMED as %s", finding.id, status_word)

        elif "PARTIALLY CORRECT" in first_line:
            # Keep status but add context
            finding.details = (finding.details or "") + f" | AI Verification: PARTIAL — {answer.strip()}"
            logger.info("[verify] Finding %d PARTIALLY CONFIRMED", finding.id)

        elif "CANNOT DETERMINE" in first_line:
            # Keep as needs review
            finding.passed = -1
            finding.details = (finding.details or "") + f" | AI Verification: INCONCLUSIVE — {answer.strip()}"
            logger.info("[verify] Finding %d INCONCLUSIVE", finding.id)

        else:
            # Unexpected response — append as note
            finding.details = (finding.details or "") + f" | AI Verification: {answer.strip()[:300]}"

        db.commit()

    result = {
        "verified": verified,
        "total_findings": len(findings),
        "false_positives_removed": upgraded,
        "confirmed_issues": confirmed,
        "skipped": len(findings) - verified,
        "estimated_cost": f"${verified * 0.02:.2f}",
    }
    print(f"[verify] COMPLETE: {result}")
    return result


def _extract_page_number(text: str) -> int | None:
    """Extract page number from finding details text."""
    import re
    # Match patterns like "Page 16:", "(Page 7)", "pg 12"
    match = re.search(r"(?:Page|pg)\s*(\d+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
