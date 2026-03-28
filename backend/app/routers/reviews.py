from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import ReviewResult, Submittal
from app.models.schemas import ReviewResultResponse
from app.services.review_service import run_review
from app.services.full_review_service import run_full_review
from app.review_engine.registry import get_available_equipment_types

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


@router.get("/equipment-types")
def list_equipment_types():
    """List all supported equipment types."""
    return {"equipment_types": get_available_equipment_types()}
