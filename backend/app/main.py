from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import projects, submittals, reviews, comments, emails, register, rfis


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
app.include_router(register.router)
app.include_router(rfis.router)


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
        from app.models.database_models import RFI, SubmittalRegisterItem

        total_projects = db.query(func.count(Project.id)).scalar()
        total_submittals = db.query(func.count(Submittal.id)).scalar()
        pending = db.query(func.count(Submittal.id)).filter(Submittal.status.in_(["uploaded", "reviewing"])).scalar()
        reviewed = db.query(func.count(Submittal.id)).filter(Submittal.status == "reviewed").scalar()
        approved = db.query(func.count(Submittal.id)).filter(Submittal.status == "approved").scalar()

        open_comments = db.query(func.count(ReviewComment.id)).filter(ReviewComment.status == "open").scalar()
        critical = db.query(func.count(ReviewComment.id)).filter(
            ReviewComment.status == "open", ReviewComment.severity == "critical"
        ).scalar()
        major = db.query(func.count(ReviewComment.id)).filter(
            ReviewComment.status == "open", ReviewComment.severity == "major"
        ).scalar()
        resolved = db.query(func.count(ReviewComment.id)).filter(ReviewComment.status == "resolved").scalar()

        # RFI stats
        total_rfis = db.query(func.count(RFI.id)).scalar()
        open_rfis = db.query(func.count(RFI.id)).filter(RFI.status.in_(["draft", "sent"])).scalar()
        awaiting_response = db.query(func.count(RFI.id)).filter(RFI.status == "sent").scalar()

        # Submittal register stats
        register_total = db.query(func.count(SubmittalRegisterItem.id)).scalar()
        register_not_submitted = db.query(func.count(SubmittalRegisterItem.id)).filter(
            SubmittalRegisterItem.status == "not_submitted"
        ).scalar()

        # Status breakdown
        statuses = db.query(Submittal.status, func.count(Submittal.id)).group_by(Submittal.status).all()
        status_dict = {s: c for s, c in statuses}

        # Severity breakdown of open comments
        severities = db.query(ReviewComment.severity, func.count(ReviewComment.id)).filter(
            ReviewComment.status == "open"
        ).group_by(ReviewComment.severity).all()
        severity_dict = {s: c for s, c in severities}

        # Equipment type breakdown
        eq_types = db.query(Submittal.equipment_type, func.count(Submittal.id)).group_by(
            Submittal.equipment_type
        ).all()
        eq_type_dict = {t: c for t, c in eq_types}

        # Recent submittals
        recent = db.query(Submittal).order_by(Submittal.created_at.desc()).limit(10).all()
        recent_list = [
            {
                "id": s.id, "title": s.title, "equipment_type": s.equipment_type,
                "status": s.status, "created_at": s.created_at.isoformat() if s.created_at else None,
                "manufacturer": s.manufacturer, "page_count": s.page_count,
            }
            for s in recent
        ]

        return {
            "total_projects": total_projects,
            "total_submittals": total_submittals,
            "pending_review": pending,
            "reviewed": reviewed,
            "approved": approved,
            "open_comments": open_comments,
            "critical_issues": critical,
            "major_issues": major,
            "resolved_comments": resolved,
            "total_rfis": total_rfis,
            "open_rfis": open_rfis,
            "awaiting_response": awaiting_response,
            "register_total": register_total,
            "register_not_submitted": register_not_submitted,
            "submittals_by_status": status_dict,
            "comments_by_severity": severity_dict,
            "submittals_by_equipment_type": eq_type_dict,
            "recent_submittals": recent_list,
        }
    finally:
        db.close()
