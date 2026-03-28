"""PDF annotation service - add real PDF annotations with callout lines."""
import math
import os
from io import BytesIO
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import (
    ArrayObject, DictionaryObject, FloatObject, NameObject,
    NumberObject, TextStringObject, RectangleObject,
)
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, ReviewComment


def annotate_pdf(db: Session, submittal_id: int) -> str:
    """Create an annotated copy of a submittal PDF with real PDF annotations."""
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

    # Copy all pages first
    for page in reader.pages:
        writer.add_page(page)

    # Group comments by page (1-indexed)
    comments_by_page: dict[int, list] = {}
    unassigned = []
    for c in comments:
        if c.page_number and 1 <= c.page_number <= num_pages:
            comments_by_page.setdefault(c.page_number, [])
            comments_by_page[c.page_number].append(c)
        else:
            unassigned.append(c)

    # Put unassigned comments on the last page (most likely the drawings)
    if unassigned:
        last_page = num_pages
        comments_by_page.setdefault(last_page, [])
        comments_by_page[last_page].extend(unassigned)

    # Add annotations to each page
    for page_num, page_comments in comments_by_page.items():
        page_idx = page_num - 1
        page = writer.pages[page_idx]
        media_box = page.mediabox
        page_width = float(media_box.width)
        page_height = float(media_box.height)

        _add_annotations_to_page(page, page_comments, page_width, page_height)

    # Add summary pages at the front
    summary_buffer = _create_summary_pages(comments, submittal)
    summary_reader = PdfReader(summary_buffer)

    # Build final PDF: summary pages first, then annotated original
    final_writer = PdfWriter()
    for sp in summary_reader.pages:
        final_writer.add_page(sp)
    for page in writer.pages:
        final_writer.add_page(page)

    # Save
    annotated_dir = os.path.join(os.path.dirname(submittal.file_path), "annotated")
    os.makedirs(annotated_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(submittal.file_path))[0]
    annotated_path = os.path.join(annotated_dir, f"{base_name}_MARKED_UP.pdf")

    with open(annotated_path, "wb") as f:
        final_writer.write(f)

    submittal.annotated_file_path = annotated_path
    db.commit()

    return annotated_path


def _add_annotations_to_page(page, comments: list, page_width: float, page_height: float):
    """Add FreeText callout annotations to a PDF page — same style as Bluebeam/Revu."""

    severity_colors = {
        "critical": [1.0, 0.0, 0.0],       # Red
        "major": [1.0, 0.5, 0.0],           # Orange
        "minor": [0.9, 0.75, 0.0],          # Yellow
        "info": [0.0, 0.4, 0.9],            # Blue
    }

    # Layout: place comment boxes along the right margin, stacked vertically
    margin_x = page_width - 200  # Right side of page
    box_width = 190
    box_height_per_line = 12
    spacing = 8
    current_y = page_height - 40  # Start near top

    existing_annots = page.get("/Annots")
    if existing_annots:
        try:
            annot_list = list(existing_annots)
        except:
            annot_list = []
    else:
        annot_list = []

    for i, comment in enumerate(comments):
        severity = comment.severity or "info"
        color = severity_colors.get(severity, [0.3, 0.3, 0.3])
        text = f"[{severity.upper()}] {comment.comment_text}"
        if comment.reference_code:
            text += f" ({comment.reference_code})"

        # Calculate box height based on text length
        chars_per_line = 35
        num_lines = max(1, math.ceil(len(text) / chars_per_line))
        num_lines = min(num_lines, 6)  # Cap at 6 lines
        box_height = num_lines * box_height_per_line + 10

        # Position the comment box
        box_x1 = margin_x
        box_y2 = current_y
        box_y1 = current_y - box_height
        box_x2 = box_x1 + box_width

        # Where the callout arrow points to on the drawing
        # Point to a spot on the left side of the page (the actual drawing area)
        point_x = margin_x - 30
        point_y = (box_y1 + box_y2) / 2

        # Elbow point for the callout line
        elbow_x = margin_x - 10
        elbow_y = (box_y1 + box_y2) / 2

        # Create FreeText annotation with callout line
        annot = DictionaryObject()
        annot.update({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/FreeText"),
            NameObject("/Rect"): ArrayObject([
                FloatObject(box_x1), FloatObject(box_y1),
                FloatObject(box_x2), FloatObject(box_y2),
            ]),
            NameObject("/Contents"): TextStringObject(text),
            NameObject("/IT"): NameObject("/FreeTextCallout"),
            NameObject("/CL"): ArrayObject([
                FloatObject(point_x), FloatObject(point_y),
                FloatObject(elbow_x), FloatObject(elbow_y),
                FloatObject(box_x1), FloatObject((box_y1 + box_y2) / 2),
            ]),
            NameObject("/C"): ArrayObject([FloatObject(c) for c in color]),
            NameObject("/CA"): FloatObject(0.8),  # Opacity
            NameObject("/Border"): ArrayObject([
                NumberObject(0), NumberObject(0), NumberObject(1),
            ]),
            NameObject("/BS"): DictionaryObject({
                NameObject("/W"): NumberObject(1),
                NameObject("/S"): NameObject("/S"),
            }),
            NameObject("/DA"): TextStringObject("/Helv 8 Tf 0 0 0 rg"),
            NameObject("/DS"): TextStringObject(
                f"font: Helvetica 8pt; color: #{''.join(f'{int(c*255):02x}' for c in color)}"
            ),
            NameObject("/LE"): ArrayObject([NameObject("/OpenArrow"), NameObject("/None")]),
        })

        annot_list.append(annot)

        current_y -= (box_height + spacing)

        # If we've run out of vertical space, wrap to a second column
        if current_y < 40:
            current_y = page_height - 40
            margin_x -= 210  # Move left for next column
            if margin_x < 50:
                break  # Too many comments for this page

    # Set annotations on the page
    page[NameObject("/Annots")] = ArrayObject(annot_list)


