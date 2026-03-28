"""PDF text extraction and basic data identification."""
import re
from typing import Optional


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF file using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        return f"[PDF text extraction failed: {e}]"


def extract_text_by_page(file_path: str) -> list[dict]:
    """Extract text from each page separately.

    Returns a list of dicts: [{"page": 1, "text": "...", "text_lower": "..."}, ...]
    Page numbers are 1-indexed to match PDF page numbering.
    """
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({
                "page": i + 1,  # 1-indexed
                "text": text,
                "text_lower": text.lower(),
            })
        return pages
    except Exception as e:
        return [{"page": 1, "text": f"[PDF extraction failed: {e}]", "text_lower": ""}]


def get_page_count(file_path: str) -> int:
    """Get the number of pages in a PDF."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        return len(reader.pages)
    except Exception:
        return 0


def extract_metadata(text: str) -> dict:
    """Extract structured metadata from PDF text for review engine."""
    text_lower = text.lower()
    metadata = {}

    # Voltage
    voltages = re.findall(r'(\d{3,5})\s*(?:v(?:ac|dc)?|volt)', text_lower)
    if voltages:
        metadata["voltages_found"] = [int(v) for v in voltages]

    # Current/Amperage
    amps = re.findall(r'(\d{2,5})\s*(?:a(?:mp)?s?\b)', text_lower)
    if amps:
        metadata["amperage_found"] = [int(a) for a in amps]

    # Power ratings
    kva = re.findall(r'(\d{2,5})\s*kva', text_lower)
    kw = re.findall(r'(\d{2,5})\s*kw', text_lower)
    if kva:
        metadata["kva_found"] = [int(k) for k in kva]
    if kw:
        metadata["kw_found"] = [int(k) for k in kw]

    # Frequency
    if "60 hz" in text_lower or "60hz" in text_lower:
        metadata["frequency"] = 60
    elif "50 hz" in text_lower or "50hz" in text_lower:
        metadata["frequency"] = 50

    # Manufacturer hints
    manufacturers = [
        "eaton", "schneider", "siemens", "abb", "ge", "square d",
        "cutler-hammer", "mitsubishi", "caterpillar", "cummins",
        "kohler", "generac", "mtu", "liebert", "vertiv", "apc",
        "starline", "raritan", "servertech", "cyber power",
        "pdu", "legrand", "hubbell", "chatsworth"
    ]
    for mfr in manufacturers:
        if mfr in text_lower:
            metadata.setdefault("manufacturers", []).append(mfr)

    # Standards referenced
    standards = re.findall(r'(?:nec|nfpa|ieee|ul|ansi|iec)\s*[\d.]+', text_lower)
    if standards:
        metadata["standards_referenced"] = list(set(standards))

    return metadata


def extract_metadata_by_page(pages: list[dict]) -> list[dict]:
    """Extract metadata for each page individually.

    Takes output of extract_text_by_page, returns same list with 'metadata' added.
    """
    for page_data in pages:
        page_data["metadata"] = extract_metadata(page_data["text"])
    return pages
