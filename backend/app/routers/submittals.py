import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.database_models import Submittal, ReviewComment
from app.models.schemas import SubmittalResponse
from app.services.pdf_parser import get_page_count

router = APIRouter(prefix="/api/submittals", tags=["submittals"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


@router.get("/", response_model=list[SubmittalResponse])
def list_submittals(project_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Submittal)
    if project_id:
        query = query.filter(Submittal.project_id == project_id)
    submittals = query.order_by(Submittal.created_at.desc()).all()

    result = []
    for s in submittals:
        total_comments = db.query(func.count(ReviewComment.id)).filter(ReviewComment.submittal_id == s.id).scalar()
        open_comments = db.query(func.count(ReviewComment.id)).filter(
            ReviewComment.submittal_id == s.id, ReviewComment.status == "open"
        ).scalar()
        resp = SubmittalResponse(
            id=s.id, project_id=s.project_id, title=s.title,
            submittal_number=s.submittal_number, equipment_type=s.equipment_type,
            manufacturer=s.manufacturer, model_number=s.model_number,
            spec_section=s.spec_section, status=s.status,
            file_path=s.file_path, annotated_file_path=s.annotated_file_path,
            file_size=s.file_size, page_count=s.page_count,
            submitted_by=s.submitted_by, contractor=s.contractor,
            created_at=s.created_at, reviewed_at=s.reviewed_at,
            comment_count=total_comments, open_comments=open_comments,
        )
        result.append(resp)
    return result


@router.post("/upload", response_model=SubmittalResponse)
async def upload_submittal(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    title: str = Form(...),
    equipment_type: str = Form("auto"),
    submittal_number: str = Form(None),
    manufacturer: str = Form(None),
    model_number: str = Form(None),
    spec_section: str = Form(None),
    submitted_by: str = Form(None),
    contractor: str = Form(None),
    db: Session = Depends(get_db),
):
    # Save file
    project_dir = os.path.join(UPLOAD_DIR, str(project_id))
    os.makedirs(project_dir, exist_ok=True)

    file_path = os.path.join(project_dir, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)
    page_count = get_page_count(file_path)

    submittal = Submittal(
        project_id=project_id,
        title=title,
        submittal_number=submittal_number,
        equipment_type=equipment_type,
        manufacturer=manufacturer,
        model_number=model_number,
        spec_section=spec_section,
        submitted_by=submitted_by,
        contractor=contractor,
        file_path=file_path,
        file_size=file_size,
        page_count=page_count,
    )
    db.add(submittal)
    db.commit()
    db.refresh(submittal)

    return SubmittalResponse(
        id=submittal.id, project_id=submittal.project_id, title=submittal.title,
        submittal_number=submittal.submittal_number, equipment_type=submittal.equipment_type,
        manufacturer=submittal.manufacturer, model_number=submittal.model_number,
        spec_section=submittal.spec_section, status=submittal.status,
        file_path=submittal.file_path, annotated_file_path=submittal.annotated_file_path,
        file_size=submittal.file_size, page_count=submittal.page_count,
        submitted_by=submittal.submitted_by, contractor=submittal.contractor,
        created_at=submittal.created_at, reviewed_at=submittal.reviewed_at,
        comment_count=0, open_comments=0,
    )


@router.get("/{submittal_id}", response_model=SubmittalResponse)
def get_submittal(submittal_id: int, db: Session = Depends(get_db)):
    s = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submittal not found")
    total_comments = db.query(func.count(ReviewComment.id)).filter(ReviewComment.submittal_id == s.id).scalar()
    open_comments = db.query(func.count(ReviewComment.id)).filter(
        ReviewComment.submittal_id == s.id, ReviewComment.status == "open"
    ).scalar()
    return SubmittalResponse(
        id=s.id, project_id=s.project_id, title=s.title,
        submittal_number=s.submittal_number, equipment_type=s.equipment_type,
        manufacturer=s.manufacturer, model_number=s.model_number,
        spec_section=s.spec_section, status=s.status,
        file_path=s.file_path, annotated_file_path=s.annotated_file_path,
        file_size=s.file_size, page_count=s.page_count,
        submitted_by=s.submitted_by, contractor=s.contractor,
        created_at=s.created_at, reviewed_at=s.reviewed_at,
        comment_count=total_comments, open_comments=open_comments,
    )


@router.get("/{submittal_id}/pdf")
def serve_pdf(submittal_id: int, db: Session = Depends(get_db)):
    s = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submittal not found")
    if not os.path.exists(s.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(s.file_path, media_type="application/pdf")


@router.post("/{submittal_id}/annotate")
def annotate_submittal(submittal_id: int, db: Session = Depends(get_db)):
    """Generate an annotated/marked-up PDF with all review comments."""
    from app.services.pdf_annotator import annotate_pdf
    try:
        annotated_path, summary_pages = annotate_pdf(db, submittal_id)
        return {
            "annotated_file_path": annotated_path,
            "summary_page_count": summary_pages,
            "detail": "Annotated PDF created",
        }
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{submittal_id}/annotated-pdf")
def serve_annotated_pdf(submittal_id: int, download: bool = False, db: Session = Depends(get_db)):
    """Serve the annotated/marked-up PDF. ?download=true forces download."""
    s = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submittal not found")
    if not s.annotated_file_path or not os.path.exists(s.annotated_file_path):
        raise HTTPException(status_code=404, detail="Annotated PDF not yet generated. Run /annotate first.")
    if download:
        return FileResponse(s.annotated_file_path, media_type="application/pdf",
                            filename=os.path.basename(s.annotated_file_path))
    return FileResponse(s.annotated_file_path, media_type="application/pdf")


@router.post("/{submittal_id}/stamp")
def stamp_submittal(
    submittal_id: int,
    disposition: str = Form("approved_as_noted"),
    reviewer_name: str = Form("Engineer of Record"),
    db: Session = Depends(get_db),
):
    """Apply a review disposition stamp to the submittal PDF."""
    from app.services.approval_stamp import apply_stamp
    try:
        stamped_path = apply_stamp(db, submittal_id, disposition, reviewer_name)
        return FileResponse(stamped_path, media_type="application/pdf",
                            filename=os.path.basename(stamped_path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{submittal_id}")
def delete_submittal(submittal_id: int, db: Session = Depends(get_db)):
    s = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Submittal not found")
    if os.path.exists(s.file_path):
        os.remove(s.file_path)
    db.delete(s)
    db.commit()
    return {"detail": "Submittal deleted"}
