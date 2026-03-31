"""Model vs Checklist — side-by-side comparison on the real Leviathan MDB.

Runs both approaches on the same document and compares:
- How many findings each produces
- Signal-to-noise ratio
- Which real issues each catches
"""
import os
import pytest

from tests.swarm.pdf_gen.base_builder import SubmittalBuilder
from tests.swarm.conftest import run_review_pipeline

from app.services.pdf_parser import extract_text_by_page, extract_metadata_by_page, extract_metadata
from app.services.page_classifier import classify_all_pages, get_page_summary
from app.services.equipment_extractor import extract_all_equipment
from app.services.topology import build_topology
from app.services.jurisdiction import detect_jurisdiction
from app.services.system_model import build_system_model, check_model


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")


def _load_text(filename):
    with open(os.path.join(TEST_DATA_DIR, filename)) as f:
        return f.read()


def _build_pdf(tmpdir, header, text, filename="model_test.pdf"):
    pdf_path = os.path.join(tmpdir, filename)
    builder = SubmittalBuilder()
    builder.add_raw_page(header, text.strip().split("\n"))
    builder.build(pdf_path)
    return pdf_path


def _run_model_pipeline(pdf_path):
    """Run extraction + model building + model checks."""
    pages = extract_text_by_page(pdf_path)
    pages = extract_metadata_by_page(pages)
    pages = classify_all_pages(pages)
    page_summary = get_page_summary(pages)

    full_text = "\n".join(p["text"] for p in pages)
    global_metadata = extract_metadata(full_text)

    equipment = extract_all_equipment(pages)
    topology = build_topology(equipment, pages)
    jurisdiction = detect_jurisdiction(pages, global_metadata)

    model = build_system_model(
        equipment=equipment,
        topology=topology,
        pages=pages,
        page_summary=page_summary,
        jurisdiction_result=jurisdiction,
        global_metadata=global_metadata,
    )

    findings = check_model(model)

    return model, findings


