"""Review report generator — creates a standalone professional PDF review report.

This is NOT the marked-up submittal. This is a separate document summarizing:
- Cover page with project/submittal metadata and disposition
- Executive summary with pass/fail/review stats
- Jurisdiction detection results
- Equipment discovered table
- All findings sorted by severity
- SLD-to-schedule cross-check results
- Cross-reference findings (topology, sizing, coordination)
"""
import os
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, ReviewResult, ReviewComment


# ---------------------------------------------------------------------------
#  Color palette (matches pdf_annotator styling)
# ---------------------------------------------------------------------------
DARK_BLUE = Color(0.12, 0.18, 0.30)
WHITE = Color(1, 1, 1)
LIGHT_BG = Color(0.95, 0.95, 0.97)
BORDER_GRAY = Color(0.8, 0.8, 0.8)
TEXT_DARK = Color(0.1, 0.1, 0.1)
TEXT_MID = Color(0.3, 0.3, 0.3)
TEXT_LIGHT = Color(0.5, 0.5, 0.5)

SEVERITY_COLORS = {
    "critical": Color(0.75, 0.05, 0.05),
    "major": Color(0.75, 0.35, 0),
    "minor": Color(0.55, 0.45, 0),
    "info": Color(0.2, 0.35, 0.7),
}

SEVERITY_BG = {
    "critical": Color(1.0, 0.92, 0.92),
    "major": Color(1.0, 0.95, 0.88),
    "minor": Color(1.0, 1.0, 0.90),
    "info": Color(0.90, 0.94, 1.0),
}

STATUS_COLORS = {
    "approved": Color(0.13, 0.55, 0.13),
    "rejected": Color(0.75, 0.05, 0.05),
    "revise_resubmit": Color(0.85, 0.45, 0.0),
    "reviewed": Color(0.2, 0.35, 0.7),
    "reviewing": Color(0.5, 0.5, 0.5),
    "uploaded": Color(0.5, 0.5, 0.5),
}

ROW_COLORS = [WHITE, Color(0.96, 0.96, 0.98)]

# Page dimensions
W, H = letter
MARGIN_LEFT = 50
MARGIN_RIGHT = 50
CONTENT_WIDTH = W - MARGIN_LEFT - MARGIN_RIGHT
BOTTOM_MARGIN = 60


# ---------------------------------------------------------------------------
#  Main entry point
# ---------------------------------------------------------------------------

