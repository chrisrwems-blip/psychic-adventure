from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.database_models import SubmittalRegisterItem, Project
from app.models.schemas import (
    RegisterItemCreate,
    RegisterItemUpdate,
    RegisterItemResponse,
    RegisterSummary,
)

router = APIRouter(prefix="/api/register", tags=["register"])


@router.get("/{project_id}", response_model=list[RegisterItemResponse])
def list_register_items(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    items = (
        db.query(SubmittalRegisterItem)
        .filter(SubmittalRegisterItem.project_id == project_id)
        .order_by(SubmittalRegisterItem.created_at.desc())
        .all()
    )
    return items


@router.post("/{project_id}", response_model=RegisterItemResponse)
def create_register_item(
    project_id: int, item: RegisterItemCreate, db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db_item = SubmittalRegisterItem(project_id=project_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.patch("/{item_id}", response_model=RegisterItemResponse)
def update_register_item(
    item_id: int, update: RegisterItemUpdate, db: Session = Depends(get_db)
):
    db_item = (
        db.query(SubmittalRegisterItem)
        .filter(SubmittalRegisterItem.id == item_id)
        .first()
    )
    if not db_item:
        raise HTTPException(status_code=404, detail="Register item not found")
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{item_id}")
def delete_register_item(item_id: int, db: Session = Depends(get_db)):
    db_item = (
        db.query(SubmittalRegisterItem)
        .filter(SubmittalRegisterItem.id == item_id)
        .first()
    )
    if not db_item:
        raise HTTPException(status_code=404, detail="Register item not found")
    db.delete(db_item)
    db.commit()
    return {"detail": "Register item deleted"}


@router.get("/{project_id}/summary", response_model=RegisterSummary)
def register_summary(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    counts = (
        db.query(SubmittalRegisterItem.status, func.count(SubmittalRegisterItem.id))
        .filter(SubmittalRegisterItem.project_id == project_id)
        .group_by(SubmittalRegisterItem.status)
        .all()
    )
    status_map = {s: c for s, c in counts}
    total = sum(status_map.values())
    return RegisterSummary(
        total=total,
        not_submitted=status_map.get("not_submitted", 0),
        under_review=status_map.get("under_review", 0),
        approved=status_map.get("approved", 0),
        rejected=status_map.get("rejected", 0),
        resubmit_required=status_map.get("resubmit_required", 0),
    )
