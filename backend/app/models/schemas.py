from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    client: Optional[str]
    location: Optional[str]
    tier_level: Optional[str]
    created_at: datetime
    submittal_count: Optional[int] = 0


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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

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


# --- Review Result Schemas ---
class ReviewResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submittal_id: int
    check_name: str
    check_category: Optional[str]
    passed: int
    details: Optional[str]
    reference_standard: Optional[str]


# --- Email Schemas ---
class EmailGenerate(BaseModel):
    email_type: str = "clarification"
    recipients: Optional[str] = None
    additional_notes: Optional[str] = None


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submittal_id: int
    email_type: str
    subject: str
    body: str
    recipients: Optional[str]
    sent: int
    created_at: datetime


# --- RFI Schemas ---
class RFICreate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    severity: Optional[str] = "major"
    recipients: Optional[str] = None
    due_date: Optional[datetime] = None
    related_comment_ids: Optional[str] = None  # JSON list of comment IDs


class RFIStatusUpdate(BaseModel):
    status: str  # draft, sent, responded, closed


class RFIResponseUpdate(BaseModel):
    response_text: str


class RFIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submittal_id: int
    rfi_number: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    status: str
    severity: Optional[str]
    recipients: Optional[str]
    due_date: Optional[datetime]
    sent_at: Optional[datetime]
    response_received_at: Optional[datetime]
    response_text: Optional[str]
    related_comment_ids: Optional[str]
    created_at: datetime
    closed_at: Optional[datetime]


# --- Submittal Register Schemas ---
class RegisterItemCreate(BaseModel):
    spec_section: Optional[str] = None
    description: str
    required: Optional[int] = 1
    submittal_id: Optional[int] = None
    status: Optional[str] = "not_submitted"
    priority: Optional[str] = "normal"
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class RegisterItemUpdate(BaseModel):
    spec_section: Optional[str] = None
    description: Optional[str] = None
    required: Optional[int] = None
    submittal_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class RegisterItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    spec_section: Optional[str]
    description: Optional[str]
    required: int
    submittal_id: Optional[int]
    status: str
    priority: str
    notes: Optional[str]
    due_date: Optional[datetime]
    created_at: datetime


class RegisterSummary(BaseModel):
    total: int
    not_submitted: int
    under_review: int
    approved: int
    rejected: int
    resubmit_required: int


# --- Dashboard ---
class DashboardStats(BaseModel):
    total_projects: int
    total_submittals: int
    pending_review: int
    open_comments: int
    critical_issues: int
    submittals_by_status: dict
    recent_submittals: list
