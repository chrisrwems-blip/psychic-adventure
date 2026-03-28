"""Revision comparison service — compares two versions of a submittal (Rev A vs Rev B).

Extracts text and equipment from both PDFs, then identifies:
- New equipment added in the revision
- Equipment removed from the original
- Changed ratings (same Q-designation, different specs)
- Pages with significantly different text content
"""
import difflib
from dataclasses import dataclass, asdict
from typing import Optional

from app.services.pdf_parser import extract_text_by_page
from app.services.equipment_extractor import extract_all_equipment, ExtractedEquipment
from app.services.page_classifier import classify_all_pages


@dataclass
class RevisionChange:
    """A single change between two revisions."""
    change_type: str  # "added", "removed", "modified", "rating_changed"
    equipment_id: str  # Q-designation or page reference
    page_old: Optional[int]
    page_new: Optional[int]
    description: str  # Human-readable description of the change
    old_value: Optional[str]
    new_value: Optional[str]


# Fields on ExtractedEquipment that represent ratings worth comparing
_RATING_FIELDS = [
    ("frame_size", "Frame size"),
    ("trip_rating", "Trip rating"),
    ("interrupting_rating", "kAIC rating"),
    ("amperage", "Amperage"),
    ("voltage", "Voltage"),
    ("kva", "kVA"),
    ("kw", "kW"),
    ("model", "Model"),
    ("impedance", "Impedance"),
    ("phases", "Phases"),
]

# Threshold for considering a page's text "significantly changed"
_TEXT_CHANGE_THRESHOLD = 0.85


def _build_equipment_map(equipment_list: list[ExtractedEquipment]) -> dict[str, ExtractedEquipment]:
    """Build a lookup from designation to equipment.

    If the same designation appears on multiple pages, keep the one with the
    most populated fields (richest data).
    """
    equip_map: dict[str, ExtractedEquipment] = {}
    for eq in equipment_list:
        key = eq.designation.strip().upper()
        if not key or key == "UNKNOWN":
            continue
        if key in equip_map:
            # Keep the entry with more populated rating fields
            existing_count = sum(1 for f, _ in _RATING_FIELDS if getattr(equip_map[key], f))
            new_count = sum(1 for f, _ in _RATING_FIELDS if getattr(eq, f))
            if new_count > existing_count:
                equip_map[key] = eq
        else:
            equip_map[key] = eq
    return equip_map


def _compare_equipment(old_map: dict[str, ExtractedEquipment],
                       new_map: dict[str, ExtractedEquipment]) -> list[RevisionChange]:
    """Compare equipment between two revisions."""
    changes: list[RevisionChange] = []

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    # New equipment in Rev B
    for key in sorted(new_keys - old_keys):
        eq = new_map[key]
        desc_parts = [eq.equipment_type]
        if eq.frame_size:
            desc_parts.append(f"frame {eq.frame_size}")
        if eq.trip_rating:
            desc_parts.append(f"trip {eq.trip_rating}")
        if eq.amperage:
            desc_parts.append(f"{eq.amperage}A")
        changes.append(RevisionChange(
            change_type="added",
            equipment_id=eq.designation,
            page_old=None,
            page_new=eq.page_number,
            description=f"New equipment added: {eq.designation} ({', '.join(desc_parts)})",
            old_value=None,
            new_value=f"{eq.equipment_type} on page {eq.page_number}",
        ))

    # Removed equipment from Rev A
    for key in sorted(old_keys - new_keys):
        eq = old_map[key]
        desc_parts = [eq.equipment_type]
        if eq.frame_size:
            desc_parts.append(f"frame {eq.frame_size}")
        if eq.trip_rating:
            desc_parts.append(f"trip {eq.trip_rating}")
        changes.append(RevisionChange(
            change_type="removed",
            equipment_id=eq.designation,
            page_old=eq.page_number,
            page_new=None,
            description=f"Equipment removed: {eq.designation} ({', '.join(desc_parts)})",
            old_value=f"{eq.equipment_type} on page {eq.page_number}",
            new_value=None,
        ))

    # Changed ratings on common equipment
    for key in sorted(old_keys & new_keys):
        old_eq = old_map[key]
        new_eq = new_map[key]
        rating_diffs = []

        for field_name, label in _RATING_FIELDS:
            old_val = getattr(old_eq, field_name) or ""
            new_val = getattr(new_eq, field_name) or ""
            old_val_s = str(old_val).strip()
            new_val_s = str(new_val).strip()
            if old_val_s != new_val_s and (old_val_s or new_val_s):
                rating_diffs.append((label, old_val_s, new_val_s))

        if rating_diffs:
            diff_descriptions = []
            for label, ov, nv in rating_diffs:
                if ov and nv:
                    diff_descriptions.append(f"{label}: {ov} -> {nv}")
                elif nv:
                    diff_descriptions.append(f"{label}: (none) -> {nv}")
                else:
                    diff_descriptions.append(f"{label}: {ov} -> (removed)")

            changes.append(RevisionChange(
                change_type="rating_changed",
                equipment_id=old_eq.designation,
                page_old=old_eq.page_number,
                page_new=new_eq.page_number,
                description=f"Rating changed on {old_eq.designation}: {'; '.join(diff_descriptions)}",
                old_value=", ".join(f"{l}: {o}" for l, o, _ in rating_diffs if o),
                new_value=", ".join(f"{l}: {n}" for l, _, n in rating_diffs if n),
            ))

    return changes


