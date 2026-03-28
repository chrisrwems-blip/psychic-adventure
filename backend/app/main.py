from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import projects, submittals, reviews, comments, emails


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="DataCenter Submittal Review Platform",
    description="Automated submittal review for modular data center electrical systems",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(submittals.router)
app.include_router(reviews.router)
app.include_router(comments.router)
app.include_router(emails.router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "DataCenter Submittal Review Platform"}


@app.get("/api/dashboard")
def dashboard():
    from sqlalchemy import func
    from app.database import SessionLocal
    from app.models.database_models import Project, Submittal, ReviewComment

    db = SessionLocal()
    try:
        total_projects = db.query(func.count(Project.id)).scalar()
        total_submittals = db.query(func.count(Submittal.id)).scalar()
        pending = db.query(func.count(Submittal.id)).filter(Submittal.status.in_(["uploaded", "reviewing"])).scalar()
        open_comments = db.query(func.count(ReviewComment.id)).filter(ReviewComment.status == "open").scalar()
        critical = db.query(func.count(ReviewComment.id)).filter(
            ReviewComment.status == "open", ReviewComment.severity == "critical"
        ).scalar()

        # Status breakdown
        statuses = db.query(Submittal.status, func.count(Submittal.id)).group_by(Submittal.status).all()
        status_dict = {s: c for s, c in statuses}

        # Recent submittals
        recent = db.query(Submittal).order_by(Submittal.created_at.desc()).limit(10).all()
        recent_list = [
            {"id": s.id, "title": s.title, "equipment_type": s.equipment_type, "status": s.status}
            for s in recent
        ]

        return {
            "total_projects": total_projects,
            "total_submittals": total_submittals,
            "pending_review": pending,
            "open_comments": open_comments,
            "critical_issues": critical,
            "submittals_by_status": status_dict,
            "recent_submittals": recent_list,
        }
    finally:
        db.close()
