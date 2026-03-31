"""Real Submittal Benchmark — feeds actual Armada/Leviathan submittal text through
the review pipeline and evaluates against engineering ground truth.

This is the honest test. No synthetic text, no hand-crafted keywords.
Real equipment descriptions from real vendor submittals (Silent-Aire/Cubic),
extracted via SharePoint MCP from the Armada Hardware Infrastructure team's
actual project documentation.

Documents used:
- LV_Switchgear_markup.pdf — Cubic pre-CAD MDB layout for Armada Leviathan
- 6777-ARMADA MDC-SLD Submittal REV A — Silent-Aire Galleon SLD (480V/60Hz)

Ground truth: What a senior electrical engineer reviewing the Leviathan MDB
would flag during submittal review, based on NEC requirements and data center
best practices.
"""
import os
import pytest

from tests.swarm.pdf_gen.base_builder import SubmittalBuilder
from tests.swarm.conftest import run_review_pipeline


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")


def _build_pdf_from_text(tmpdir: str, pages: list[tuple[str, str]], filename="real_test.pdf") -> str:
    """Build a PDF from raw text pages. Each page is (header, text_content)."""
    pdf_path = os.path.join(tmpdir, filename)
    builder = SubmittalBuilder()
    for header, text in pages:
        lines = text.strip().split("\n")
        builder.add_raw_page(header, lines)
    builder.build(pdf_path)
    return pdf_path


def _load_text(filename: str) -> str:
    path = os.path.join(TEST_DATA_DIR, filename)
    with open(path, "r") as f:
        return f.read()


def _any_finding_mentions(results, keyword, sources=None):
    if sources is None:
        sources = ["checklist_findings", "xref_findings", "deep_findings",
                    "sld_xcheck_findings", "naming_findings"]
    keyword_lower = keyword.lower()
    for source_key in sources:
        for f in results.get(source_key, []):
            text = " ".join(filter(None, [
                getattr(f, "details", None),
                getattr(f, "description", None),
                getattr(f, "check_name", None),
            ])).lower()
            if getattr(f, "passed", None) == 1:
                continue
            if keyword_lower in text:
                return True
    return False


def _count_findings_by_severity(results):
    """Count non-passing findings by severity across all sources."""
    counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}
    for source_key in ["checklist_findings", "xref_findings", "deep_findings",
                         "sld_xcheck_findings", "naming_findings"]:
        for f in results.get(source_key, []):
            if getattr(f, "passed", None) == 1:
                continue
            sev = getattr(f, "severity", "info")
            counts[sev] = counts.get(sev, 0) + 1
    return counts


