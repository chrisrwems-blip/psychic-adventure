"""
Feedback Router

Endpoints for recording engineer feedback on findings and retrieving
learning statistics (suppression/priority lists).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import FindingFeedback, Submittal
from app.services.learning import (
    record_feedback,
    get_suppression_list,
    get_priority_list,
    apply_learning,
)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


# --- Schemas ---

class FeedbackCreate(BaseModel):
    finding_type: str
    check_name: str = ""
    action: str  # "agreed", "dismissed", "modified"
    engineer_notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submittal_id: Optional[int]
    finding_type: str
    check_name: Optional[str]
    action: str
    engineer_notes: Optional[str]
    created_at: datetime


class FeedbackStatsResponse(BaseModel):
    suppression_list: list[dict]
    priority_list: list[dict]


class ApplyLearningRequest(BaseModel):
    findings: list[dict]


# --- Routes ---

@router.post("/{submittal_id}", response_model=FeedbackResponse)
def post_feedback(
    submittal_id: int,
    body: FeedbackCreate,
    db: Session = Depends(get_db),
):
    """Record engineer feedback on a finding."""
    # Validate action
    valid_actions = {"agreed", "dismissed", "modified"}
    if body.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{body.action}'. Must be one of: {', '.join(valid_actions)}",
        )

    # Validate submittal exists
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise HTTPException(status_code=404, detail="Submittal not found")

    feedback = record_feedback(
        db=db,
        submittal_id=submittal_id,
        finding_type=body.finding_type,
        check_name=body.check_name,
        action=body.action,
        notes=body.engineer_notes,
    )
    return feedback


@router.get("/stats", response_model=FeedbackStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get suppression and priority lists based on historical feedback."""
    return FeedbackStatsResponse(
        suppression_list=get_suppression_list(db),
        priority_list=get_priority_list(db),
    )


@router.get("/history", response_model=list[FeedbackResponse])
def get_history(
    submittal_id: Optional[int] = Query(None),
    finding_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """List all feedback, with optional filters."""
    query = db.query(FindingFeedback)
    if submittal_id is not None:
        query = query.filter(FindingFeedback.submittal_id == submittal_id)
    if finding_type is not None:
        query = query.filter(FindingFeedback.finding_type == finding_type)
    if action is not None:
        query = query.filter(FindingFeedback.action == action)
    return query.order_by(FindingFeedback.created_at.desc()).limit(limit).all()


@router.post("/apply-learning")
def post_apply_learning(
    body: ApplyLearningRequest,
    db: Session = Depends(get_db),
):
    """
    Apply learning to a list of findings.

    Accepts a list of finding dicts (each must have 'finding_type') and returns
    the reordered list with confidence indicators and suppression/boost markers.
    """
    return {"findings": apply_learning(body.findings, db)}
