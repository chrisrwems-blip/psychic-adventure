from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.database_models import Project, Submittal
from app.models.schemas import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    result = []
    for p in projects:
        count = db.query(func.count(Submittal.id)).filter(Submittal.project_id == p.id).scalar()
        resp = ProjectResponse(
            id=p.id, name=p.name, description=p.description,
            client=p.client, location=p.location, tier_level=p.tier_level,
            created_at=p.created_at, submittal_count=count,
        )
        result.append(resp)
    return result


@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return ProjectResponse(
        id=db_project.id, name=db_project.name, description=db_project.description,
        client=db_project.client, location=db_project.location, tier_level=db_project.tier_level,
        created_at=db_project.created_at, submittal_count=0,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    count = db.query(func.count(Submittal.id)).filter(Submittal.project_id == project.id).scalar()
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description,
        client=project.client, location=project.location, tier_level=project.tier_level,
        created_at=project.created_at, submittal_count=count,
    )


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"detail": "Project deleted"}
