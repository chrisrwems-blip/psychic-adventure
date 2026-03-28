import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import RFI, ReviewComment, Submittal
from app.models.schemas import RFICreate, RFIStatusUpdate, RFIResponseUpdate, RFIResponse

router = APIRouter(prefix="/api/rfis", tags=["rfis"])


def _next_rfi_number(db: Session, submittal_id: int) -> str:
    """Generate the next RFI number for a submittal (RFI-001, RFI-002, ...)."""
    count = db.query(func.count(RFI.id)).filter(RFI.submittal_id == submittal_id).scalar()
    return f"RFI-{count + 1:03d}"


def _build_rfi_body(comments: list[ReviewComment]) -> str:
    """Build RFI body text from a list of review comments."""
    lines = ["The following items require clarification or response:\n"]
    for i, c in enumerate(comments, 1):
        page_ref = f"Page {c.page_number}" if c.page_number else "General"
        severity_tag = f"[{(c.severity or 'major').upper()}]"
        code_ref = f" ({c.reference_code})" if c.reference_code else ""
        lines.append(f"{i}. {severity_tag} {page_ref}{code_ref}: {c.comment_text}")
    lines.append("\nPlease respond to each item above with the requested information or corrective action.")
    return "\n".join(lines)


@router.get("/all", response_model=list[RFIResponse])
def list_all_rfis(
    status: str = None,
    severity: str = None,
    project_id: int = None,
    db: Session = Depends(get_db),
):
    """List all RFIs across all submittals, with optional filters."""
    query = db.query(RFI)
    if status:
        query = query.filter(RFI.status == status)
    if severity:
        query = query.filter(RFI.severity == severity)
    if project_id:
        query = query.join(Submittal).filter(Submittal.project_id == project_id)
    return query.order_by(RFI.created_at.desc()).all()


@router.post("/{submittal_id}/create", response_model=RFIResponse)
def create_rfi(submittal_id: int, rfi_data: RFICreate, db: Session = Depends(get_db)):
    """Create an RFI from review comments. Auto-populates body from open critical/major comments
    if no body is provided."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise HTTPException(status_code=404, detail="Submittal not found")

    rfi_number = _next_rfi_number(db, submittal_id)

    # If related_comment_ids provided, use those; otherwise grab all open critical/major
    comment_ids = []
    if rfi_data.related_comment_ids:
        try:
            comment_ids = json.loads(rfi_data.related_comment_ids)
        except (json.JSONDecodeError, TypeError):
            comment_ids = []

    if comment_ids:
        comments = (
            db.query(ReviewComment)
            .filter(ReviewComment.id.in_(comment_ids), ReviewComment.submittal_id == submittal_id)
            .order_by(ReviewComment.page_number, ReviewComment.id)
            .all()
        )
    else:
        comments = (
            db.query(ReviewComment)
            .filter(
                ReviewComment.submittal_id == submittal_id,
                ReviewComment.status == "open",
                ReviewComment.severity.in_(["critical", "major"]),
            )
            .order_by(ReviewComment.page_number, ReviewComment.id)
            .all()
        )
        comment_ids = [c.id for c in comments]

    # Auto-generate body from comments if not provided
    body = rfi_data.body
    if not body and comments:
        body = _build_rfi_body(comments)

    # Auto-generate subject if not provided
    subject = rfi_data.subject
    if not subject:
        subject = f"{rfi_number}: {submittal.title} — Request for Information"

    rfi = RFI(
        submittal_id=submittal_id,
        rfi_number=rfi_number,
        subject=subject,
        body=body,
        status="draft",
        severity=rfi_data.severity or "major",
        recipients=rfi_data.recipients,
        due_date=rfi_data.due_date,
        related_comment_ids=json.dumps(comment_ids),
    )
    db.add(rfi)
    db.commit()
    db.refresh(rfi)
    return rfi


@router.get("/{submittal_id}", response_model=list[RFIResponse])
def list_rfis(
    submittal_id: int,
    status: str = None,
    db: Session = Depends(get_db),
):
    """List all RFIs for a submittal, optionally filtered by status."""
    query = db.query(RFI).filter(RFI.submittal_id == submittal_id)
    if status:
        query = query.filter(RFI.status == status)
    return query.order_by(RFI.created_at.desc()).all()


@router.patch("/{rfi_id}/status", response_model=RFIResponse)
def update_rfi_status(rfi_id: int, update: RFIStatusUpdate, db: Session = Depends(get_db)):
    """Update RFI status (draft -> sent -> responded -> closed)."""
    rfi = db.query(RFI).filter(RFI.id == rfi_id).first()
    if not rfi:
        raise HTTPException(status_code=404, detail="RFI not found")

    valid_statuses = {"draft", "sent", "responded", "closed"}
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{update.status}'. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    rfi.status = update.status

    now = datetime.now(timezone.utc)
    if update.status == "sent" and not rfi.sent_at:
        rfi.sent_at = now
    elif update.status == "closed" and not rfi.closed_at:
        rfi.closed_at = now

    db.commit()
    db.refresh(rfi)
    return rfi


@router.patch("/{rfi_id}/response", response_model=RFIResponse)
def log_rfi_response(rfi_id: int, update: RFIResponseUpdate, db: Session = Depends(get_db)):
    """Log the vendor's response to an RFI."""
    rfi = db.query(RFI).filter(RFI.id == rfi_id).first()
    if not rfi:
        raise HTTPException(status_code=404, detail="RFI not found")

    rfi.response_text = update.response_text
    rfi.response_received_at = datetime.now(timezone.utc)
    rfi.status = "responded"

    db.commit()
    db.refresh(rfi)
    return rfi
