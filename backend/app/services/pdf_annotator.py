"""PDF annotation service - add markup/comments to PDF files."""
import math
import os
from io import BytesIO
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, ReviewComment


def annotate_pdf(db: Session, submittal_id: int) -> str:
    """Create an annotated copy of a submittal PDF with review comments overlaid."""
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
    writer = PdfWriter()
    num_pages = len(reader.pages)

    # Split comments: those with assigned pages vs unassigned
    assigned = [c for c in comments if c.page_number and 1 <= c.page_number <= num_pages]
    unassigned = [c for c in comments if not c.page_number or c.page_number < 1 or c.page_number > num_pages]

    # Group assigned comments by page (0-indexed)
    comments_by_page: dict[int, list] = {}
    for c in assigned:
        page_idx = c.page_number - 1
        comments_by_page.setdefault(page_idx, [])
        comments_by_page[page_idx].append(c)

    # Spread unassigned comments evenly across all pages
    if unassigned and num_pages > 0:
        # How many comments fit per page sidebar (roughly)
        max_per_page = 8
        for i, c in enumerate(unassigned):
            page_idx = min(i // max_per_page, num_pages - 1)
            comments_by_page.setdefault(page_idx, [])
            comments_by_page[page_idx].append(c)

    # --- Build the PDF ---

    # 1. Add cover summary pages FIRST
    summary_pages = _create_summary_pages(comments, submittal)
    summary_reader = PdfReader(summary_pages)
    for sp in summary_reader.pages:
        writer.add_page(sp)

    # 2. Add original pages with comment sidebars
    for page_idx, page in enumerate(reader.pages):
        page_comments = comments_by_page.get(page_idx, [])

        if page_comments:
            media_box = page.mediabox
            page_width = float(media_box.width)
            page_height = float(media_box.height)

            overlay_buffer = BytesIO()
            overlay = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

            _draw_comment_sidebar(overlay, page_comments, page_width, page_height)

            overlay.save()
            overlay_buffer.seek(0)

            overlay_reader = PdfReader(overlay_buffer)
            if len(overlay_reader.pages) > 0:
                page.merge_page(overlay_reader.pages[0])

        writer.add_page(page)

    # Save annotated PDF
    annotated_dir = os.path.join(os.path.dirname(submittal.file_path), "annotated")
    os.makedirs(annotated_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(submittal.file_path))[0]
    annotated_path = os.path.join(annotated_dir, f"{base_name}_MARKED_UP.pdf")

    with open(annotated_path, "wb") as f:
        writer.write(f)

    submittal.annotated_file_path = annotated_path
    db.commit()

    return annotated_path


# ---------------------------------------------------------------------------
#  Sidebar drawing
# ---------------------------------------------------------------------------

def _draw_comment_sidebar(c: canvas.Canvas, comments: list, page_width: float, page_height: float):
    """Draw a narrow comment sidebar on the right edge of the page."""
    sidebar_width = 170
    margin = 5
    x_start = page_width - sidebar_width - margin
    y_start = page_height - 25

    # Background
    c.setFillColor(Color(1, 1, 0.88, alpha=0.90))
    c.rect(x_start - 5, 10, sidebar_width + 10, page_height - 20, fill=True, stroke=False)

    # Left border line
    c.setStrokeColor(Color(0.5, 0.5, 0.5))
    c.setLineWidth(0.75)
    c.line(x_start - 5, 10, x_start - 5, page_height - 10)

    # Header
    c.setFillColor(Color(0.15, 0.15, 0.15))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x_start, y_start, "REVIEW COMMENTS")
    c.setLineWidth(0.3)
    c.line(x_start, y_start - 3, x_start + sidebar_width - 10, y_start - 3)

    y = y_start - 14

    severity_colors = {
        "critical": Color(0.8, 0.1, 0.1),
        "major": Color(0.8, 0.4, 0),
        "minor": Color(0.6, 0.55, 0),
        "info": Color(0.2, 0.4, 0.8),
    }

    for comment in comments:
        if y < 25:
            break

        color = severity_colors.get(comment.severity, Color(0.3, 0.3, 0.3))

        # Severity tag
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(x_start, y, f"[{comment.severity.upper()}]")

        # Reference
        ref_x = x_start + 42
        if comment.reference_code:
            c.setFillColor(Color(0.35, 0.35, 0.35))
            c.setFont("Helvetica-Oblique", 5)
            c.drawString(ref_x, y, comment.reference_code[:25])

        y -= 8

        # Comment text
        c.setFillColor(Color(0.1, 0.1, 0.1))
        c.setFont("Helvetica", 5.5)
        text = comment.comment_text[:180]
        lines = _wrap_text(text, sidebar_width - 12, 5.5)
        for line in lines[:3]:
            if y < 25:
                break
            c.drawString(x_start, y, line)
            y -= 7

        # Thin divider
        y -= 2
        c.setStrokeColor(Color(0.82, 0.82, 0.82))
        c.setLineWidth(0.2)
        c.line(x_start, y, x_start + sidebar_width - 10, y)
        y -= 4


# ---------------------------------------------------------------------------
#  Summary cover pages
# ---------------------------------------------------------------------------