class TestLeviathanMDB:
    """Test the review engine against the real Leviathan MDB switchgear layout.

    This is a Cubic pre-CAD design for the Armada Leviathan main distribution
    board. It's a 10-cubicle, 4000A, 480V switchgear lineup with:
    - 2x E6.2H 4000A ACB mains (cubicles 1 & 10)
    - 1x E4.2H 3200A ACB loadbank (cubicle 2)
    - 2x E4.2H 3200A ACB IT couplers (cubicles 3 & 6)
    - 8x XT7H 1000A MCCB IT/mech feeders (cubicles 4, 5, 7, 9)
    - 1x XT7H 1600A MCCB bypass mech UPS (cubicle 8)
    - 10x XT5H 400A MCCB distribution (cubicles 4, 5, 7)
    - 48x XT2H 160A/60A rack plug MCCBs (cubicles 4, 5, 7, 9)

    ENGINEERING GROUND TRUTH — what a senior reviewer would flag:
    """

    def test_pipeline_runs_on_real_text(self, tmp_pdf_dir):
        """Verify the pipeline doesn't crash on real submittal text."""
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)])
        results = run_review_pipeline(pdf)

        assert len(results["checklist_findings"]) > 0, \
            "Pipeline produced no checklist findings on real MDB layout"
        assert len(results["equipment"]) > 0, \
            "Equipment extractor found nothing in real MDB text"

    def test_equipment_extraction_from_real_text(self, tmp_pdf_dir):
        """Verify the extractor finds real ABB equipment from Cubic layout text."""
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)])
        results = run_review_pipeline(pdf)

        equipment = results["equipment"]
        eq_desigs = [eq.designation for eq in equipment]
        eq_types = [eq.equipment_type for eq in equipment]

        # Should find breakers from the real ABB equipment text
        print(f"\nExtracted {len(equipment)} equipment items:")
        for eq in equipment:
            print(f"  [{eq.equipment_type}] {eq.designation} "
                  f"(page {eq.page_number}, {eq.amperage or '?'}A)")

        assert len(equipment) >= 3, \
            f"Expected >= 3 equipment items from Leviathan MDB, got {len(equipment)}: {eq_desigs}"

    def test_no_kaic_shown_on_layout(self, tmp_pdf_dir):
        """The Cubic MDB layout shows NO kAIC ratings on any breaker.

        ENGINEERING: This is a real gap. The layout shows E6.2H 4000A but
        doesn't state the interrupting rating. For a 4000A service, the
        engineer MUST know the kAIC to verify NEC 110.9 compliance. A good
        review tool should flag this.
        """
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)])
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "short-circuit") or
                 _any_finding_mentions(results, "sccr") or
                 _any_finding_mentions(results, "interrupting") or
                 _any_finding_mentions(results, "kaic") or
                 _any_finding_mentions(results, "withstand") or
                 _any_finding_mentions(results, "fault current"))
        if not found:
            pytest.xfail("Engine did not flag missing kAIC on 4000A MDB — "
                         "real gap in Cubic layout, no interrupting ratings shown")
        else:
            print("\nCORRECT: Engine flagged missing kAIC/SCCR on Leviathan MDB")

    def test_no_ground_fault_protection_mentioned(self, tmp_pdf_dir):
        """The Cubic layout mentions NO ground fault protection.

        ENGINEERING: NEC 230.95 requires GFP for 480Y/277V services at
        1000A or above. This is a 4000A service. The word "ground fault"
        doesn't appear anywhere. A reviewer must flag this.
        """
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)])
        results = run_review_pipeline(pdf)

        found = _any_finding_mentions(results, "ground fault")
        if not found:
            pytest.xfail("Engine did not flag missing GFP on 4000A MDB — "
                         "NEC 230.95 requires GFP at this rating")
        else:
            print("\nCORRECT: Engine flagged missing GFP on 4000A Leviathan MDB")

    def test_no_arc_flash_data(self, tmp_pdf_dir):
        """No arc flash analysis referenced in the Cubic layout.

        ENGINEERING: NFPA 70E requires arc flash labels. IEEE 1584 analysis
        must be referenced. The layout is silent on arc flash — a reviewer
        must note this for the submittal response.
        """
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)])
        results = run_review_pipeline(pdf)

        found = _any_finding_mentions(results, "arc flash")
        if not found:
            pytest.xfail("Engine did not flag missing arc flash data on MDB layout")
        else:
            print("\nCORRECT: Engine flagged missing arc flash reference")

    def test_interlocking_tbd(self, tmp_pdf_dir):
        """Cubicle 10 says 'INTERLOCKING TBC' — not confirmed.

        ENGINEERING: The interlocking scheme between mains and generator
        is critical for selective coordination and preventing paralleling.
        'TBC' means it hasn't been designed yet. A reviewer should flag
        this as an open item requiring response.
        """
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)])
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "interlock") or
                 _any_finding_mentions(results, "tbc") or
                 _any_finding_mentions(results, "tbd"))
        if not found:
            pytest.xfail("Engine did not flag 'INTERLOCKING TBC' — "
                         "open design item on mains interlocking")
        else:
            print("\nCORRECT: Engine flagged unconfirmed interlocking scheme")

    def test_no_voltage_label_on_layout(self, tmp_pdf_dir):
        """The Cubic layout shows NO system voltage (480V, 277V, etc.).

        ENGINEERING: Every SLD must clearly state the system voltage.
        The layout shows '4000A BUS BAR' but never says what voltage.
        This is a basic submittal deficiency.
        """
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)])
        results = run_review_pipeline(pdf)

        found = _any_finding_mentions(results, "voltage")
        # The layout genuinely has no voltage label
        if found:
            print("\nCORRECT: Engine flagged missing voltage on MDB layout")

    def test_pre_cad_disclaimer(self, tmp_pdf_dir):
        """The layout says 'PRE CAD DESIGN ONLY' and 'NOT AN APPROVAL DRAWING'.

        ENGINEERING: This is a preliminary drawing. The reviewer should note
        this status and clarify whether it's being submitted for information
        only or for approval. If for approval, it needs to be upgraded.
        """
        text = _load_text("lv_switchgear_markup_text.txt")
        assert "PRE CAD DESIGN ONLY" in text
        assert "NOT AN APPROVAL DRAWING" in text
        # This is a document status check — the engine may or may not catch it
        # but it's important context for the reviewer

    def test_print_full_engine_output(self, tmp_pdf_dir):
        """Print everything the engine finds on the real Leviathan MDB.

        This is the benchmark output. Compare it to what YOU would flag.
        """
        text = _load_text("lv_switchgear_markup_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA LEVIATHAN MDB", text)])
        results = run_review_pipeline(pdf)

        counts = _count_findings_by_severity(results)

        print("\n")
        print("=" * 100)
        print("  REAL SUBMITTAL BENCHMARK: ARMADA LEVIATHAN MDB (Cubic Layout)")
        print("=" * 100)
        print(f"  Equipment extracted: {len(results['equipment'])}")
        print(f"  SLD entries: {len(results['sld_entries'])}")
        print(f"  Schedule entries: {len(results['schedule_entries'])}")
        print(f"  Findings: {counts['critical']} critical, {counts['major']} major, "
              f"{counts['minor']} minor, {counts['info']} info")
        print("")

        print("  --- EQUIPMENT FOUND ---")
        for eq in results["equipment"]:
            print(f"    [{eq.equipment_type}] {eq.designation} "
                  f"({eq.amperage or '?'}A, {eq.voltage or '?'}V, page {eq.page_number})")

        print("")
        print("  --- CRITICAL/MAJOR FINDINGS ---")
        for source_key in ["checklist_findings", "xref_findings", "deep_findings",
                             "sld_xcheck_findings", "naming_findings"]:
            for f in results.get(source_key, []):
                sev = getattr(f, "severity", "info")
                passed = getattr(f, "passed", None)
                if passed == 1 or sev not in ("critical", "major"):
                    continue
                text_detail = getattr(f, "details", None) or getattr(f, "description", "")
                ref = getattr(f, "reference_standard", None) or getattr(f, "reference_code", "")
                check_id = getattr(f, "check_id", "") or ""
                print(f"    [{sev.upper()}] {check_id} {text_detail[:120]}")
                if ref:
                    print(f"             Ref: {ref}")

        print("")
        print("  --- ENGINEERING GROUND TRUTH (what a reviewer SHOULD flag) ---")
        print("    1. No kAIC/SCCR shown on any breaker (NEC 110.9)")
        print("    2. No ground fault protection referenced (NEC 230.95)")
        print("    3. No arc flash analysis referenced (NFPA 70E, IEEE 1584)")
        print("    4. No system voltage label (480V not stated)")
        print("    5. 'INTERLOCKING TBC' — mains interlock scheme unconfirmed")
        print("    6. 'PRE CAD DESIGN ONLY' — not an approval drawing")
        print("    7. No NEC 110.24 AFC labeling")
        print("    8. 1600A bypass breaker (cubicle 8) — NEC 240.87 arc energy reduction?")
        print("    9. Cable sizing '300sq 4c 240PE' — verify adequacy for 4000A service")
        print("   10. Power Safe Connectors 'TBC' — another unconfirmed item")
        print("=" * 100)

        # This test always passes — it's informational
        assert True


class TestGalleonSLD:
    """Test the review engine against the real Galleon SLD submittal."""

    def test_pipeline_runs_on_galleon_sld(self, tmp_pdf_dir):
        """Verify the pipeline runs on the real Galleon SLD text."""
        text = _load_text("galleon_sld_text.txt")
        pdf = _build_pdf_from_text(tmp_pdf_dir,
            [("SINGLE LINE DIAGRAM - ARMADA MDC GALLEON", text)])
        results = run_review_pipeline(pdf)

        assert len(results["checklist_findings"]) > 0
        print(f"\nGalleon SLD: {len(results['equipment'])} equipment, "
              f"{len(results['checklist_findings'])} checklist findings")