# ---------------------------------------------------------------------------
#  Summary cover pages (same as before)
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

    # Project info
    y = h - 105
    c.setFillColor(Color(0.95, 0.95, 0.97))
    c.rect(40, y - 80, w - 80, 85, fill=True, stroke=False)
    c.setStrokeColor(Color(0.8, 0.8, 0.8))
    c.rect(40, y - 80, w - 80, 85, fill=False, stroke=True)

    c.setFillColor(Color(0.1, 0.1, 0.1))
    info_y = y - 5
    _draw_info_row(c, 55, info_y, "Submittal:", submittal.title or "N/A")
    info_y -= 16
    _draw_info_row(c, 55, info_y, "Equipment:", submittal.equipment_type.replace("_", " ").title())
    _draw_info_row(c, 320, info_y, "Submittal No:", submittal.submittal_number or "N/A")
    info_y -= 16
    _draw_info_row(c, 55, info_y, "Manufacturer:", submittal.manufacturer or "N/A")
    _draw_info_row(c, 320, info_y, "Contractor:", submittal.contractor or "N/A")
    info_y -= 16
    _draw_info_row(c, 55, info_y, "Status:", (submittal.status or "").replace("_", " ").upper())

    # Stats boxes
    total = len(comments)
    critical = sum(1 for co in comments if co.severity == "critical")
    major = sum(1 for co in comments if co.severity == "major")
    minor = sum(1 for co in comments if co.severity == "minor")
    open_ct = sum(1 for co in comments if co.status == "open")

    stat_y = h - 215
    stat_items = [
        ("TOTAL", str(total), Color(0.2, 0.3, 0.6)),
        ("CRITICAL", str(critical), Color(0.8, 0.1, 0.1)),
        ("MAJOR", str(major), Color(0.85, 0.45, 0)),
        ("MINOR", str(minor), Color(0.7, 0.6, 0)),
        ("OPEN", str(open_ct), Color(0.9, 0.2, 0.2)),
    ]

    box_w = 90
    for i, (label, val, color) in enumerate(stat_items):
        bx = 50 + i * (box_w + 12)
        c.setFillColor(color)
        c.rect(bx, stat_y, box_w, 45, fill=True, stroke=False)
        c.setFillColor(Color(1, 1, 1))
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(bx + box_w / 2, stat_y + 22, val)
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx + box_w / 2, stat_y + 8, label)

    # Comment table
    table_y = stat_y - 30
    _draw_table_header(c, table_y, w)
    y = table_y - 16

    severity_text_colors = {
        "critical": Color(0.75, 0.05, 0.05),
        "major": Color(0.75, 0.35, 0),
        "minor": Color(0.55, 0.45, 0),
        "info": Color(0.2, 0.35, 0.7),
    }
    row_colors = [Color(1, 1, 1), Color(0.96, 0.96, 0.98)]

    for i, co in enumerate(comments):
        text_lines = _wrap_text(co.comment_text[:250], 230, 7)
        lines_to_show = min(len(text_lines), 3)
        row_h = max(14, lines_to_show * 10 + 4)

        if y - row_h < 40:
            c.showPage()
            y = h - 50
            _draw_table_header(c, y, w)
            y -= 16

        # Row background
        c.setFillColor(row_colors[i % 2])
        c.rect(40, y - row_h + 12, w - 80, row_h, fill=True, stroke=False)

        c.setFont("Helvetica", 7)

        # Number
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.drawString(50, y, str(i + 1))

        # Page
        c.drawString(68, y, str(co.page_number or "-"))

        # Severity
        sev_color = severity_text_colors.get(co.severity, Color(0.3, 0.3, 0.3))
        c.setFillColor(sev_color)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(95, y, co.severity.upper())

        # Status
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.setFont("Helvetica", 7)
        c.drawString(150, y, co.status.upper())

        # Reference
        c.drawString(200, y, (co.reference_code or "")[:18])

        # Comment
        c.setFillColor(Color(0.1, 0.1, 0.1))
        for j, line in enumerate(text_lines[:3]):
            c.drawString(290, y - (j * 10), line)

        y -= row_h

    c.save()
    buffer.seek(0)
    return buffer


def _draw_info_row(c, x, y, label, value):
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, label)
    c.setFont("Helvetica", 10)
    c.drawString(x + len(label) * 6 + 10, y, value)


def _draw_table_header(c, y, w):
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