def _create_summary_pages(comments: list, submittal) -> BytesIO:
    """Create professional summary cover pages listing all comments."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    w, h = letter

    # --- Page 1: Header ---
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
    info_y = y - 5
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, info_y, "Submittal:")
    c.setFont("Helvetica", 10)
    c.drawString(130, info_y, submittal.title or "N/A")

    info_y -= 16
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, info_y, "Equipment:")
    c.setFont("Helvetica", 10)
    c.drawString(130, info_y, submittal.equipment_type.replace("_", " ").title())

    c.setFont("Helvetica-Bold", 10)
    c.drawString(320, info_y, "Submittal No:")
    c.setFont("Helvetica", 10)
    c.drawString(410, info_y, submittal.submittal_number or "N/A")

    info_y -= 16
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, info_y, "Manufacturer:")
    c.setFont("Helvetica", 10)
    c.drawString(140, info_y, submittal.manufacturer or "N/A")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(320, info_y, "Contractor:")
    c.setFont("Helvetica", 10)
    c.drawString(400, info_y, submittal.contractor or "N/A")

    info_y -= 16
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, info_y, "Status:")
    c.setFont("Helvetica", 10)
    c.drawString(130, info_y, (submittal.status or "").replace("_", " ").upper())

    # --- Statistics boxes ---
    total = len(comments)
    critical = sum(1 for co in comments if co.severity == "critical")
    major = sum(1 for co in comments if co.severity == "major")
    minor = sum(1 for co in comments if co.severity == "minor")
    info = sum(1 for co in comments if co.severity == "info")
    open_ct = sum(1 for co in comments if co.status == "open")

    stat_y = h - 215
    box_w = 90
    box_h = 45
    gap = 12
    start_x = 50

    stat_items = [
        ("TOTAL", str(total), Color(0.2, 0.3, 0.6)),
        ("CRITICAL", str(critical), Color(0.8, 0.1, 0.1)),
        ("MAJOR", str(major), Color(0.85, 0.45, 0)),
        ("MINOR", str(minor), Color(0.7, 0.6, 0)),
        ("OPEN", str(open_ct), Color(0.9, 0.2, 0.2)),
    ]

    for i, (label, val, color) in enumerate(stat_items):
        bx = start_x + i * (box_w + gap)
        c.setFillColor(color)
        c.rect(bx, stat_y, box_w, box_h, fill=True, stroke=False)
        c.setFillColor(Color(1, 1, 1))
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(bx + box_w / 2, stat_y + 22, val)
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx + box_w / 2, stat_y + 8, label)

    # --- Comment table ---
    table_y = stat_y - 30

    c.setFillColor(Color(0.12, 0.18, 0.30))
    c.rect(40, table_y - 2, w - 80, 18, fill=True, stroke=False)
    c.setFillColor(Color(1, 1, 1))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, table_y + 3, "#")
    c.drawString(68, table_y + 3, "SEVERITY")
    c.drawString(130, table_y + 3, "STATUS")
    c.drawString(190, table_y + 3, "REFERENCE")
    c.drawString(290, table_y + 3, "COMMENT")

    y = table_y - 16
    row_colors = [Color(1, 1, 1), Color(0.96, 0.96, 0.98)]

    severity_text_colors = {
        "critical": Color(0.75, 0.05, 0.05),
        "major": Color(0.75, 0.35, 0),
        "minor": Color(0.55, 0.45, 0),
        "info": Color(0.2, 0.35, 0.7),
    }

    for i, co in enumerate(comments):
        # Calculate row height
        text_lines = _wrap_text(co.comment_text[:250], 270, 7)
        lines_to_show = min(len(text_lines), 3)
        row_h = max(14, lines_to_show * 10 + 4)

        if y - row_h < 40:
            # New page
            c.showPage()
            y = h - 50

            # Repeat header
            c.setFillColor(Color(0.12, 0.18, 0.30))
            c.rect(40, y - 2, w - 80, 18, fill=True, stroke=False)
            c.setFillColor(Color(1, 1, 1))
            c.setFont("Helvetica-Bold", 8)
            c.drawString(50, y + 3, "#")
            c.drawString(68, y + 3, "SEVERITY")
            c.drawString(130, y + 3, "STATUS")
            c.drawString(190, y + 3, "REFERENCE")
            c.drawString(290, y + 3, "COMMENT")
            y -= 16

        # Row background
        c.setFillColor(row_colors[i % 2])
        c.rect(40, y - row_h + 12, w - 80, row_h, fill=True, stroke=False)

        # Row number
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.setFont("Helvetica", 7)
        c.drawString(50, y, str(i + 1))

        # Severity (colored)
        sev_color = severity_text_colors.get(co.severity, Color(0.3, 0.3, 0.3))
        c.setFillColor(sev_color)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(68, y, co.severity.upper())

        # Status
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.setFont("Helvetica", 7)
        c.drawString(130, y, co.status.upper())

        # Reference
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.setFont("Helvetica", 6.5)
        c.drawString(190, y, (co.reference_code or "")[:20])

        # Comment text
        c.setFillColor(Color(0.1, 0.1, 0.1))
        c.setFont("Helvetica", 7)
        for j, line in enumerate(text_lines[:3]):
            c.drawString(290, y - (j * 10), line)

        y -= row_h

    c.save()
    buffer.seek(0)
    return buffer


def _wrap_text(text: str, max_width: float, font_size: float) -> list[str]:
    """Simple text wrapping based on approximate character width."""
    chars_per_line = int(max_width / (font_size * 0.45))
    lines = []
    words = text.split()
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 > chars_per_line:
            if current_line:
                lines.append(current_line)
            current_line = word
        else:
            current_line = f"{current_line} {word}" if current_line else word
    if current_line:
        lines.append(current_line)
    return lines
