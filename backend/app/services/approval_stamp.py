"""Approval stamp service — adds professional review stamps to PDFs.

Stamps include:
- APPROVED / APPROVED AS NOTED / REVISE & RESUBMIT / REJECTED
- Reviewer name, date, project info
- Stamp appears on the first page and optionally on every page
"""
import os
from io import BytesIO
from datetime import datetime, timezone
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, Project


STAMP_COLORS = {
    "approved": Color(0.1, 0.6, 0.2),           # Green
    "approved_as_noted": Color(0.2, 0.4, 0.8),   # Blue
    "revise_resubmit": Color(0.85, 0.5, 0.0),    # Orange
    "rejected": Color(0.8, 0.1, 0.1),             # Red
}

STAMP_LABELS = {
    "approved": "APPROVED",
    "approved_as_noted": "APPROVED AS NOTED",
    "revise_resubmit": "REVISE AND RESUBMIT",
    "rejected": "REJECTED",
}


def apply_stamp(
    db: Session,
    submittal_id: int,
    disposition: str,
    reviewer_name: str = "Engineer of Record",
    stamp_all_pages: bool = False,
) -> str:
    """Apply a review stamp to the submittal PDF.

    Args:
        disposition: "approved", "approved_as_noted", "revise_resubmit", "rejected"
        reviewer_name: Name to appear on stamp
        stamp_all_pages: If True, stamp every page. If False, only first page.

    Returns: path to the stamped PDF
    """
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise ValueError(f"Submittal {submittal_id} not found")

    project = db.query(Project).filter(Project.id == submittal.project_id).first()

    # Use annotated PDF if available, otherwise original
    source_path = submittal.annotated_file_path or submittal.file_path
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"PDF not found: {source_path}")

    reader = PdfReader(source_path)
    writer = PdfWriter()

    color = STAMP_COLORS.get(disposition, STAMP_COLORS["approved_as_noted"])
    label = STAMP_LABELS.get(disposition, disposition.upper())
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    project_name = project.name if project else "N/A"

    for i, page in enumerate(reader.pages):
        if i == 0 or stamp_all_pages:
            media_box = page.mediabox
            pw = float(media_box.width)
            ph = float(media_box.height)

            stamp_overlay = _create_stamp_overlay(
                pw, ph, label, reviewer_name, date_str,
                project_name, submittal.title, color
            )
            stamp_reader = PdfReader(stamp_overlay)
            if stamp_reader.pages:
                page.merge_page(stamp_reader.pages[0])

        writer.add_page(page)

    # Save stamped PDF
    stamped_dir = os.path.join(os.path.dirname(submittal.file_path), "stamped")
    os.makedirs(stamped_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(submittal.file_path))[0]
    stamped_path = os.path.join(stamped_dir, f"{base_name}_STAMPED.pdf")

    with open(stamped_path, "wb") as f:
        writer.write(f)

    # Update submittal status
    status_map = {
        "approved": "approved",
        "approved_as_noted": "approved",
        "revise_resubmit": "revise_resubmit",
        "rejected": "rejected",
    }
    submittal.status = status_map.get(disposition, submittal.status)
    db.commit()

    return stamped_path


def _create_stamp_overlay(
    page_width: float, page_height: float,
    label: str, reviewer: str, date: str,
    project: str, submittal_title: str,
    color: Color,
) -> BytesIO:
    """Create a transparent overlay with the review stamp."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    # Position stamp in upper-right corner
    stamp_w = 220
    stamp_h = 100
    x = page_width - stamp_w - 20
    y = page_height - stamp_h - 20

    # Outer border (double line)
    c.setStrokeColor(color)
    c.setLineWidth(3)
    c.rect(x, y, stamp_w, stamp_h, fill=False, stroke=True)
    c.setLineWidth(1)
    c.rect(x + 4, y + 4, stamp_w - 8, stamp_h - 8, fill=False, stroke=True)

    # Semi-transparent background
    bg = Color(color.red, color.green, color.blue, alpha=0.08)
    c.setFillColor(bg)
    c.rect(x + 4, y + 4, stamp_w - 8, stamp_h - 8, fill=True, stroke=False)

    # Disposition label (big text)
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 12 if len(label) < 15 else 9)
    c.drawCentredString(x + stamp_w / 2, y + stamp_h - 25, label)

    # Divider line
    c.setStrokeColor(color)
    c.setLineWidth(0.5)
    c.line(x + 15, y + stamp_h - 32, x + stamp_w - 15, y + stamp_h - 32)

    # Details
    c.setFillColor(Color(0.2, 0.2, 0.2))
    c.setFont("Helvetica", 7)
    c.drawString(x + 12, y + stamp_h - 45, f"Reviewer: {reviewer}")
    c.drawString(x + 12, y + stamp_h - 57, f"Date: {date}")
    c.drawString(x + 12, y + stamp_h - 69, f"Project: {project[:30]}")
    c.drawString(x + 12, y + stamp_h - 81, f"Submittal: {submittal_title[:30]}")

    # Diagonal watermark text (subtle)
    c.saveState()
    c.setFillColor(Color(color.red, color.green, color.blue, alpha=0.04))
    c.setFont("Helvetica-Bold", 72)
    c.translate(page_width / 2, page_height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, label)
    c.restoreState()

    c.save()
    buffer.seek(0)
    return buffer
