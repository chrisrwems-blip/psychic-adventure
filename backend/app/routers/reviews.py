import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import ReviewResult, Submittal
from app.models.schemas import ReviewResultResponse
from app.services.review_service import run_review
from app.services.full_review_service import run_full_review
from app.services.report_generator import generate_review_report
from app.services.revision_diff import compare_revisions
from app.review_engine.registry import get_available_equipment_types

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/{submittal_id}/run")
def trigger_review(submittal_id: int, full: bool = True, db: Session = Depends(get_db)):
    """Run the automated review engine on a submittal.

    full=True (default): Full package review — scans every page, finds every
    piece of equipment, runs all applicable checklists, cross-references sizing.

    full=False: Single equipment type review (original behavior).
    """
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise HTTPException(status_code=404, detail="Submittal not found")
    try:
        if full:
            summary = run_full_review(db, submittal_id)
        else:
            summary = run_review(db, submittal_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{submittal_id}/results", response_model=list[ReviewResultResponse])
def get_review_results(submittal_id: int, db: Session = Depends(get_db)):
    """Get review results for a submittal."""
    results = (
        db.query(ReviewResult)
        .filter(ReviewResult.submittal_id == submittal_id)
        .order_by(ReviewResult.check_category, ReviewResult.check_name)
        .all()
    )
    return results


@router.get("/{submittal_id}/report")
def download_review_report(submittal_id: int, db: Session = Depends(get_db)):
    """Generate and download a professional PDF review report.

    This is a standalone report document (not the marked-up submittal).
    Contains cover page, executive summary, jurisdiction, equipment table,
    findings by severity, SLD cross-check, and cross-reference results.
    """
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise HTTPException(status_code=404, detail="Submittal not found")

    # Check that a review has been run
    result_count = db.query(ReviewResult).filter(
        ReviewResult.submittal_id == submittal_id
    ).count()
    if result_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No review results found. Run a review first before generating a report.",
        )

    try:
        report_path = generate_review_report(db, submittal_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")

    if not os.path.exists(report_path):
        raise HTTPException(status_code=500, detail="Report file was not created")

    filename = os.path.basename(report_path)
    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{submittal_id}/diagnose")
def diagnose_submittal(submittal_id: int, db: Session = Depends(get_db)):
    """Diagnostic endpoint — shows what the engine sees in the PDF without running a full review."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise HTTPException(status_code=404, detail="Submittal not found")

    from app.services.pdf_parser import extract_text_by_page, extract_metadata_by_page, extract_metadata
    from app.services.page_classifier import classify_all_pages, get_page_summary
    from app.services.equipment_extractor import extract_all_equipment

    pages = extract_text_by_page(submittal.file_path)
    pages = extract_metadata_by_page(pages)
    pages = classify_all_pages(pages)

    full_text = "\n".join(p["text"] for p in pages)
    global_meta = extract_metadata(full_text)
    page_summary = get_page_summary(pages)
    all_equipment = extract_all_equipment(pages)

    # Sample pages with most text (the real content)
    content_pages = sorted(pages, key=lambda p: len(p["text"]), reverse=True)[:20]

    return {
        "total_pages": len(pages),
        "pages_with_text": sum(1 for p in pages if len(p["text"]) > 50),
        "pages_with_no_text": sum(1 for p in pages if len(p["text"]) <= 50),
        "total_text_chars": len(full_text),
        "page_type_breakdown": page_summary,
        "global_metadata": global_meta,
        "equipment_found": [
            {
                "type": eq.equipment_type,
                "designation": eq.designation,
                "page": eq.page_number,
                "voltage": eq.voltage,
                "amperage": eq.amperage,
                "kva": eq.kva,
                "kw": eq.kw,
                "frame_size": eq.frame_size,
                "trip_rating": eq.trip_rating,
                "conductor_size": eq.conductor_size,
                "raw_text": eq.raw_text[:150],
            }
            for eq in all_equipment
        ],
        "equipment_count": len(all_equipment),
        "top_content_pages": [
            {
                "page": p["page"],
                "chars": len(p["text"]),
                "type": p.get("page_type", "unknown"),
                "preview": p["text"][:300],
            }
            for p in content_pages
        ],
    }


@router.post("/{submittal_id}/compare-revision")
async def compare_revision(
    submittal_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Compare a new revision PDF against the existing submittal's PDF.

    Upload the revised PDF and get back a structured diff showing what changed:
    new/removed equipment, changed ratings, and modified pages.
    """
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise HTTPException(status_code=404, detail="Submittal not found")

    if not submittal.file_path or not os.path.exists(submittal.file_path):
        raise HTTPException(status_code=400, detail="Original submittal PDF not found on disk")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Revision file must be a PDF")

    # Save the revision PDF to a temp location
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    revision_filename = f"revision_{submittal_id}_{file.filename}"
    revision_path = os.path.join(UPLOAD_DIR, revision_filename)

    try:
        with open(revision_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = compare_revisions(submittal.file_path, revision_path)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revision comparison failed: {e}")

    finally:
        # Clean up the temporary revision file
        if os.path.exists(revision_path):
            os.remove(revision_path)


@router.get("/equipment-types")
def list_equipment_types():
    """List all supported equipment types."""
    return {"equipment_types": get_available_equipment_types()}


@router.post("/{submittal_id}/vision-analyze")
def trigger_vision_analysis(submittal_id: int, db: Session = Depends(get_db)):
    """Start background vision AI analysis on drawing pages."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise HTTPException(status_code=404, detail="Submittal not found")

    from app.services.vision_batch import start_vision_analysis
    from app.services.vision_analyzer import is_vision_available

    vision_status = is_vision_available()
    if not vision_status["available"]:
        return {"status": "unavailable", "message": vision_status["details"]}

    start_vision_analysis(submittal_id)
    return {"status": "started", "backend": vision_status["backend"]}


@router.get("/{submittal_id}/vision-status")
def get_vision_status(submittal_id: int):
    """Check the status of a running vision analysis job."""
    from app.services.vision_batch import get_vision_job_status
    return get_vision_job_status(submittal_id)


@router.get("/vision-available")
def check_vision():
    """Check if any vision backend (Ollama or Claude API) is available."""
    from app.services.vision_analyzer import is_vision_available
    return is_vision_available()


@router.get("/nec-commentary/{code_ref:path}")
def get_nec_commentary(code_ref: str):
    """Get NEC code commentary for a specific reference."""
    from app.services.nec_commentary import get_commentary
    commentary = get_commentary(code_ref)
    if not commentary:
        return {"found": False, "code": code_ref}
    return {"found": True, "code": code_ref, **commentary}
