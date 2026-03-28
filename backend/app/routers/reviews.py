from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import ReviewResult, Submittal
from app.models.schemas import ReviewResultResponse
from app.services.review_service import run_review
from app.review_engine.registry import get_available_equipment_types

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/{submittal_id}/run")
def trigger_review(submittal_id: int, db: Session = Depends(get_db)):
    """Run the automated review engine on a submittal."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise HTTPException(status_code=404, detail="Submittal not found")
    try:
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


@router.get("/equipment-types")
def list_equipment_types():
    """List all supported equipment types."""
    return {"equipment_types": get_available_equipment_types()}
