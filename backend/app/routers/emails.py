from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import GeneratedEmail
from app.models.schemas import EmailGenerate, EmailResponse
from app.services.email_generator import generate_email

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.post("/{submittal_id}/generate", response_model=EmailResponse)
def create_email(submittal_id: int, request: EmailGenerate, db: Session = Depends(get_db)):
    """Generate an email (RFI, clarification, rejection, or approval) for a submittal."""
    try:
        email = generate_email(
            db=db,
            submittal_id=submittal_id,
            email_type=request.email_type,
            recipients=request.recipients or "",
            additional_notes=request.additional_notes or "",
        )
        return email
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/submittal/{submittal_id}", response_model=list[EmailResponse])
def list_emails(submittal_id: int, db: Session = Depends(get_db)):
    """List all generated emails for a submittal."""
    return (
        db.query(GeneratedEmail)
        .filter(GeneratedEmail.submittal_id == submittal_id)
        .order_by(GeneratedEmail.created_at.desc())
        .all()
    )


@router.get("/{email_id}", response_model=EmailResponse)
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(GeneratedEmail).filter(GeneratedEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@router.patch("/{email_id}/mark-sent")
def mark_email_sent(email_id: int, db: Session = Depends(get_db)):
    email = db.query(GeneratedEmail).filter(GeneratedEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    email.sent = 1
    db.commit()
    return {"detail": "Email marked as sent"}
