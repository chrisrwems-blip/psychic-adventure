"""Page classifier — identifies what type of content is on each page of a submittal."""
import re
from typing import Optional


class PageType:
    SLD = "single_line_diagram"
    PANEL_SCHEDULE = "panel_schedule"
    EQUIPMENT_SCHEDULE = "equipment_schedule"
    CUT_SHEET = "cut_sheet"
    SPEC_SECTION = "specification"
    CABLE_SCHEDULE = "cable_schedule"
    LOAD_SCHEDULE = "load_schedule"
    RISER_DIAGRAM = "riser_diagram"
    PLAN_DRAWING = "plan_drawing"
    COVER_SHEET = "cover_sheet"
    TABLE_OF_CONTENTS = "table_of_contents"
    GENERAL_NOTES = "general_notes"
    UNKNOWN = "unknown"


# Keywords strongly associated with each page type
PAGE_SIGNATURES = {
    PageType.SLD: {
        "strong": ["single line", "one line", "one-line", "single-line", "sld", "1-line"],
        "moderate": ["main breaker", "tie breaker", "bus section", "switchgear", "mcc ",
                      "switchboard", "normal source", "emergency source", "utility feed",
                      "generator feed", "ats", "transfer switch"],
        "threshold": 1,  # 1 strong OR 3+ moderate
    },
    PageType.PANEL_SCHEDULE: {
        "strong": ["panel schedule", "panelboard schedule", "circuit breaker schedule",
                    "branch circuit", "panel designation"],
        "moderate": ["ckt", "circuit", "trip", "frame", "pole", "wire size", "wire #",
                      "neutral", "phase a", "phase b", "phase c", "va ", " amp",
                      "20a", "30a", "40a", "50a", "60a", "100a", "15a"],
        "threshold": 1,
    },
    PageType.EQUIPMENT_SCHEDULE: {
        "strong": ["equipment schedule", "transformer schedule", "motor schedule",
                    "generator schedule", "ups schedule", "ats schedule"],
        "moderate": ["schedule", "qty", "quantity", "hp ", "kva ", "voltage",
                      "manufacturer", "model no", "catalog no"],
        "threshold": 1,
    },
    PageType.CUT_SHEET: {
        "strong": ["product data", "cut sheet", "catalog data", "submittal data",
                    "technical data", "data sheet", "specification sheet"],
        "moderate": ["features", "ordering information", "catalog number",
                      "dimensions", "weight", "ratings", "certifications",
                      "ul listed", "nema", "approvals"],
        "threshold": 1,
    },
    PageType.SPEC_SECTION: {
        "strong": ["section 26", "division 26", "part 1", "part 2", "part 3",
                    "spec section"],
        "moderate": ["submittals", "quality assurance", "delivery", "storage",
                      "warranty", "products", "execution", "manufacturers",
                      "acceptable products"],
        "threshold": 1,
    },
    PageType.CABLE_SCHEDULE: {
        "strong": ["cable schedule", "conductor schedule", "wire schedule",
                    "conduit schedule", "raceway schedule"],
        "moderate": ["from", "to ", "wire size", "conduit size", "length",
                      "awg", "kcmil", "thhn", "xhhw", "mc cable"],
        "threshold": 1,
    },
    PageType.LOAD_SCHEDULE: {
        "strong": ["load schedule", "load summary", "load calculation",
                    "demand load", "connected load"],
        "moderate": ["total load", "demand factor", "kva", "kw ", "amps",
                      "power factor", "diversity"],
        "threshold": 1,
    },
    PageType.RISER_DIAGRAM: {
        "strong": ["riser diagram", "riser schedule", "electrical riser",
                    "power riser"],
        "moderate": ["floor", "level", "mains", "feeder", "distribution"],
        "threshold": 1,
    },
    PageType.PLAN_DRAWING: {
        "strong": ["floor plan", "electrical plan", "power plan", "lighting plan",
                    "receptacle plan"],
        "moderate": ["plan ", "layout", "north", "scale:", "detail"],
        "threshold": 1,
    },
    PageType.COVER_SHEET: {
        "strong": ["cover sheet", "title sheet", "submittal transmittal"],
        "moderate": ["project name", "project number", "submitted by",
                      "date submitted", "revision", "approval"],
        "threshold": 1,
    },
    PageType.TABLE_OF_CONTENTS: {
        "strong": ["table of contents", "index"],
        "moderate": ["page ", "section ", "appendix"],
        "threshold": 1,
    },
    PageType.GENERAL_NOTES: {
        "strong": ["general notes", "electrical notes", "code references"],
        "moderate": ["nec ", "nfpa", "note:", "reference:"],
        "threshold": 1,
    },
}


def classify_page(text: str) -> dict:
    """Classify a single page's content type and confidence.

    Returns: {"type": PageType, "confidence": float, "scores": dict}
    """
    text_lower = text.lower()
    scores = {}

    for page_type, signatures in PAGE_SIGNATURES.items():
        strong_matches = sum(1 for kw in signatures["strong"] if kw in text_lower)
        moderate_matches = sum(1 for kw in signatures["moderate"] if kw in text_lower)

        # Score: strong matches worth 3, moderate worth 1
        score = strong_matches * 3 + moderate_matches
        scores[page_type] = score

    if not scores or max(scores.values()) == 0:
        return {"type": PageType.UNKNOWN, "confidence": 0.0, "scores": scores}

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    total_score = sum(scores.values())
    confidence = best_score / total_score if total_score > 0 else 0

    # Minimum score threshold
    if best_score < 2:
        return {"type": PageType.UNKNOWN, "confidence": 0.0, "scores": scores}

    return {"type": best_type, "confidence": round(confidence, 2), "scores": scores}


def classify_all_pages(pages: list[dict]) -> list[dict]:
    """Classify every page in the submittal.

    Takes output from extract_text_by_page.
    Adds 'page_type' and 'type_confidence' to each page dict.
    """
    for page_data in pages:
        result = classify_page(page_data["text"])
        page_data["page_type"] = result["type"]
        page_data["type_confidence"] = result["confidence"]

    return pages


def get_pages_of_type(pages: list[dict], page_type: str) -> list[dict]:
    """Filter pages to only those of a specific type."""
    return [p for p in pages if p.get("page_type") == page_type]


def get_page_summary(pages: list[dict]) -> dict:
    """Get a summary of how many pages of each type were found."""
    summary = {}
    for p in pages:
        pt = p.get("page_type", PageType.UNKNOWN)
        summary[pt] = summary.get(pt, 0) + 1
    return summary
