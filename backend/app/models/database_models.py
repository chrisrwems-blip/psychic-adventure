from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


class SubmittalStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    REVIEWING = "reviewing"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISE_RESUBMIT = "revise_resubmit"


class CommentStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


class CommentSeverity(str, enum.Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class EquipmentType(str, enum.Enum):
    SWITCHGEAR = "switchgear"
    UPS = "ups"
    PDU = "pdu"
    GENERATOR = "generator"
    TRANSFORMER = "transformer"
    ATS = "ats"
    CABLE = "cable"
    BUS_DUCT = "bus_duct"
    PANELBOARD = "panelboard"
    RPP = "rpp"
    STS = "sts"
    BATTERY = "battery"
    COOLING = "cooling"
    BUSWAY = "busway"
    OTHER = "other"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    client = Column(String(255))
    location = Column(String(255))
    tier_level = Column(String(10))  # Tier I, II, III, IV
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    submittals = relationship("Submittal", back_populates="project", cascade="all, delete-orphan")


class Submittal(Base):
    __tablename__ = "submittals"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    submittal_number = Column(String(50))
    equipment_type = Column(String(50), nullable=False)
    manufacturer = Column(String(255))
    model_number = Column(String(255))
    spec_section = Column(String(50))
    status = Column(String(30), default=SubmittalStatus.UPLOADED)
    file_path = Column(String(500), nullable=False)
    annotated_file_path = Column(String(500))
    file_size = Column(Integer)
    page_count = Column(Integer)
    submitted_by = Column(String(255))
    contractor = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime)

    project = relationship("Project", back_populates="submittals")
    comments = relationship("ReviewComment", back_populates="submittal", cascade="all, delete-orphan")
    review_results = relationship("ReviewResult", back_populates="submittal", cascade="all, delete-orphan")
    emails = relationship("GeneratedEmail", back_populates="submittal", cascade="all, delete-orphan")


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)
    submittal_id = Column(Integer, ForeignKey("submittals.id"), nullable=False)
    page_number = Column(Integer)
    x_position = Column(Float)
    y_position = Column(Float)
    comment_text = Column(Text, nullable=False)
    category = Column(String(100))
    severity = Column(String(20), default=CommentSeverity.INFO)
    status = Column(String(20), default=CommentStatus.OPEN)
    assigned_to = Column(String(255))
    reference_code = Column(String(100))  # NEC, NFPA, IEEE reference
    resolution_notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime)

    submittal = relationship("Submittal", back_populates="comments")


class ReviewResult(Base):
    __tablename__ = "review_results"

    id = Column(Integer, primary_key=True, index=True)
    submittal_id = Column(Integer, ForeignKey("submittals.id"), nullable=False)
    check_name = Column(String(255), nullable=False)
    check_category = Column(String(100))
    passed = Column(Integer)  # 1=pass, 0=fail, -1=needs_review
    details = Column(Text)
    reference_standard = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    submittal = relationship("Submittal", back_populates="review_results")


class GeneratedEmail(Base):
    __tablename__ = "generated_emails"

    id = Column(Integer, primary_key=True, index=True)
    submittal_id = Column(Integer, ForeignKey("submittals.id"), nullable=False)
    email_type = Column(String(50))  # rfi, clarification, rejection, approval
    subject = Column(String(500))
    body = Column(Text)
    recipients = Column(Text)  # JSON list
    sent = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    submittal = relationship("Submittal", back_populates="emails")


class RFI(Base):
    __tablename__ = "rfis"

    id = Column(Integer, primary_key=True, index=True)
    submittal_id = Column(Integer, ForeignKey("submittals.id"), nullable=False)
    rfi_number = Column(String(50))  # Auto-generated: RFI-001, RFI-002
    subject = Column(String(500))
    body = Column(Text)
    status = Column(String(30), default="draft")  # draft, sent, responded, closed
    severity = Column(String(20), default="major")
    recipients = Column(Text)
    due_date = Column(DateTime)
    sent_at = Column(DateTime)
    response_received_at = Column(DateTime)
    response_text = Column(Text)
    related_comment_ids = Column(Text)  # JSON list of comment IDs
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime)

    submittal = relationship("Submittal", backref="rfis")


class SubmittalRegisterItem(Base):
    __tablename__ = "submittal_register"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    spec_section = Column(String(50))  # e.g., "26 24 16"
    description = Column(String(500))  # e.g., "Medium Voltage Switchgear"
    required = Column(Integer, default=1)  # 1=required, 0=optional
    submittal_id = Column(Integer, ForeignKey("submittals.id"), nullable=True)  # linked submittal
    status = Column(String(30), default="not_submitted")  # not_submitted, under_review, approved, rejected, resubmit_required
    priority = Column(String(20), default="normal")  # critical, high, normal, low
    notes = Column(Text)
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project")
    submittal = relationship("Submittal")
