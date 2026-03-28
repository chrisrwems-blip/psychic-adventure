"""Spec document validator — cross-references submittal against project specification.

Upload a Division 26 specification PDF. The tool extracts requirements and
validates the submittal against them. Flags deviations, missing items, and
"or equal" substitutions.
"""
import re
from dataclasses import dataclass
from typing import Optional

from .pdf_parser import extract_text_by_page
from .cross_reference import CrossRefFinding


@dataclass
class SpecRequirement:
    """A single requirement extracted from the specification."""
    section: str       # e.g., "26 24 16"
    paragraph: str     # e.g., "2.A.3"
    requirement_type: str  # "manufacturer", "product", "standard", "feature", "performance"
    text: str
    page_number: int


def extract_spec_requirements(spec_file_path: str) -> list[SpecRequirement]:
    """Extract requirements from a Division 26 specification PDF."""
    pages = extract_text_by_page(spec_file_path)
    requirements = []
    current_section = ""

    for page_data in pages:
        text = page_data["text"]
        text_lower = text.lower()
        page_num = page_data["page"]

        # Detect section numbers: "SECTION 26 24 16" or "26 24 16"
        section_match = re.search(r'(?:section\s+)?(\d{2}\s+\d{2}\s+\d{2})', text_lower)
        if section_match:
            current_section = section_match.group(1).strip()

        # Extract manufacturer requirements: "Manufacturer: ABB, Eaton, or approved equal"
        for match in re.finditer(r'(?:manufacturer|acceptable\s+manufacturer)s?\s*[:=]\s*(.+?)(?:\n|\.)', text, re.IGNORECASE):
            requirements.append(SpecRequirement(
                section=current_section,
                paragraph="",
                requirement_type="manufacturer",
                text=match.group(1).strip(),
                page_number=page_num,
            ))

        # Extract product requirements: "Product: ABB Emax 2 E-series"
        for match in re.finditer(r'(?:product|model|catalog)s?\s*[:=]\s*(.+?)(?:\n|\.)', text, re.IGNORECASE):
            requirements.append(SpecRequirement(
                section=current_section,
                paragraph="",
                requirement_type="product",
                text=match.group(1).strip(),
                page_number=page_num,
            ))

        # Extract "shall" requirements
        for match in re.finditer(r'([^.]*\bshall\b[^.]*\.)', text, re.IGNORECASE):
            req_text = match.group(1).strip()
            if len(req_text) > 20 and len(req_text) < 500:
                # Classify the requirement
                req_type = "feature"
                if any(kw in req_text.lower() for kw in ["ul listed", "ul 489", "ul 1558", "listed", "labeled"]):
                    req_type = "standard"
                elif any(kw in req_text.lower() for kw in ["kva", "kw", "amp", "volt", "kaic"]):
                    req_type = "performance"

                requirements.append(SpecRequirement(
                    section=current_section,
                    paragraph="",
                    requirement_type=req_type,
                    text=req_text,
                    page_number=page_num,
                ))

        # Extract "or equal" / "or approved equal" references
        for match in re.finditer(r'(\w[\w\s-]+)\s+or\s+(?:approved\s+)?equal', text, re.IGNORECASE):
            requirements.append(SpecRequirement(
                section=current_section,
                paragraph="",
                requirement_type="manufacturer",
                text=f"{match.group(1).strip()} or approved equal",
                page_number=page_num,
            ))

    return requirements


def validate_submittal_against_spec(
    spec_requirements: list[SpecRequirement],
    submittal_pages: list[dict],
    equipment: list,
) -> list[CrossRefFinding]:
    """Compare submittal content against spec requirements."""
    findings = []
    full_text = "\n".join(p.get("text_lower", "") for p in submittal_pages)

    for req in spec_requirements:
        if req.requirement_type == "manufacturer":
            # Check if specified manufacturer is present in submittal
            manufacturers = re.findall(r'\b(\w{3,})\b', req.text.lower())
            found_any = any(m in full_text for m in manufacturers if len(m) > 3)

            if not found_any and len(manufacturers) > 0:
                findings.append(CrossRefFinding(
                    finding_type="spec_manufacturer_mismatch",
                    severity="major",
                    equipment_1=f"Spec Section {req.section}",
                    equipment_2=None,
                    page_number=req.page_number,
                    description=(
                        f"Spec requires: \"{req.text}\". "
                        f"None of the specified manufacturers found in submittal. "
                        f"If substituting, provide \"or equal\" documentation."
                    ),
                    reference_code=f"Spec Section {req.section}",
                    recommendation="Verify submittal matches specified manufacturer or submit substitution request.",
                ))

        elif req.requirement_type == "standard":
            # Check if referenced standard is addressed
            keywords = re.findall(r'\b(ul\s*\d+|ieee\s*\d+|nfpa\s*\d+|astm\s*\w+)\b', req.text.lower())
            for kw in keywords:
                if kw not in full_text:
                    findings.append(CrossRefFinding(
                        finding_type="spec_standard_missing",
                        severity="major",
                        equipment_1=f"Spec Section {req.section}",
                        equipment_2=None,
                        page_number=req.page_number,
                        description=(
                            f"Spec requires compliance with {kw.upper()}. "
                            f"This standard is not referenced in the submittal."
                        ),
                        reference_code=f"Spec Section {req.section}",
                        recommendation=f"Verify submittal demonstrates compliance with {kw.upper()}.",
                    ))

        elif req.requirement_type == "performance":
            # Check if performance values are present
            values = re.findall(r'(\d+)\s*(kva|kw|amp|volt|kaic|ka)', req.text.lower())
            for val, unit in values:
                if f"{val}" not in full_text:
                    findings.append(CrossRefFinding(
                        finding_type="spec_performance_gap",
                        severity="major",
                        equipment_1=f"Spec Section {req.section}",
                        equipment_2=None,
                        page_number=req.page_number,
                        description=(
                            f"Spec requires {val} {unit}. "
                            f"This value not confirmed in submittal."
                        ),
                        reference_code=f"Spec Section {req.section}",
                        recommendation=f"Verify submittal meets spec requirement of {val} {unit}.",
                    ))

    return findings
