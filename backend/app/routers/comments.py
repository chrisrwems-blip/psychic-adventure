from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import ReviewComment
from app.models.schemas import CommentCreate, CommentUpdate, CommentResponse

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.get("/submittal/{submittal_id}", response_model=list[CommentResponse])
def list_comments(
    submittal_id: int,
    status: str = None,
    severity: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(ReviewComment).filter(ReviewComment.submittal_id == submittal_id)
    if status:
        query = query.filter(ReviewComment.status == status)
    if severity:
        query = query.filter(ReviewComment.severity == severity)
    return query.order_by(ReviewComment.created_at.desc()).all()


@router.get("/all", response_model=list[CommentResponse])
def list_all_comments(
    status: str = None,
    severity: str = None,
    project_id: int = None,
    db: Session = Depends(get_db),
):
    """List all comments across submittals, with optional filters."""
    query = db.query(ReviewComment)
    if status:
        query = query.filter(ReviewComment.status == status)
    if severity:
        query = query.filter(ReviewComment.severity == severity)
    if project_id:
        from app.models.database_models import Submittal
        query = query.join(Submittal).filter(Submittal.project_id == project_id)
    return query.order_by(ReviewComment.created_at.desc()).all()


@router.post("/submittal/{submittal_id}", response_model=CommentResponse)
def add_comment(submittal_id: int, comment: CommentCreate, db: Session = Depends(get_db)):
    db_comment = ReviewComment(submittal_id=submittal_id, **comment.model_dump())
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


@router.patch("/{comment_id}", response_model=CommentResponse)
def update_comment(comment_id: int, update: CommentUpdate, db: Session = Depends(get_db)):
    comment = db.query(ReviewComment).filter(ReviewComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(comment, key, value)

    if update.status == "resolved" and not comment.resolved_at:
        comment.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(ReviewComment).filter(ReviewComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    db.delete(comment)
    db.commit()
    return {"detail": "Comment deleted"}
