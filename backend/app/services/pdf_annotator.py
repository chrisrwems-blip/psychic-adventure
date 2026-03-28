"""PDF annotation service - add markup/comments to PDF files."""
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
        .order_by(ReviewComment.page_number, ReviewComment.id)
        .all()
    )

    reader = PdfReader(submittal.file_path)
    writer = PdfWriter()

    # Group comments by page (1-indexed), unassigned go to page 1
    comments_by_page: dict[int, list[ReviewComment]] = {}
    for c in comments:
        page = (c.page_number or 1) - 1  # Convert to 0-indexed
        if page < 0 or page >= len(reader.pages):
            page = 0
        comments_by_page.setdefault(page, [])
        comments_by_page[page].append(c)

    for page_idx, page in enumerate(reader.pages):
        page_comments = comments_by_page.get(page_idx, [])

        if page_comments:
            # Get page dimensions
            media_box = page.mediabox
            page_width = float(media_box.width)
            page_height = float(media_box.height)

            # Create overlay with comments
            overlay_buffer = BytesIO()
            overlay = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

            _draw_comment_sidebar(overlay, page_comments, page_width, page_height)
            _draw_comment_markers(overlay, page_comments, page_width, page_height)

            overlay.save()
            overlay_buffer.seek(0)

            # Merge overlay onto page
            overlay_reader = PdfReader(overlay_buffer)
            if len(overlay_reader.pages) > 0:
                page.merge_page(overlay_reader.pages[0])

        writer.add_page(page)

    # Add summary page at the end
    summary_buffer = _create_summary_page(comments, submittal)
    summary_reader = PdfReader(summary_buffer)
    for sp in summary_reader.pages:
        writer.add_page(sp)

    # Save annotated PDF
    annotated_dir = os.path.join(os.path.dirname(submittal.file_path), "annotated")
    os.makedirs(annotated_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(submittal.file_path))[0]
    annotated_path = os.path.join(annotated_dir, f"{base_name}_MARKED_UP.pdf")

    with open(annotated_path, "wb") as f:
        writer.write(f)

    # Update submittal record
    submittal.annotated_file_path = annotated_path
    db.commit()

    return annotated_path


def _draw_comment_sidebar(c: canvas.Canvas, comments: list, page_width: float, page_height: float):
    """Draw a comment sidebar on the right edge of the page."""
    sidebar_width = 180
    margin = 5
    x_start = page_width - sidebar_width - margin
    y_start = page_height - 30

    # Semi-transparent sidebar background
    c.setFillColor(Color(1, 1, 0.85, alpha=0.85))
    c.rect(x_start - 5, 10, sidebar_width + 10, page_height - 20, fill=True, stroke=False)

    # Border
    c.setStrokeColor(Color(0.6, 0.6, 0.6))
    c.setLineWidth(0.5)
    c.line(x_start - 5, 10, x_start - 5, page_height - 10)

    # Header
    c.setFillColor(Color(0.2, 0.2, 0.2))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_start, y_start, "REVIEW COMMENTS")
    c.setLineWidth(0.3)
    c.line(x_start, y_start - 3, x_start + sidebar_width - 10, y_start - 3)

    y = y_start - 15

    severity_colors = {
        "critical": Color(0.8, 0.1, 0.1),
        "major": Color(0.8, 0.4, 0),
        "minor": Color(0.7, 0.6, 0),
        "info": Color(0.2, 0.4, 0.8),
    }

    for i, comment in enumerate(comments):
        if y < 30:
            break  # Don't overflow page

        color = severity_colors.get(comment.severity, Color(0.3, 0.3, 0.3))

        # Severity badge
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 6)
        badge_text = comment.severity.upper()
        c.drawString(x_start, y, f"[{badge_text}]")

        # Reference code
        if comment.reference_code:
            c.setFillColor(Color(0.4, 0.4, 0.4))
            c.setFont("Helvetica", 5)
            c.drawString(x_start + 45, y, comment.reference_code)

        y -= 9

        # Comment text (wrapped)
        c.setFillColor(Color(0.1, 0.1, 0.1))
        c.setFont("Helvetica", 6)
        text = comment.comment_text[:200]  # Truncate long comments
        lines = _wrap_text(text, sidebar_width - 10, 6)
        for line in lines[:4]:  # Max 4 lines per comment
            if y < 30:
                break
            c.drawString(x_start, y, line)
            y -= 8

        # Divider
        y -= 3
        c.setStrokeColor(Color(0.8, 0.8, 0.8))
        c.setLineWidth(0.2)
        c.line(x_start, y, x_start + sidebar_width - 10, y)
        y -= 5