def generate_review_report(db: Session, submittal_id: int) -> str:
    """Generate a PDF review report and return the file path."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise ValueError(f"Submittal {submittal_id} not found")

    comments = (
        db.query(ReviewComment)
        .filter(ReviewComment.submittal_id == submittal_id)
        .order_by(ReviewComment.id)
        .all()
    )

    results = (
        db.query(ReviewResult)
        .filter(ReviewResult.submittal_id == submittal_id)
        .order_by(ReviewResult.check_category, ReviewResult.check_name)
        .all()
    )

    # Compute stats
    stats = _compute_stats(results, comments)

    # Build the PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    _draw_cover_page(c, submittal, stats)
    c.showPage()

    y = _draw_executive_summary(c, submittal, stats)
    y = _draw_jurisdiction_section(c, y, results)
    y = _check_page_break(c, y, 200)
    y = _draw_equipment_table(c, y, results)
    y = _check_page_break(c, y, 100)
    y = _draw_findings_by_severity(c, y, results, comments)
    y = _check_page_break(c, y, 100)
    y = _draw_sld_crosscheck(c, y, results)
    y = _check_page_break(c, y, 100)
    y = _draw_cross_reference(c, y, results)

    # Footer on last page
    _draw_footer(c)

    c.save()
    buffer.seek(0)

    # Write to file
    report_dir = os.path.join(os.path.dirname(submittal.file_path), "reports")
    os.makedirs(report_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(submittal.file_path))[0]
    report_path = os.path.join(report_dir, f"{base_name}_REVIEW_REPORT.pdf")

    with open(report_path, "wb") as f:
        f.write(buffer.read())

    return report_path


# ---------------------------------------------------------------------------
#  Stats computation
# ---------------------------------------------------------------------------

def _compute_stats(results: list, comments: list) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed == 1)
    failed = sum(1 for r in results if r.passed == 0)
    needs_review = sum(1 for r in results if r.passed == -1)

    critical = sum(1 for c in comments if c.severity == "critical")
    major = sum(1 for c in comments if c.severity == "major")
    minor = sum(1 for c in comments if c.severity == "minor")
    info = sum(1 for c in comments if c.severity == "info")
    open_ct = sum(1 for c in comments if c.status == "open")

    if critical > 0:
        recommendation = "REVISE AND RESUBMIT — Critical issues found"
    elif failed > 10 or major > 5:
        recommendation = "REVISE AND RESUBMIT — Multiple significant issues"
    elif failed > 0:
        recommendation = "APPROVED AS NOTED — Address comments before fabrication"
    elif needs_review > total * 0.5:
        recommendation = "REQUIRES MANUAL REVIEW — Insufficient data for automated review"
    else:
        recommendation = "APPROVED — No significant issues found"

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "needs_review": needs_review,
        "critical": critical,
        "major": major,
        "minor": minor,
        "info": info,
        "open": open_ct,
        "total_comments": len(comments),
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
#  Cover page
# ---------------------------------------------------------------------------

def _draw_cover_page(c, submittal, stats):
    """Full-page cover with project info and disposition stamp."""
    # Dark blue header band
    c.setFillColor(DARK_BLUE)
    c.rect(0, H - 160, W, 160, fill=True, stroke=False)

    # Title
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(MARGIN_LEFT, H - 70, "SUBMITTAL REVIEW REPORT")

    c.setFont("Helvetica", 13)
    c.drawString(MARGIN_LEFT, H - 95, "DC Submittal Review Platform")

    # Thin accent line
    c.setStrokeColor(Color(0.3, 0.5, 0.8))
    c.setLineWidth(2)
    c.line(MARGIN_LEFT, H - 115, W - MARGIN_RIGHT, H - 115)

    # Date line
    c.setFont("Helvetica", 11)
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    c.drawString(MARGIN_LEFT, H - 140, f"Report Generated: {now}")

    # --- Project info box ---
    box_top = H - 190
    box_height = 180
    c.setFillColor(LIGHT_BG)
    c.rect(MARGIN_LEFT - 10, box_top - box_height, CONTENT_WIDTH + 20, box_height,
           fill=True, stroke=False)
    c.setStrokeColor(BORDER_GRAY)
    c.rect(MARGIN_LEFT - 10, box_top - box_height, CONTENT_WIDTH + 20, box_height,
           fill=False, stroke=True)

    y = box_top - 20
    _info_line(c, MARGIN_LEFT, y, "Submittal Title:", submittal.title or "N/A")
    y -= 22
    _info_line(c, MARGIN_LEFT, y, "Submittal No:", submittal.submittal_number or "N/A")
    _info_line(c, 320, y, "Equipment Type:",
               (submittal.equipment_type or "").replace("_", " ").title())
    y -= 22
    _info_line(c, MARGIN_LEFT, y, "Manufacturer:", submittal.manufacturer or "N/A")
    _info_line(c, 320, y, "Model:", submittal.model_number or "N/A")
    y -= 22
    _info_line(c, MARGIN_LEFT, y, "Contractor:", submittal.contractor or "N/A")
    _info_line(c, 320, y, "Submitted By:", submittal.submitted_by or "N/A")
    y -= 22
    _info_line(c, MARGIN_LEFT, y, "Pages:", str(submittal.page_count or "N/A"))
    _info_line(c, 320, y, "Spec Section:", submittal.spec_section or "N/A")
    y -= 22
    reviewed = submittal.reviewed_at.strftime("%B %d, %Y") if submittal.reviewed_at else "N/A"
    _info_line(c, MARGIN_LEFT, y, "Review Date:", reviewed)

    # --- Disposition stamp ---
    stamp_y = box_top - box_height - 80
    status = submittal.status or "reviewed"
    status_label = status.replace("_", " ").upper()
    stamp_color = STATUS_COLORS.get(status, TEXT_MID)

    # Stamp box
    stamp_width = 280
    stamp_height = 50
    stamp_x = (W - stamp_width) / 2
    c.setStrokeColor(stamp_color)
    c.setLineWidth(3)
    c.rect(stamp_x, stamp_y, stamp_width, stamp_height, fill=False, stroke=True)

    c.setFillColor(stamp_color)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W / 2, stamp_y + 16, status_label)

    # --- Recommendation ---
    rec_y = stamp_y - 40
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_LEFT, rec_y, "Recommendation:")
    c.setFont("Helvetica", 11)
    c.drawString(MARGIN_LEFT + 110, rec_y, stats["recommendation"])

    # --- Quick stats boxes at bottom ---
    stat_y = rec_y - 60
    stat_items = [
        ("TOTAL CHECKS", stats["total"], DARK_BLUE),
        ("PASSED", stats["passed"], Color(0.13, 0.55, 0.13)),
        ("FAILED", stats["failed"], Color(0.75, 0.05, 0.05)),
        ("NEEDS REVIEW", stats["needs_review"], Color(0.85, 0.45, 0.0)),
        ("COMMENTS", stats["total_comments"], Color(0.2, 0.35, 0.7)),
    ]
    box_w = 95
    gap = 8
    total_w = len(stat_items) * box_w + (len(stat_items) - 1) * gap
    start_x = (W - total_w) / 2

    for i, (label, val, clr) in enumerate(stat_items):
        bx = start_x + i * (box_w + gap)
        c.setFillColor(clr)
        c.roundRect(bx, stat_y, box_w, 50, 4, fill=True, stroke=False)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(bx + box_w / 2, stat_y + 25, str(val))
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx + box_w / 2, stat_y + 10, label)

    # Footer
    _draw_footer(c)


# ---------------------------------------------------------------------------
#  Executive summary (page 2 top)
# ---------------------------------------------------------------------------

def _draw_executive_summary(c, submittal, stats) -> float:
    """Draw executive summary section. Returns current y position."""
    y = H - 30
    y = _draw_section_header(c, y, "EXECUTIVE SUMMARY")

    y -= 5
    c.setFillColor(LIGHT_BG)
    c.rect(MARGIN_LEFT - 5, y - 100, CONTENT_WIDTH + 10, 100, fill=True, stroke=False)

    iy = y - 15
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 10)

    lines = [
        f"Total automated checks performed: {stats['total']}",
        f"Passed: {stats['passed']}  |  Failed: {stats['failed']}  |  Needs Review: {stats['needs_review']}",
        f"Comments generated: {stats['total_comments']}  (Critical: {stats['critical']}, Major: {stats['major']}, Minor: {stats['minor']}, Info: {stats['info']})",
        f"Open items: {stats['open']}",
        "",
        f"Recommendation: {stats['recommendation']}",
    ]
    for line in lines:
        if line.startswith("Recommendation:"):
            c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN_LEFT + 5, iy, line)
        c.setFont("Helvetica", 10)
        iy -= 14

    return y - 115


# ---------------------------------------------------------------------------
#  Jurisdiction section
# ---------------------------------------------------------------------------

def _draw_jurisdiction_section(c, y: float, results: list) -> float:
    """Draw jurisdiction detection results."""
    y = _check_page_break(c, y, 120)
    y = _draw_section_header(c, y, "JURISDICTION / CODE DETECTION")

    # Pull jurisdiction info from review results
    jurisdiction_results = [
        r for r in results if r.check_category and "jurisdiction" in r.check_category.lower()
    ]
    jurisdiction_warnings = [
        r for r in results
        if r.check_category and "jurisdiction" in r.check_category.lower()
        and r.passed != 1
    ]

    y -= 5
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 10)

    if jurisdiction_results:
        for jr in jurisdiction_results:
            ref = jr.reference_standard or ""
            # Parse code and confidence from reference_standard field
            c.drawString(MARGIN_LEFT + 5, y, f"Detection: {ref}")
            y -= 14
            if jr.details:
                detail_lines = _wrap_text(jr.details, CONTENT_WIDTH - 10, 9)
                for dl in detail_lines[:3]:
                    c.drawString(MARGIN_LEFT + 5, y, dl)
                    y -= 13
            y -= 5
    else:
        c.drawString(MARGIN_LEFT + 5, y, "No jurisdiction data available. Run a full review to detect NEC vs IEC applicability.")
        y -= 14

    # Warnings
    if jurisdiction_warnings:
        y -= 5
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(SEVERITY_COLORS["critical"])
        c.drawString(MARGIN_LEFT + 5, y, "Jurisdiction Warnings:")
        c.setFont("Helvetica", 9)
        c.setFillColor(TEXT_DARK)
        y -= 14
        for jw in jurisdiction_warnings:
            lines = _wrap_text(jw.details or jw.check_name, CONTENT_WIDTH - 20, 9)
            for line in lines[:2]:
                c.drawString(MARGIN_LEFT + 15, y, f"- {line}")
                y -= 13
            y -= 3

    return y - 10


# ---------------------------------------------------------------------------
#  Equipment discovered table
# ---------------------------------------------------------------------------

def _draw_equipment_table(c, y: float, results: list) -> float:
    """Draw table of discovered equipment from cross-reference results."""
    y = _check_page_break(c, y, 150)
    y = _draw_section_header(c, y, "EQUIPMENT DISCOVERED")

    # We reconstruct equipment info from review results where possible.
    # Equipment-related results have check_category with the equipment type.
    categories = set()
    for r in results:
        if r.check_category:
            categories.add(r.check_category)

    # Group results to show a summary of what was checked
    category_counts = {}
    for r in results:
        cat = r.check_category or "Uncategorized"
        if cat not in category_counts:
            category_counts[cat] = {"total": 0, "passed": 0, "failed": 0, "review": 0}
        category_counts[cat]["total"] += 1
        if r.passed == 1:
            category_counts[cat]["passed"] += 1
        elif r.passed == 0:
            category_counts[cat]["failed"] += 1
        else:
            category_counts[cat]["review"] += 1

    if not category_counts:
        c.setFillColor(TEXT_MID)
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN_LEFT + 5, y - 5, "No equipment data available. Run a full review first.")
        return y - 25

    # Table header
    y -= 2
    col_x = [MARGIN_LEFT, MARGIN_LEFT + 200, MARGIN_LEFT + 270,
             MARGIN_LEFT + 330, MARGIN_LEFT + 390, MARGIN_LEFT + 450]

    c.setFillColor(DARK_BLUE)
    c.rect(MARGIN_LEFT - 5, y - 2, CONTENT_WIDTH + 10, 16, fill=True, stroke=False)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col_x[0], y + 3, "CHECK CATEGORY")
    c.drawString(col_x[1], y + 3, "TOTAL")
    c.drawString(col_x[2], y + 3, "PASSED")
    c.drawString(col_x[3], y + 3, "FAILED")
    c.drawString(col_x[4], y + 3, "REVIEW")
    y -= 16

    for i, (cat, counts) in enumerate(sorted(category_counts.items())):
        row_h = 14
        y = _check_page_break(c, y, row_h + 5)

        c.setFillColor(ROW_COLORS[i % 2])
        c.rect(MARGIN_LEFT - 5, y - 2, CONTENT_WIDTH + 10, row_h, fill=True, stroke=False)

        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 8)
        # Truncate long category names
        display_cat = cat[:35] + "..." if len(cat) > 38 else cat
        c.drawString(col_x[0], y + 2, display_cat)
        c.drawString(col_x[1], y + 2, str(counts["total"]))

        c.setFillColor(Color(0.13, 0.55, 0.13))
        c.drawString(col_x[2], y + 2, str(counts["passed"]))
        c.setFillColor(SEVERITY_COLORS["critical"])
        c.drawString(col_x[3], y + 2, str(counts["failed"]))
        c.setFillColor(Color(0.85, 0.45, 0.0))
        c.drawString(col_x[4], y + 2, str(counts["review"]))

        y -= row_h

    return y - 15


# ---------------------------------------------------------------------------
#  Findings by severity
# ---------------------------------------------------------------------------

def _draw_findings_by_severity(c, y: float, results: list, comments: list) -> float:
    """Draw all findings grouped and sorted by severity."""
    y = _check_page_break(c, y, 100)
    y = _draw_section_header(c, y, "FINDINGS BY SEVERITY")

    if not comments:
        c.setFillColor(TEXT_MID)
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN_LEFT + 5, y - 5, "No findings to report.")
        return y - 25

    # Sort comments: critical first, then major, minor, info
    severity_order = {"critical": 0, "major": 1, "minor": 2, "info": 3}
    sorted_comments = sorted(comments, key=lambda co: severity_order.get(co.severity, 4))

    current_severity = None
    finding_num = 0

    for co in sorted_comments:
        sev = co.severity or "info"

        # Severity group header
        if sev != current_severity:
            y = _check_page_break(c, y, 50)
            current_severity = sev
            y -= 8
            sev_color = SEVERITY_COLORS.get(sev, TEXT_MID)

            # Severity badge
            badge_w = 80
            c.setFillColor(sev_color)
            c.roundRect(MARGIN_LEFT, y - 2, badge_w, 16, 3, fill=True, stroke=False)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(MARGIN_LEFT + badge_w / 2, y + 2, sev.upper())
            y -= 22

        finding_num += 1

        # Estimate height needed for this finding
        text = co.comment_text or ""
        text_lines = _wrap_text(text, CONTENT_WIDTH - 30, 8.5)
        text_lines = text_lines[:6]  # Cap at 6 lines
        needed_h = 18 + len(text_lines) * 12 + 20

        y = _check_page_break(c, y, needed_h)

        # Finding background box
        bg_color = SEVERITY_BG.get(sev, LIGHT_BG)
        c.setFillColor(bg_color)
        box_h = needed_h - 5
        c.roundRect(MARGIN_LEFT, y - box_h + 14, CONTENT_WIDTH, box_h, 3,
                     fill=True, stroke=False)

        # Left severity stripe
        c.setFillColor(sev_color)
        c.rect(MARGIN_LEFT, y - box_h + 14, 4, box_h, fill=True, stroke=False)

        # Finding number and metadata
        fy = y
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(sev_color)
        c.drawString(MARGIN_LEFT + 12, fy, f"#{finding_num}")

        # Page number
        if co.page_number:
            c.setFillColor(TEXT_MID)
            c.setFont("Helvetica", 8)
            c.drawString(MARGIN_LEFT + 40, fy, f"Page {co.page_number}")

        # Category
        if co.category:
            c.drawString(MARGIN_LEFT + 100, fy, co.category)

        # Reference code
        if co.reference_code:
            c.setFillColor(DARK_BLUE)
            c.setFont("Helvetica-Bold", 8)
            c.drawRightString(W - MARGIN_RIGHT - 5, fy, co.reference_code)

        # Comment text
        fy -= 14
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 8.5)
        for line in text_lines:
            c.drawString(MARGIN_LEFT + 12, fy, line)
            fy -= 12

        y = fy - 8

    return y - 10


# ---------------------------------------------------------------------------
#  SLD-to-Schedule cross-check
# ---------------------------------------------------------------------------

def _draw_sld_crosscheck(c, y: float, results: list) -> float:
    """Draw SLD vs schedule cross-check results."""
    y = _check_page_break(c, y, 100)
    y = _draw_section_header(c, y, "SLD-TO-SCHEDULE CROSS-CHECK")

    sld_results = [
        r for r in results
        if r.check_category and (
            "sld" in r.check_category.lower()
            or "schedule" in r.check_category.lower()
            or "naming" in r.check_category.lower()
            or "cross-check" in r.check_category.lower()
        )
    ]

    if not sld_results:
        c.setFillColor(TEXT_MID)
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN_LEFT + 5, y - 5,
                     "No SLD-to-schedule cross-check data available.")
        return y - 25

    mismatches = [r for r in sld_results if r.passed != 1]
    matches = [r for r in sld_results if r.passed == 1]

    # Summary line
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_LEFT + 5, y - 5,
                 f"Total cross-checks: {len(sld_results)}  |  "
                 f"Matched: {len(matches)}  |  Mismatches: {len(mismatches)}")
    y -= 25

    if not mismatches:
        c.setFillColor(Color(0.13, 0.55, 0.13))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN_LEFT + 5, y, "All SLD-to-schedule cross-checks passed.")
        return y - 20

    # Table of mismatches
    y -= 2
    c.setFillColor(DARK_BLUE)
    c.rect(MARGIN_LEFT - 5, y - 2, CONTENT_WIDTH + 10, 16, fill=True, stroke=False)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN_LEFT, y + 3, "CHECK")
    c.drawString(MARGIN_LEFT + 250, y + 3, "STATUS")
    c.drawString(MARGIN_LEFT + 310, y + 3, "DETAILS")
    y -= 16

    for i, r in enumerate(mismatches):
        detail_lines = _wrap_text(r.details or "", CONTENT_WIDTH - 320, 7.5)
        detail_lines = detail_lines[:2]
        row_h = max(14, len(detail_lines) * 11 + 3)

        y = _check_page_break(c, y, row_h + 5)

        c.setFillColor(ROW_COLORS[i % 2])
        c.rect(MARGIN_LEFT - 5, y - row_h + 12, CONTENT_WIDTH + 10, row_h,
               fill=True, stroke=False)

        c.setFont("Helvetica", 7.5)
        c.setFillColor(TEXT_DARK)
        check_label = (r.check_name or "")[:42]
        c.drawString(MARGIN_LEFT, y, check_label)

        status_color = SEVERITY_COLORS["critical"] if r.passed == 0 else Color(0.85, 0.45, 0.0)
        c.setFillColor(status_color)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(MARGIN_LEFT + 250, y, "FAIL" if r.passed == 0 else "REVIEW")

        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 7)
        for j, dl in enumerate(detail_lines):
            c.drawString(MARGIN_LEFT + 310, y - j * 11, dl)

        y -= row_h

    return y - 15


# ---------------------------------------------------------------------------
#  Cross-reference findings
# ---------------------------------------------------------------------------

def _draw_cross_reference(c, y: float, results: list) -> float:
    """Draw cross-reference / topology / sizing findings."""
    y = _check_page_break(c, y, 100)
    y = _draw_section_header(c, y, "CROSS-REFERENCE FINDINGS")

    xref_results = [
        r for r in results
        if r.check_category and "cross-reference" in r.check_category.lower()
    ]

    if not xref_results:
        c.setFillColor(TEXT_MID)
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN_LEFT + 5, y - 5,
                     "No cross-reference findings available.")
        return y - 25

    xref_fail = [r for r in xref_results if r.passed != 1]
    xref_pass = [r for r in xref_results if r.passed == 1]

    # Summary
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN_LEFT + 5, y - 5,
                 f"Total cross-reference checks: {len(xref_results)}  |  "
                 f"Passed: {len(xref_pass)}  |  Issues: {len(xref_fail)}")
    y -= 25

    if not xref_fail:
        c.setFillColor(Color(0.13, 0.55, 0.13))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN_LEFT + 5, y, "All cross-reference checks passed.")
        return y - 20

    # List findings
    for i, r in enumerate(xref_fail):
        detail_text = r.details or r.check_name or ""
        ref = r.reference_standard or ""

        # Split details and recommendation if present
        parts = detail_text.split("| Recommendation:", 1)
        description = parts[0].strip()
        recommendation = parts[1].strip() if len(parts) > 1 else ""

        desc_lines = _wrap_text(description, CONTENT_WIDTH - 25, 8.5)
        desc_lines = desc_lines[:4]
        rec_lines = _wrap_text(recommendation, CONTENT_WIDTH - 40, 8) if recommendation else []
        rec_lines = rec_lines[:2]

        needed = 16 + len(desc_lines) * 12 + (len(rec_lines) * 11 + 14 if rec_lines else 0) + 10
        y = _check_page_break(c, y, needed)

        # Determine severity from finding_type in category
        finding_type = ""
        if r.check_category:
            finding_type = r.check_category.replace("Cross-Reference: ", "")

        is_fail = r.passed == 0
        sev_color = SEVERITY_COLORS["critical"] if is_fail else Color(0.85, 0.45, 0.0)
        bg_color = SEVERITY_BG["critical"] if is_fail else SEVERITY_BG["major"]

        # Background
        box_h = needed - 5
        c.setFillColor(bg_color)
        c.roundRect(MARGIN_LEFT, y - box_h + 14, CONTENT_WIDTH, box_h, 3,
                     fill=True, stroke=False)

        # Left stripe
        c.setFillColor(sev_color)
        c.rect(MARGIN_LEFT, y - box_h + 14, 4, box_h, fill=True, stroke=False)

        # Finding type tag
        fy = y
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(sev_color)
        c.drawString(MARGIN_LEFT + 12, fy, finding_type.upper())

        if ref:
            c.setFillColor(DARK_BLUE)
            c.drawRightString(W - MARGIN_RIGHT - 5, fy, ref)

        # Description
        fy -= 14
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 8.5)
        for dl in desc_lines:
            c.drawString(MARGIN_LEFT + 12, fy, dl)
            fy -= 12

        # Recommendation
        if rec_lines:
            fy -= 2
            c.setFillColor(DARK_BLUE)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(MARGIN_LEFT + 12, fy, "Recommendation:")
            fy -= 11
            c.setFillColor(TEXT_MID)
            c.setFont("Helvetica", 8)
            for rl in rec_lines:
                c.drawString(MARGIN_LEFT + 20, fy, rl)
                fy -= 11

        y = fy - 8

    return y - 10


# ---------------------------------------------------------------------------
#  Utility helpers
# ---------------------------------------------------------------------------

def _draw_section_header(c, y: float, title: str) -> float:
    """Draw a dark blue section header bar. Returns y after the header."""
    c.setFillColor(DARK_BLUE)
    c.rect(MARGIN_LEFT - 10, y - 4, CONTENT_WIDTH + 20, 22, fill=True, stroke=False)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN_LEFT, y + 2, title)
    return y - 26


def _check_page_break(c, y: float, needed: float) -> float:
    """If not enough room, start a new page. Returns y at top of content area."""
    if y - needed < BOTTOM_MARGIN:
        _draw_footer(c)
        c.showPage()
        return H - 40
    return y


def _draw_footer(c):
    """Draw page footer with branding."""
    c.setFillColor(TEXT_LIGHT)
    c.setFont("Helvetica", 7)
    c.drawString(MARGIN_LEFT, 25, "DC Submittal Review Platform — Automated Review Report")
    c.drawRightString(W - MARGIN_RIGHT, 25,
                      f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    # Thin line above footer
    c.setStrokeColor(BORDER_GRAY)
    c.setLineWidth(0.5)
    c.line(MARGIN_LEFT, 38, W - MARGIN_RIGHT, 38)


def _info_line(c, x: float, y: float, label: str, value: str):
    """Draw a label: value pair."""
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(TEXT_MID)
    c.drawString(x, y, label)
    c.setFont("Helvetica", 10)
    c.setFillColor(TEXT_DARK)
    label_width = len(label) * 6.2 + 8
    c.drawString(x + label_width, y, value)


def _wrap_text(text: str, max_width: float, font_size: float) -> list[str]:
    """Wrap text to fit within max_width at given font size."""
    chars_per_line = int(max_width / (font_size * 0.48))
    if chars_per_line < 10:
        chars_per_line = 10
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
