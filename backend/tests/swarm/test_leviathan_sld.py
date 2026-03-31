"""Benchmark the model against the real Leviathan SLD (Q25 Rev E).

This is the honest test. The Leviathan SLD is the actual production drawing
from Silent-Aire for the Armada Leviathan modular data center. It has real
ABB breakers, real load designations, real engineering decisions.

The model should catch what an experienced reviewer would catch.
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


def _build_pdf(tmpdir, header, text, filename="lev_sld.pdf"):
    pdf_path = os.path.join(tmpdir, filename)
    builder = SubmittalBuilder()
    builder.add_raw_page(header, text.strip().split("\n"))
    builder.build(pdf_path)
    return pdf_path


def _run_model_on_sld(tmpdir):
    text = _load_text("leviathan_sld_rev_e_text.txt")
    pdf = _build_pdf(tmpdir, "SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDC", text)

    pages = extract_text_by_page(pdf)
    pages = extract_metadata_by_page(pages)
    pages = classify_all_pages(pages)
    page_summary = get_page_summary(pages)
    full_text = "\n".join(p["text"] for p in pages)
    global_metadata = extract_metadata(full_text)
    equipment = extract_all_equipment(pages)
    topology = build_topology(equipment, pages)
    jurisdiction = detect_jurisdiction(pages, global_metadata)

    model = build_system_model(
        equipment=equipment, topology=topology, pages=pages,
        page_summary=page_summary, jurisdiction_result=jurisdiction,
        global_metadata=global_metadata,
    )
    findings = check_model(model)
    return model, findings


class TestLeviathanSLD:

    def test_model_builds_without_crash(self, tmp_pdf_dir):
        model, findings = _run_model_on_sld(tmp_pdf_dir)
        assert len(findings) > 0

    def test_print_full_sld_review(self, tmp_pdf_dir):
        """Print the complete model review of the Leviathan SLD."""
        model, findings = _run_model_on_sld(tmp_pdf_dir)

        print("\n")
        print("=" * 110)
        print("  LEVIATHAN SLD REVIEW (Q25 Rev E) — Model Output")
        print("=" * 110)

        print(f"\n  SYSTEM MODEL:")
        print(f"    Jurisdiction: {model.jurisdiction} ({model.jurisdiction_confidence:.0%})")
        print(f"    System voltage: {model.system_voltage or 'NOT STATED'}V")
        print(f"    Available fault current: {model.available_fault_current_kA or 'NOT FOUND'}kA")
        print(f"    Generator: {model.generator_kva or '?'}kVA / {model.generator_kw or '?'}kW")
        print(f"    QF designations parsed: {len(model.qf_designations)}")
        print(f"    Loads parsed: {len(model.loads)}")
        print(f"    Equipment extracted: {model.total_equipment_count}")
        print(f"    Breakers in model: {len(model.breakers)}")
        print(f"    Transformers: {len(model.transformers)}")
        print(f"    Service entrances: {len(model.service_entrances)}")
        print(f"    Dual mains: {model.has_dual_mains}")
        print(f"    UPS feed-through: {model.has_ups_feed_through}")
        print(f"    Bypass: {model.has_bypass}")

        # Count by severity
        counts = {}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        print(f"\n  FINDINGS: {counts.get('critical', 0)} critical, "
              f"{counts.get('major', 0)} major, {counts.get('minor', 0)} minor, "
              f"{counts.get('info', 0)} info — {len(findings)} total")

        print(f"\n  --- ALL FINDINGS ---")
        for f in sorted(findings, key=lambda x: {"critical": 0, "major": 1, "minor": 2, "info": 3}.get(x.severity, 4)):
            print(f"    [{f.severity.upper():8s}] {f.check_id}: {f.description[:130]}")
            if f.reference:
                print(f"               Ref: {f.reference}")

        # Engineer ground truth — 22 items from my thorough review
        print(f"\n  --- ENGINEER GROUND TRUTH (22 items from manual review) ---")
        ground_truth = [
            ("IT load 2.28MW vs spec 1.77MW", "critical"),
            ("QF141 UPS UOB D — no breaker model", "critical"),
            ("Duplicate: UIB A (QF9 and QF12)", "critical"),
            ("Duplicate: UOB B (QF139 and QF143)", "critical"),
            ("QF12 XT7ML vs all other XT7L — why motor variant?", "major"),
            ("E4.3H on mains vs E6.2H on Cubic layout — which purchased?", "major"),
            ("QF3 E4.3N — N=low breaking capacity, verify kAIC vs 65kA", "critical"),
            ("Chiller1 415.44kVA vs Chiller2/3 416.67kVA", "major"),
            ("XT7L 1600A bypass — verify UL availability", "major"),
            ("TM1 25kVA 480/208V still shown despite Note E (208V dropped)", "major"),
            ("General Services Panel — LOADS TO BE DEFINED", "major"),
            ("Mech Container MCC/BMS — LOADS TO BE DEFINED", "major"),
            ("QF52/QF53 1000A frame 800A trip — what do they feed?", "major"),
            ("Network rack Sn=44.74kVA vs 42.5kW spec", "minor"),
            ("65kA AFC — verify XT2H 125A kAIC adequate", "major"),
            ("No cable schedule for 180+ circuits", "major"),
            ("XT2H vs XT2h capitalization inconsistency", "minor"),
            ("S203-C80NA MCB on SLD — what does it protect?", "minor"),
            ("No arc flash analysis referenced", "major"),
            ("No NEC 110.24 AFC field labels", "major"),
            ("No coordination study referenced", "major"),
            ("RDHx busway/socket — confirm model", "minor"),
        ]

        finding_text_all = " ".join(f.description.lower() + " " + f.check_id.lower()
                                     for f in findings)
        caught = 0
        for item, severity in ground_truth:
            # Loose keyword matching
            keywords = [w for w in item.lower().split() if len(w) > 3]
            hit = sum(1 for kw in keywords if kw in finding_text_all)
            status = "CAUGHT" if hit >= 2 else "MISSED"
            if status == "CAUGHT":
                caught += 1
            print(f"    [{status:6s}] [{severity:8s}] {item}")

        print(f"\n  SCORE: {caught}/{len(ground_truth)} ground truth items caught "
              f"({caught/len(ground_truth)*100:.0f}%)")
        print("=" * 110)

        assert True  # Informational