def _draw_comment_markers(c: canvas.Canvas, comments: list, page_width: float, page_height: float):
    """Draw numbered markers at comment positions (if x,y are set) or along the left margin."""
    severity_colors = {
        "critical": Color(0.9, 0.1, 0.1),
        "major": Color(0.9, 0.5, 0),
        "minor": Color(0.8, 0.7, 0),
        "info": Color(0.2, 0.5, 0.9),
    }

    for i, comment in enumerate(comments):
        color = severity_colors.get(comment.severity, Color(0.5, 0.5, 0.5))

        if comment.x_position and comment.y_position:
            # Use stored position (normalized 0-1)
            x = comment.x_position * page_width
            y = comment.y_position * page_height
        else:
            # Place markers along left margin
            x = 15
            y = page_height - 50 - (i * 25)
            if y < 30:
                continue

        # Draw circle marker
        c.setFillColor(color)
        c.circle(x, y, 6, fill=True, stroke=False)

        # Number in circle
        c.setFillColor(Color(1, 1, 1))
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x, y - 2.5, str(i + 1))


def _wrap_text(text: str, max_width: float, font_size: float) -> list[str]:
    """Simple text wrapping based on approximate character width."""
    chars_per_line = int(max_width / (font_size * 0.5))
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


def _create_summary_page(comments: list, submittal) -> BytesIO:
    """Create a summary page listing all comments."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "SUBMITTAL REVIEW COMMENT SUMMARY")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Submittal: {submittal.title}")
    c.drawString(50, height - 85, f"Equipment Type: {submittal.equipment_type.replace('_', ' ').title()}")
    if submittal.manufacturer:
        c.drawString(50, height - 100, f"Manufacturer: {submittal.manufacturer}")
    if submittal.submittal_number:
        c.drawString(350, height - 70, f"Submittal No: {submittal.submittal_number}")

    c.setLineWidth(1)
    c.line(50, height - 110, width - 50, height - 110)

    # Stats
    y = height - 130
    total = len(comments)
    critical = sum(1 for co in comments if co.severity == "critical")
    major = sum(1 for co in comments if co.severity == "major")
    minor = sum(1 for co in comments if co.severity == "minor")
    open_count = sum(1 for co in comments if co.status == "open")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, f"Total Comments: {total}")
    c.drawString(200, y, f"Critical: {critical}")
    c.drawString(300, y, f"Major: {major}")
    c.drawString(400, y, f"Minor: {minor}")
    c.drawString(480, y, f"Open: {open_count}")

    y -= 25

    # Table header
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, y, "#")
    c.drawString(65, y, "SEVERITY")
    c.drawString(120, y, "STATUS")
    c.drawString(170, y, "REFERENCE")
    c.drawString(250, y, "COMMENT")
    c.line(50, y - 3, width - 50, y - 3)
    y -= 15

    # Comments
    c.setFont("Helvetica", 7)
    for i, co in enumerate(comments):
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 7)

        c.drawString(50, y, str(i + 1))
        c.drawString(65, y, co.severity.upper())
        c.drawString(120, y, co.status.upper())
        c.drawString(170, y, (co.reference_code or "")[:15])

        # Wrap comment text
        text_lines = _wrap_text(co.comment_text[:300], 300, 7)
        for j, line in enumerate(text_lines[:3]):
            c.drawString(250, y - (j * 9), line)

        y -= max(12, len(text_lines[:3]) * 9 + 5)

    c.save()
    buffer.seek(0)
    return buffer
