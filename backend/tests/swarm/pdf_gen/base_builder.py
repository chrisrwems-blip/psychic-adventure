"""ReportLab PDF builder for generating test submittals.

Produces text-layer PDFs that PyPDF2 can extract. Visual fidelity is irrelevant —
only the text content matters for the review engine.
"""
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 50
TOP_MARGIN = PAGE_HEIGHT - 50
LINE_HEIGHT = 14
FONT_NAME = "Courier"
FONT_SIZE = 9


class SubmittalBuilder:
    """Accumulates pages of text and writes them to a PDF file."""

    def __init__(self):
        self._pages: list[tuple[str, list[str]]] = []  # (header, lines)

    def add_sld_page(self, panel_name: str, lines: list[str]):
        header = f"SINGLE LINE DIAGRAM - {panel_name}"
        self._pages.append((header, lines))

    def add_schedule_page(self, panel_name: str, lines: list[str]):
        header = f"PANEL SCHEDULE - {panel_name} BREAKER DETAILS"
        self._pages.append((header, lines))

    def add_equipment_page(self, lines: list[str]):
        header = "EQUIPMENT SCHEDULE"
        self._pages.append((header, lines))

    def add_cable_page(self, lines: list[str]):
        header = "CABLE SCHEDULE"
        self._pages.append((header, lines))

    def add_general_notes_page(self, lines: list[str]):
        header = "GENERAL NOTES"
        self._pages.append((header, lines))

    def add_raw_page(self, header: str, lines: list[str]):
        self._pages.append((header, lines))

    def build(self, output_path: str):
        """Write all pages to a PDF file at output_path."""
        c = canvas.Canvas(output_path, pagesize=letter)

        for header, lines in self._pages:
            self._write_page(c, header, lines)
            c.showPage()

        c.save()

    def _write_page(self, c: canvas.Canvas, header: str, lines: list[str]):
        c.setFont(FONT_NAME, FONT_SIZE + 2)
        y = TOP_MARGIN
        c.drawString(LEFT_MARGIN, y, header)
        y -= LINE_HEIGHT * 2

        c.setFont(FONT_NAME, FONT_SIZE)
        for line in lines:
            if y < 50:
                c.showPage()
                c.setFont(FONT_NAME, FONT_SIZE)
                y = TOP_MARGIN
            c.drawString(LEFT_MARGIN, y, line)
            y -= LINE_HEIGHT
