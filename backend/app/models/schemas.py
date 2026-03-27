from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# --- Project Schemas ---
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    client: Optional[str] = None
    location: Optional[str] = None
    tier_level: Optional[str] = "III"


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    client: Optional[str]
    location: Optional[str]
    tier_level: Optional[str]
    created_at: datetime
    submittal_count: Optional[int] = 0

    class Config:
        from_attributes = True


# --- Submittal Schemas ---
class SubmittalCreate(BaseModel):
    project_id: int
    title: str
    submittal_number: Optional[str] = None
    equipment_type: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    spec_section: Optional[str] = None
    submitted_by: Optional[str] = None
    contractor: Optional[str] = None


class SubmittalResponse(BaseModel):
    id: int
    project_id: int
    title: str
    submittal_number: Optional[str]
    equipment_type: str
    manufacturer: Optional[str]
    model_number: Optional[str]
    spec_section: Optional[str]
    status: str
    file_path: str
    annotated_file_path: Optional[str]
    file_size: Optional[int]
    page_count: Optional[int]
    submitted_by: Optional[str]
    contractor: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    comment_count: Optional[int] = 0
    open_comments: Optional[int] = 0

    class Config:
        from_attributes = True


# --- Comment Schemas ---
class CommentCreate(BaseModel):
    page_number: Optional[int] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    comment_text: str
    category: Optional[str] = None
    severity: Optional[str] = "info"
    assigned_to: Optional[str] = None
    reference_code: Optional[str] = None


class CommentUpdate(BaseModel):
    comment_text: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class CommentResponse(BaseModel):
    id: int
    submittal_id: int
    page_number: Optional[int]
    x_position: Optional[float]
    y_position: Optional[float]
    comment_text: str
    category: Optional[str]
    severity: str
    status: str
    assigned_to: Optional[str]
    reference_code: Optional[str]
    resolution_notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Review Result Schemas ---
class ReviewResultResponse(BaseModel):
    id: int
    submittal_id: int
    check_name: str
    check_category: Optional[str]
    passed: int
    details: Optional[str]
    reference_standard: Optional[str]

    class Config:
        from_attributes = True


# --- Email Schemas ---
class EmailGenerate(BaseModel):
    email_type: str = "clarification"
    recipients: Optional[str] = None
    additional_notes: Optional[str] = None


class EmailResponse(BaseModel):
    id: int
    submittal_id: int
    email_type: str
    subject: str
    body: str
    recipients: Optional[str]
    sent: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Dashboard ---
class DashboardStats(BaseModel):
    total_projects: int
    total_submittals: int
    pending_review: int
    open_comments: int
    critical_issues: int
    submittals_by_status: dict
    recent_submittals: list
