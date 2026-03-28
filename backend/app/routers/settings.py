from fastapi import APIRouter
from pydantic import BaseModel

from app.services.smtp_service import (
    detect_smtp_settings,
    save_settings,
    load_settings,
    delete_settings,
    test_connection,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class EmailSettingsRequest(BaseModel):
    email: str
    password: str
    host: str
    port: int = 587
    display_name: str = ""


class DetectRequest(BaseModel):
    email: str


@router.post("/email/detect")
def detect_provider(request: DetectRequest):
    """Auto-detect SMTP settings from email address."""
    return detect_smtp_settings(request.email)


@router.post("/email/save")
def save_email_settings(request: EmailSettingsRequest):
    """Save SMTP email settings."""
    return save_settings(
        email=request.email,
        password=request.password,
        host=request.host,
        port=request.port,
        display_name=request.display_name,
    )


@router.get("/email")
def get_email_settings():
    """Get saved email settings (password masked)."""
    settings = load_settings()
    if not settings:
        return {"configured": False}
    return {
        "configured": True,
        "email": settings["email"],
        "host": settings["host"],
        "port": settings["port"],
        "display_name": settings.get("display_name", ""),
    }


@router.delete("/email")
def remove_email_settings():
    """Remove saved email settings."""
    delete_settings()
    return {"status": "removed"}


@router.post("/email/test")
def test_email_connection(request: EmailSettingsRequest):
    """Test SMTP connection with provided credentials."""
    return test_connection(
        email=request.email,
        password=request.password,
        host=request.host,
        port=request.port,
    )
