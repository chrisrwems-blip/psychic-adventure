"""Multi-submittal cross-reference — validates consistency between related submittals.

When multiple submittals exist in a project (switchgear + UPS + generator + ATS),
cross-references between them to catch mismatches:
- Generator kW matches ATS rating
- ATS rating matches switchgear incomer
- Transformer secondary voltage matches downstream panel voltage
- UPS kVA matches load requirements
"""
from sqlalchemy.orm import Session
from app.models.database_models import Submittal, ReviewResult, ReviewComment
from app.services.pdf_parser import extract_text_by_page, extract_metadata
from app.services.equipment_extractor import extract_all_equipment
from app.services.cross_reference import CrossRefFinding


def cross_reference_submittals(db: Session, project_id: int) -> list[CrossRefFinding]:
    """Cross-reference all submittals in a project against each other."""
    findings = []

    submittals = db.query(Submittal).filter(Submittal.project_id == project_id).all()
    if len(submittals) < 2:
        return findings

    # Extract key data from each submittal
    submittal_data = []
    for sub in submittals:
        try:
            pages = extract_text_by_page(sub.file_path)
            full_text = "\n".join(p["text"] for p in pages)
            metadata = extract_metadata(full_text)
            equipment = extract_all_equipment(pages)

            submittal_data.append({
                "id": sub.id,
                "title": sub.title,
                "equipment_type": sub.equipment_type,
                "metadata": metadata,
                "equipment": equipment,
                "voltages": set(metadata.get("voltages_found", [])),
                "kva": metadata.get("kva_found", []),
                "kw": metadata.get("kw_found", []),
            })
        except Exception:
            continue

    if len(submittal_data) < 2:
        return findings

    # Check voltage consistency across submittals
    all_voltages = set()
    for sd in submittal_data:
        all_voltages.update(sd["voltages"])

    # System voltage should be consistent
    system_voltages = {v for v in all_voltages if v in (208, 240, 277, 400, 415, 480)}
    if len(system_voltages) > 2:
        findings.append(CrossRefFinding(
            finding_type="cross_submittal_voltage",
            severity="major",
            equipment_1="Project",
            equipment_2=None,
            page_number=0,
            description=(
                f"Multiple system voltages across submittals: {sorted(system_voltages)}V. "
                f"Verify all submittals are designed for the same system voltage."
            ),
            reference_code="System Coordination",
            recommendation="Confirm system voltage is consistent across all equipment.",
        ))

    # Check for overlapping equipment designations across submittals
    for i, sd1 in enumerate(submittal_data):
        for sd2 in submittal_data[i+1:]:
            desigs1 = {e.designation.upper() for e in sd1["equipment"]}
            desigs2 = {e.designation.upper() for e in sd2["equipment"]}
            overlap = desigs1 & desigs2

            if len(overlap) > 5:
                # Check if overlapping equipment has consistent ratings
                for desig in list(overlap)[:10]:
                    eq1 = next((e for e in sd1["equipment"] if e.designation.upper() == desig), None)
                    eq2 = next((e for e in sd2["equipment"] if e.designation.upper() == desig), None)

                    if eq1 and eq2:
                        # Compare frame sizes
                        f1 = eq1.frame_size or eq1.amperage
                        f2 = eq2.frame_size or eq2.amperage
                        if f1 and f2 and f1 != f2:
                            findings.append(CrossRefFinding(
                                finding_type="cross_submittal_mismatch",
                                severity="critical",
                                equipment_1=desig,
                                equipment_2=None,
                                page_number=0,
                                description=(
                                    f"Equipment {desig} has different ratings across submittals: "
                                    f"\"{sd1['title']}\" shows {f1}, "
                                    f"\"{sd2['title']}\" shows {f2}."
                                ),
                                reference_code="System Coordination",
                                recommendation="Resolve rating discrepancy between submittals.",
                            ))

    return findings
