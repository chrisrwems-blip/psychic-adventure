from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import sys


def get_data_dir():
    """Return a writable directory for app data (DB, uploads, reports).

    In production (frozen exe), this is AppData/ArcLight.
    In development, this is the backend/ directory (cwd).
    """
    if getattr(sys, "frozen", False):
        app_data = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ArcLight")
        os.makedirs(app_data, exist_ok=True)
        return app_data
    return "."


def _default_db_url():
    """Use a writable location for the database in production (frozen exe)."""
    db_path = os.path.join(get_data_dir(), "submittal_review.db")
    return f"sqlite:///{db_path}"


DATABASE_URL = os.getenv("DATABASE_URL", _default_db_url())

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import database_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
