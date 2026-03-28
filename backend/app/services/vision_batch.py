"""Background vision analysis — runs AI vision on drawing pages after the main review.

Automatically identifies pages that need vision analysis:
- SLD pages with little extractable text (drawings without text layers)
- GA/layout drawings (for clearance verification)
- Cut sheets flagged as potentially IEC-only (for UL verification)

Runs as a background task — main review completes immediately with
text-based results. Vision findings append as they complete.
"""
import os
import threading
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.database_models import Submittal, ReviewResult, ReviewComment
from app.services.vision_analyzer import (
    is_vision_available, analyze_sld_page, analyze_cutsheet_for_ul,
    analyze_clearances, VisionResult,
)
from app.services.pdf_parser import extract_text_by_page
from app.services.page_classifier import classify_all_pages, PageType


# Track running jobs
_running_jobs: dict[int, dict] = {}  # submittal_id -> status dict


def get_vision_job_status(submittal_id: int) -> dict:
    """Get the status of a running or completed vision analysis job."""
    if submittal_id in _running_jobs:
        return _running_jobs[submittal_id]
    return {"status": "not_started", "pages_total": 0, "pages_complete": 0, "findings": 0}


def start_vision_analysis(submittal_id: int):
    """Start background vision analysis for a submittal. Non-blocking."""
    vision = is_vision_available()
    if not vision["available"]:
        _running_jobs[submittal_id] = {
            "status": "unavailable",
            "backend": "none",
            "message": "No vision backend available. Install Ollama + LLaVA or set ANTHROPIC_API_KEY.",
            "pages_total": 0,
            "pages_complete": 0,
            "findings": 0,
        }
        return

    _running_jobs[submittal_id] = {
        "status": "starting",
        "backend": vision["backend"],
        "pages_total": 0,
        "pages_complete": 0,
        "findings": 0,
    }

    thread = threading.Thread(target=_run_vision_job, args=(submittal_id,), daemon=True)
    thread.start()


def _run_vision_job(submittal_id: int):
    """Background thread that runs vision analysis on relevant pages."""
    db = SessionLocal()
    try:
        submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
        if not submittal or not os.path.exists(submittal.file_path):
            _running_jobs[submittal_id]["status"] = "error"
            _running_jobs[submittal_id]["message"] = "Submittal or file not found"
            return

        # Get pages and classify them
        pages = extract_text_by_page(submittal.file_path)
        pages = classify_all_pages(pages)

        # Identify pages that need vision analysis
        pages_to_analyze = []

        for page_data in pages:
            page_num = page_data["page"]
            page_type = page_data.get("page_type", "unknown")
            text_len = len(page_data.get("text", ""))

            # SLD pages with little text — drawing needs visual reading
            if page_type == PageType.SLD and text_len < 200:
                pages_to_analyze.append((page_num, "sld", "SLD with minimal text — visual analysis needed"))

            # GA/layout drawings
            if page_type == PageType.PLAN_DRAWING:
                pages_to_analyze.append((page_num, "clearance", "Layout drawing — check clearances"))

            # Pages with no text at all (likely scanned drawings)
            if text_len < 30 and page_type not in (PageType.COVER_SHEET, PageType.TABLE_OF_CONTENTS):
                pages_to_analyze.append((page_num, "nameplate", "No text layer — OCR/vision needed"))

        # Cap at 50 pages to keep processing reasonable
        pages_to_analyze = pages_to_analyze[:50]

        _running_jobs[submittal_id]["status"] = "running"
        _running_jobs[submittal_id]["pages_total"] = len(pages_to_analyze)

        findings_count = 0

        for i, (page_num, analysis_type, reason) in enumerate(pages_to_analyze):
            _running_jobs[submittal_id]["pages_complete"] = i

            try:
                if analysis_type == "sld":
                    result = analyze_sld_page(submittal.file_path, page_num)
                elif analysis_type == "clearance":
                    result = analyze_clearances(submittal.file_path, page_num)
                else:
                    # Generic nameplate/OCR analysis
                    from app.services.vision_analyzer import analyze_nameplate
                    result = analyze_nameplate(submittal.file_path, page_num)

                if result and result.answer:
                    # Save as review result
                    db_result = ReviewResult(
                        submittal_id=submittal_id,
                        check_name=f"[Vision AI] Page {page_num}: {reason}",
                        check_category="AI Vision Analysis",
                        passed=-1,  # needs human review
                        details=f"Page {page_num} ({result.backend} analysis): {result.answer[:500]}",
                        reference_standard="AI Vision",
                    )
                    db.add(db_result)

                    # If the answer mentions concerns, create a comment
                    answer_lower = result.answer.lower()
                    is_concern = any(kw in answer_lower for kw in [
                        "not ul", "no ul", "iec only", "violation", "undersized",
                        "inadequate", "missing", "does not meet", "clearance",
                        "less than", "insufficient",
                    ])

                    if is_concern:
                        comment = ReviewComment(
                            submittal_id=submittal_id,
                            comment_text=f"[Vision AI] Page {page_num}: {result.answer[:300]}",
                            category="vision_analysis",
                            severity="major",
                            page_number=page_num,
                        )
                        db.add(comment)
                        findings_count += 1

                    db.commit()

            except Exception as e:
                # Log but don't stop the whole job
                pass

            _running_jobs[submittal_id]["pages_complete"] = i + 1
            _running_jobs[submittal_id]["findings"] = findings_count

        _running_jobs[submittal_id]["status"] = "complete"
        _running_jobs[submittal_id]["pages_complete"] = len(pages_to_analyze)

    except Exception as e:
        _running_jobs[submittal_id]["status"] = "error"
        _running_jobs[submittal_id]["message"] = str(e)
    finally:
        db.close()
