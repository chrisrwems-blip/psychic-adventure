"""PDF annotation service - creates real visible PDF annotations with appearance streams."""
import math
import os
from io import BytesIO
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import (
    ArrayObject, ContentStream, DecodedStreamObject, DictionaryObject,
    EncodedStreamObject, FloatObject, NameObject, NumberObject,
    TextStringObject, RectangleObject, StreamObject,
)
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, ReviewComment


def annotate_pdf(db: Session, submittal_id: int) -> str:
    """Create an annotated copy of a submittal PDF with visible callout annotations."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise ValueError(f"Submittal {submittal_id} not found")

    if not os.path.exists(submittal.file_path):
        raise FileNotFoundError(f"PDF file not found: {submittal.file_path}")

    comments = (
        db.query(ReviewComment)
        .filter(ReviewComment.submittal_id == submittal_id)
        .order_by(ReviewComment.id)
        .all()
    )

    reader = PdfReader(submittal.file_path)
    num_pages = len(reader.pages)

    # Group comments by page
    comments_by_page: dict[int, list] = {}
    unassigned = []
    for c in comments:
        if c.page_number and 1 <= c.page_number <= num_pages:
            comments_by_page.setdefault(c.page_number, [])
            comments_by_page[c.page_number].append(c)
        else:
            unassigned.append(c)

    # Spread unassigned across pages
    if unassigned and num_pages > 0:
        max_per_page = 6
        for i, c in enumerate(unassigned):
            page_num = min(i // max_per_page + 1, num_pages)
            comments_by_page.setdefault(page_num, [])
            comments_by_page[page_num].append(c)

    # For each page with comments, create an overlay using reportlab
    # and merge it onto the page. This guarantees visibility in all viewers.
    writer = PdfWriter()

    for page_idx in range(num_pages):
        page = reader.pages[page_idx]
        page_num = page_idx + 1
        page_comments = comments_by_page.get(page_num, [])

        if page_comments:
            media_box = page.mediabox
            page_width = float(media_box.width)
            page_height = float(media_box.height)

            overlay_buffer = _create_annotation_overlay(
                page_comments, page_width, page_height
            )
            overlay_reader = PdfReader(overlay_buffer)
            if len(overlay_reader.pages) > 0:
                page.merge_page(overlay_reader.pages[0])

        writer.add_page(page)

    # Build final: summary pages first, then annotated pages
    summary_buffer = _create_summary_pages(comments, submittal)
    summary_reader = PdfReader(summary_buffer)

    summary_page_count = len(summary_reader.pages)

    final_writer = PdfWriter()
    for sp in summary_reader.pages:
        final_writer.add_page(sp)
    for p in writer.pages:
        final_writer.add_page(p)

    # Save
    annotated_dir = os.path.join(os.path.dirname(submittal.file_path), "annotated")
    os.makedirs(annotated_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(submittal.file_path))[0]
    annotated_path = os.path.join(annotated_dir, f"{base_name}_MARKED_UP.pdf")

    with open(annotated_path, "wb") as f:
        final_writer.write(f)

    submittal.annotated_file_path = annotated_path
    db.commit()
    return annotated_path, summary_page_count


def _create_annotation_overlay(comments: list, page_width: float, page_height: float) -> BytesIO:
    """Create a transparent overlay PDF with callout-style comment boxes using reportlab.

    This renders as actual drawn content, guaranteed visible in every PDF viewer.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    severity_colors = {
        "critical": (0.85, 0.1, 0.1),
        "major": (0.85, 0.45, 0.0),
        "minor": (0.7, 0.6, 0.0),
        "info": (0.15, 0.4, 0.85),
    }

    severity_bg = {
        "critical": (1.0, 0.92, 0.92),
        "major": (1.0, 0.95, 0.88),
        "minor": (1.0, 1.0, 0.9),
        "info": (0.9, 0.94, 1.0),
    }

    # Comment boxes go along the right side
    box_width = 175
    margin = 8
    box_x = page_width - box_width - margin
    current_y = page_height - 25
    line_height = 8
    padding = 5

    for i, comment in enumerate(comments):
        severity = comment.severity or "info"
        fg = severity_colors.get(severity, (0.3, 0.3, 0.3))
        bg = severity_bg.get(severity, (0.97, 0.97, 0.97))

        # Build text
        header = f"[{severity.upper()}]"
        ref = f" {comment.reference_code}" if comment.reference_code else ""
        body = comment.comment_text[:160]

        # Wrap body text
        body_lines = _wrap_text(body, box_width - 2 * padding, 7)
        body_lines = body_lines[:4]  # Max 4 lines

        # Calculate box height
        box_height = padding + 10 + len(body_lines) * line_height + padding

        box_y = current_y - box_height

        if box_y < 20:
            break  # Out of room

        # --- Draw the callout line (arrow from drawing area to box) ---
        arrow_tip_x = box_x - 20
        arrow_tip_y = box_y + box_height / 2
        arrow_start_x = box_x
        arrow_start_y = box_y + box_height / 2

        c.setStrokeColorRGB(*fg)
        c.setLineWidth(1.2)
        c.line(arrow_tip_x, arrow_tip_y, arrow_start_x, arrow_start_y)

        # Arrowhead
        arrow_size = 6
        c.setFillColorRGB(*fg)
        arrow_path = c.beginPath()
        arrow_path.moveTo(arrow_tip_x, arrow_tip_y)
        arrow_path.lineTo(arrow_tip_x + arrow_size, arrow_tip_y + arrow_size / 2.5)
        arrow_path.lineTo(arrow_tip_x + arrow_size, arrow_tip_y - arrow_size / 2.5)
        arrow_path.close()
        c.drawPath(arrow_path, fill=True, stroke=False)

        # --- Draw box background ---
        c.setFillColorRGB(*bg)
        c.setStrokeColorRGB(*fg)
        c.setLineWidth(1.5)
        c.roundRect(box_x, box_y, box_width, box_height, 3, fill=True, stroke=True)

        # --- Draw severity header ---
        text_x = box_x + padding
        text_y = box_y + box_height - padding - 8

        c.setFillColorRGB(*fg)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(text_x, text_y, header + ref)

        # --- Draw body text ---
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.setFont("Helvetica", 6.5)
        text_y -= line_height + 1
        for line in body_lines:
            c.drawString(text_x, text_y, line)
            text_y -= line_height

        # --- Draw page indicator if we know the page ---
        if comment.page_number:
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.setFont("Helvetica", 5)
            c.drawRightString(box_x + box_width - padding, box_y + 3, f"pg {comment.page_number}")

        current_y = box_y - 6  # Spacing between boxes

    c.save()
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
#  Summary cover pages
# ---------------------------------------------------------------------------