class TestModelVsChecklist:

    def test_side_by_side_leviathan_mdb(self, tmp_pdf_dir):
        """Run both approaches on the real Leviathan MDB and compare."""
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf(tmp_pdf_dir,
                         "SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)

        # --- Checklist approach ---
        checklist_results = run_review_pipeline(pdf)
        checklist_critical = sum(
            1 for f in checklist_results["checklist_findings"]
            if f.passed != 1 and f.severity == "critical"
        )
        checklist_major = sum(
            1 for f in checklist_results["checklist_findings"]
            if f.passed != 1 and f.severity == "major"
        )
        checklist_total = checklist_critical + checklist_major
        # Add xref findings
        xref_total = len(checklist_results["xref_findings"])

        # --- Model approach ---
        model, model_findings = _run_model_pipeline(pdf)
        model_critical = sum(1 for f in model_findings if f.severity == "critical")
        model_major = sum(1 for f in model_findings if f.severity == "major")
        model_total = len(model_findings)

        print("\n")
        print("=" * 100)
        print("  MODEL vs CHECKLIST — Armada Leviathan MDB")
        print("=" * 100)

        print("\n  SYSTEM MODEL:")
        print(f"    Document scope: {model.document_scope}")
        print(f"    System voltage: {model.system_voltage or 'NOT STATED'}")
        print(f"    Jurisdiction: {model.jurisdiction} ({model.jurisdiction_confidence:.0%})")
        print(f"    Service entrances: {len(model.service_entrances)}")
        print(f"    Breakers: {len(model.breakers)}")
        print(f"    Transformers: {len(model.transformers)}")
        print(f"    Cables: {len(model.cables)}")
        print(f"    Unconfirmed items: {model.unconfirmed_items}")

        print(f"\n  CHECKLIST APPROACH:")
        print(f"    Checklist findings: {checklist_critical} critical + {checklist_major} major = {checklist_total}")
        print(f"    Cross-ref findings: {xref_total}")
        print(f"    TOTAL: {checklist_total + xref_total}")

        print(f"\n  MODEL APPROACH:")
        print(f"    Model findings: {model_critical} critical + {model_major} major = {model_total}")

        print(f"\n  NOISE REDUCTION: {checklist_total + xref_total} → {model_total} "
              f"({(1 - model_total / max(checklist_total + xref_total, 1)) * 100:.0f}% reduction)")

        print(f"\n  --- MODEL FINDINGS (all of them) ---")
        for f in model_findings:
            print(f"    [{f.severity.upper()}] {f.check_id}: {f.description[:120]}")
            if f.reference:
                print(f"             Ref: {f.reference}")

        print("\n  --- ENGINEERING GROUND TRUTH ---")
        ground_truth = [
            ("No kAIC/SCCR on breakers", "NEC 110.9"),
            ("No GFP on 4000A service", "NEC 230.95"),
            ("No arc flash analysis", "NFPA 70E / IEEE 1584"),
            ("No voltage label", "NEC 408.4"),
            ("Interlocking TBC", "Submittal Requirements"),
            ("No AFC labeling", "NEC 110.24"),
            ("1600A+ breakers need arc energy reduction", "NEC 240.87"),
        ]

        model_text = " ".join(f.description.lower() for f in model_findings)
        for item, ref in ground_truth:
            # Loose keyword check
            keywords = item.lower().split()
            caught = any(kw in model_text for kw in keywords if len(kw) > 3)
            status = "CAUGHT" if caught else "MISSED"
            print(f"    [{status}] {item} ({ref})")

        print("=" * 100)
        assert True  # Informational

    def test_model_catches_real_issues(self, tmp_pdf_dir):
        """Verify the model catches the critical engineering issues."""
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf(tmp_pdf_dir,
                         "SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)

        model, findings = _run_model_pipeline(pdf)
        finding_ids = {f.check_id for f in findings}
        finding_text = " ".join(f.description.lower() for f in findings)

        # The model should catch these — they're structural, not keyword
        issues_caught = []
        issues_missed = []

        # GFP on service entrance
        if "MODEL-GFP" in finding_ids:
            issues_caught.append("NEC 230.95 GFP")
        else:
            issues_missed.append("NEC 230.95 GFP")

        # Missing AIC
        if "MODEL-AIC" in finding_ids:
            issues_caught.append("NEC 110.9 AIC rating")
        else:
            issues_missed.append("NEC 110.9 AIC rating")

        # Arc flash
        if "MODEL-ARCFLASH" in finding_ids:
            issues_caught.append("NFPA 70E arc flash")
        else:
            issues_missed.append("NFPA 70E arc flash")

        # AFC labeling
        if "MODEL-AFC" in finding_ids:
            issues_caught.append("NEC 110.24 AFC label")
        else:
            issues_missed.append("NEC 110.24 AFC label")

        # Arc energy reduction for large breakers
        if "MODEL-ARC240.87" in finding_ids:
            issues_caught.append("NEC 240.87 arc energy reduction")
        else:
            issues_missed.append("NEC 240.87 arc energy reduction")

        print(f"\nModel caught: {issues_caught}")
        print(f"Model missed: {issues_missed}")
        print(f"Total model findings: {len(findings)}")

        assert len(issues_caught) >= 3, \
            f"Model should catch at least 3 critical issues. Caught: {issues_caught}, Missed: {issues_missed}"

    def test_model_produces_zero_noise(self, tmp_pdf_dir):
        """The model should NOT produce ATS, battery, generator, cooling findings
        on a switchgear-only document."""
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf(tmp_pdf_dir,
                         "SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)

        model, findings = _run_model_pipeline(pdf)

        # No ATS findings
        ats_findings = [f for f in findings if "ats" in f.check_id.lower()]
        assert len(ats_findings) == 0, f"Model produced ATS findings on switchgear doc: {ats_findings}"

        # No battery findings
        bat_findings = [f for f in findings if "bat" in f.check_id.lower()]
        assert len(bat_findings) == 0, f"Model produced battery findings on switchgear doc: {bat_findings}"

        # No generator findings
        gen_findings = [f for f in findings if "gen" in f.check_id.lower()]
        assert len(gen_findings) == 0, f"Model produced generator findings on switchgear doc: {gen_findings}"

        # No cooling findings
        cool_findings = [f for f in findings if "cool" in f.check_id.lower() or "clg" in f.check_id.lower()]
        assert len(cool_findings) == 0, f"Model produced cooling findings on switchgear doc: {cool_findings}"

        print(f"\nZero noise confirmed: {len(findings)} total findings, all relevant to switchgear")