def _compare_text(old_pages: list[dict], new_pages: list[dict]) -> list[RevisionChange]:
    """Find pages with significantly different text content."""
    changes: list[RevisionChange] = []

    max_pages = max(len(old_pages), len(new_pages))

    for i in range(max_pages):
        old_text = old_pages[i]["text"] if i < len(old_pages) else ""
        new_text = new_pages[i]["text"] if i < len(new_pages) else ""

        # Skip pages with negligible text on both sides
        if len(old_text.strip()) < 30 and len(new_text.strip()) < 30:
            continue

        # Page added in revision
        if i >= len(old_pages):
            page_num = i + 1
            preview = new_text[:120].replace("\n", " ").strip()
            changes.append(RevisionChange(
                change_type="added",
                equipment_id=f"Page {page_num}",
                page_old=None,
                page_new=page_num,
                description=f"New page {page_num} added in revision: {preview}...",
                old_value=None,
                new_value=f"{len(new_text)} chars",
            ))
            continue

        # Page removed in revision
        if i >= len(new_pages):
            page_num = i + 1
            preview = old_text[:120].replace("\n", " ").strip()
            changes.append(RevisionChange(
                change_type="removed",
                equipment_id=f"Page {page_num}",
                page_old=page_num,
                page_new=None,
                description=f"Page {page_num} removed in revision: {preview}...",
                old_value=f"{len(old_text)} chars",
                new_value=None,
            ))
            continue

        # Both pages exist — compare similarity
        ratio = difflib.SequenceMatcher(None, old_text, new_text).ratio()
        if ratio < _TEXT_CHANGE_THRESHOLD:
            page_num = i + 1
            change_pct = round((1 - ratio) * 100, 1)
            changes.append(RevisionChange(
                change_type="modified",
                equipment_id=f"Page {page_num}",
                page_old=page_num,
                page_new=page_num,
                description=f"Page {page_num} text changed ({change_pct}% different)",
                old_value=f"{len(old_text)} chars",
                new_value=f"{len(new_text)} chars",
            ))

    return changes


def _extract_and_classify(file_path: str) -> tuple[list[dict], list[ExtractedEquipment]]:
    """Extract text by page, classify pages, and extract equipment."""
    pages = extract_text_by_page(file_path)
    pages = classify_all_pages(pages)
    equipment = extract_all_equipment(pages)
    return pages, equipment


def compare_revisions(old_file: str, new_file: str) -> dict:
    """Compare two revisions of a submittal PDF.

    Args:
        old_file: Path to the original (Rev A) PDF.
        new_file: Path to the revision (Rev B) PDF.

    Returns:
        {
            "changes": [RevisionChange as dict, ...],
            "summary": {
                "total_changes": int,
                "equipment_added": int,
                "equipment_removed": int,
                "ratings_changed": int,
                "pages_modified": int,
                "old_page_count": int,
                "new_page_count": int,
                "old_equipment_count": int,
                "new_equipment_count": int,
            }
        }
    """
    old_pages, old_equipment = _extract_and_classify(old_file)
    new_pages, new_equipment = _extract_and_classify(new_file)

    old_map = _build_equipment_map(old_equipment)
    new_map = _build_equipment_map(new_equipment)

    equipment_changes = _compare_equipment(old_map, new_map)
    text_changes = _compare_text(old_pages, new_pages)

    # Deduplicate: don't report text changes for pages that already have equipment
    # changes, to keep the output focused.
    equipment_pages_old = {c.page_old for c in equipment_changes if c.page_old}
    equipment_pages_new = {c.page_new for c in equipment_changes if c.page_new}
    filtered_text_changes = [
        c for c in text_changes
        if c.page_old not in equipment_pages_old and c.page_new not in equipment_pages_new
    ]

    all_changes = equipment_changes + filtered_text_changes

    summary = {
        "total_changes": len(all_changes),
        "equipment_added": sum(1 for c in equipment_changes if c.change_type == "added"),
        "equipment_removed": sum(1 for c in equipment_changes if c.change_type == "removed"),
        "ratings_changed": sum(1 for c in equipment_changes if c.change_type == "rating_changed"),
        "pages_modified": len(filtered_text_changes),
        "old_page_count": len(old_pages),
        "new_page_count": len(new_pages),
        "old_equipment_count": len(old_equipment),
        "new_equipment_count": len(new_equipment),
    }

    return {
        "changes": [asdict(c) for c in all_changes],
        "summary": summary,
    }