def _create_summary_pages(comments: list, submittal) -> BytesIO:
    """Create professional summary cover pages."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    w, h = letter

    # Title bar
    c.setFillColor(Color(0.12, 0.18, 0.30))
    c.rect(0, h - 80, w, 80, fill=True, stroke=False)
    c.setFillColor(Color(1, 1, 1))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, h - 45, "SUBMITTAL REVIEW MARKUP")
    c.setFont("Helvetica", 11)
    c.drawString(50, h - 62, "DataCenter Submittal Review Platform")

    # Project info box
    y = h - 105
    c.setFillColor(Color(0.95, 0.95, 0.97))
    c.rect(40, y - 80, w - 80, 85, fill=True, stroke=False)
    c.setStrokeColor(Color(0.8, 0.8, 0.8))
    c.rect(40, y - 80, w - 80, 85, fill=False, stroke=True)

    c.setFillColor(Color(0.1, 0.1, 0.1))
    iy = y - 5
    _info(c, 55, iy, "Submittal:", submittal.title or "N/A")
    iy -= 16
    _info(c, 55, iy, "Equipment:", submittal.equipment_type.replace("_", " ").title())
    _info(c, 320, iy, "Submittal No:", submittal.submittal_number or "N/A")
    iy -= 16
    _info(c, 55, iy, "Manufacturer:", submittal.manufacturer or "N/A")
    _info(c, 320, iy, "Contractor:", submittal.contractor or "N/A")
    iy -= 16
    _info(c, 55, iy, "Status:", (submittal.status or "").replace("_", " ").upper())

    # Stat boxes
    total = len(comments)
    critical = sum(1 for co in comments if co.severity == "critical")
    major = sum(1 for co in comments if co.severity == "major")
    minor = sum(1 for co in comments if co.severity == "minor")
    open_ct = sum(1 for co in comments if co.status == "open")

    sy = h - 215
    for i, (label, val, clr) in enumerate([
        ("TOTAL", total, Color(0.2, 0.3, 0.6)),
        ("CRITICAL", critical, Color(0.8, 0.1, 0.1)),
        ("MAJOR", major, Color(0.85, 0.45, 0)),
        ("MINOR", minor, Color(0.7, 0.6, 0)),
        ("OPEN", open_ct, Color(0.9, 0.2, 0.2)),
    ]):
        bx = 50 + i * 102
        c.setFillColor(clr)
        c.rect(bx, sy, 90, 45, fill=True, stroke=False)
        c.setFillColor(Color(1, 1, 1))
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(bx + 45, sy + 22, str(val))
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx + 45, sy + 8, label)

    # Table
    ty = sy - 30
    _table_hdr(c, ty, w)
    y = ty - 16

    sev_clr = {
        "critical": Color(0.75, 0.05, 0.05), "major": Color(0.75, 0.35, 0),
        "minor": Color(0.55, 0.45, 0), "info": Color(0.2, 0.35, 0.7),
    }
    row_bg = [Color(1, 1, 1), Color(0.96, 0.96, 0.98)]

    for i, co in enumerate(comments):
        lines = _wrap_text(co.comment_text[:250], 230, 7)[:3]
        rh = max(14, len(lines) * 10 + 4)

        if y - rh < 40:
            c.showPage()
            y = h - 50
            _table_hdr(c, y, w)
            y -= 16

        c.setFillColor(row_bg[i % 2])
        c.rect(40, y - rh + 12, w - 80, rh, fill=True, stroke=False)

        c.setFont("Helvetica", 7)
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.drawString(50, y, str(i + 1))
        c.drawString(68, y, str(co.page_number or "-"))

        c.setFillColor(sev_clr.get(co.severity, Color(0.3, 0.3, 0.3)))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(95, y, co.severity.upper())

        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.setFont("Helvetica", 7)
        c.drawString(150, y, co.status.upper())
        c.drawString(200, y, (co.reference_code or "")[:18])

        c.setFillColor(Color(0.1, 0.1, 0.1))
        for j, line in enumerate(lines):
            c.drawString(290, y - (j * 10), line)

        y -= rh

    c.save()
    buffer.seek(0)
    return buffer


def _info(c, x, y, label, value):
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, label)
    c.setFont("Helvetica", 10)
    c.drawString(x + len(label) * 6 + 10, y, value)


def _table_hdr(c, y, w):
    c.setFillColor(Color(0.12, 0.18, 0.30))
    c.rect(40, y - 2, w - 80, 18, fill=True, stroke=False)
    c.setFillColor(Color(1, 1, 1))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, y + 3, "#")
    c.drawString(68, y + 3, "PG")
    c.drawString(95, y + 3, "SEVERITY")
    c.drawString(150, y + 3, "STATUS")
    c.drawString(200, y + 3, "REFERENCE")
    c.drawString(290, y + 3, "COMMENT")


def _wrap_text(text: str, max_width: float, font_size: float) -> list[str]:
    chars_per_line = int(max_width / (font_size * 0.45))
    lines = []
    words = text.split()
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > chars_per_line:
            if current:
                lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines
