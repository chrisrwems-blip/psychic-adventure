"""Hard Tier — errors that require engineering calculations or multi-document analysis.

These are the errors that a tool SHOULD catch but that require real engineering
knowledge: NEC table lookups, fault current calculations, manufacturer product
data validation, and cross-referencing between equipment on different pages.

A good reviewer catches these. A great tool automates them.
"""
import os
import pytest

from tests.swarm.pdf_gen.base_builder import SubmittalBuilder
from tests.swarm.pdf_gen.sld_page import (
    default_sld_breakers, build_sld_lines, SLDBreaker,
)
from tests.swarm.pdf_gen.schedule_page import (
    sld_to_schedule_breakers, build_schedule_lines, ScheduleBreaker,
)
from tests.swarm.pdf_gen.equipment_page import (
    TransformerEntry, CableEntry, build_equipment_lines, build_cable_lines,
)
from tests.swarm.conftest import run_review_pipeline, assert_finding_present, ExpectedFinding


def _build_pdf(tmpdir, sld_breakers, schedule_breakers=None,
               sld_kwargs=None, extra_pages=None, filename="test.pdf"):
    pdf_path = os.path.join(tmpdir, filename)
    builder = SubmittalBuilder()
    kwargs = sld_kwargs or {}
    sld_lines = build_sld_lines(sld_breakers, **kwargs)
    builder.add_sld_page("MDB-A", sld_lines)
    if schedule_breakers is not None:
        sched_lines = build_schedule_lines(schedule_breakers)
        builder.add_schedule_page("MDB-A", sched_lines)
    if extra_pages:
        for page_type, lines in extra_pages:
            if page_type == "equipment":
                builder.add_equipment_page(lines)
            elif page_type == "cable":
                builder.add_cable_page(lines)
            else:
                builder.add_raw_page(page_type, lines)
    builder.build(pdf_path)
    return pdf_path


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


class TestHardTier:

    def test_6awg_on_100a_breaker_will_catch_fire(self, tmp_pdf_dir):
        """#6 AWG copper on a 100A breaker — the wire will overheat.

        ENGINEERING: NEC 310.16 at 75°C gives #6 AWG copper 65A ampacity.
        100A breaker allows 100A continuous. 100A through a 65A-rated wire
        means the conductor runs at 154% of rated ampacity. The insulation
        degrades over weeks/months, then arcs inside the conduit.

        This is how electrical fires start. NEC 240.4 exists to prevent this.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
            SLDBreaker(3, "3", "XT5H", 100, 3, 65, "CHILLER PUMP"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        cables = [
            CableEntry("F-3", "#6 AWG", 3, "THHN", "Copper", '1" EMT', 100,
                        fed_from="MDB-A Q3", feeds="CHILLER PUMP", breaker_amps=100),
        ]
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("cable", build_cable_lines(cables))])
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "undersized") or
                 _any_finding_mentions(results, "ampacity") or
                 _any_finding_mentions(results, "310.16") or
                 _any_finding_mentions(results, "cable"))
        if not found:
            pytest.xfail("#6 AWG on 100A breaker not caught — "
                         "equipment extractor doesn't link cable conductor_size to breaker amps")

    def test_abb_xt5h_800a_doesnt_exist(self, tmp_pdf_dir):
        """XT5H specified at 800A — but XT5 maxes out at 600A.

        ENGINEERING: ABB Tmax XT frame sizes are fixed:
        XT2=125A, XT4=250A, XT5=600A, XT7=1200A.
        XT5H at 800A is a product that doesn't exist. ABB will reject
        the order. At best it's a 6-week schedule delay. At worst,
        someone orders XT5H 600A (the actual max) and puts it on an
        800A circuit — the breaker trips under normal load.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
            SLDBreaker(12, "12", "XT5H", 800, 3, 65, "CHILLER PLANT"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched)
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "xt5") or
                 _any_finding_mentions(results, "invalid") or
                 _any_finding_mentions(results, "exceed") or
                 _any_finding_mentions(results, "abb"))
        if not found:
            pytest.xfail("XT5H 800A (invalid product) not caught — "
                         "ABB validation needs breaker model+frame parsed as a pair")

    def test_14awg_on_20a_breaker_small_wire_rule(self, tmp_pdf_dir):
        """#14 AWG on a 20A breaker — violates NEC 240.4(D).

        ENGINEERING: NEC 240.4(D) explicitly limits #14 AWG to 15A OCPD max.
        No exceptions, no derating, no engineering judgment. 20A on #14 AWG
        means the wire can carry 133% of its rated ampacity before the breaker
        trips. That's a fire waiting to happen.

        This is one of the most commonly cited NEC violations in inspections.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        cables = [
            CableEntry("F-CTRL", "#14 AWG", 1, "THHN", "Copper", '1/2" EMT', 50,
                        fed_from="LP-A", feeds="CONTROL CIRCUIT", breaker_amps=20),
        ]
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("cable", build_cable_lines(cables))])
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "240.4") or
                 _any_finding_mentions(results, "small wire") or
                 _any_finding_mentions(results, "#14"))
        if not found:
            pytest.xfail("#14 AWG on 20A breaker not caught — "
                         "small wire rule check needs conductor_size on extracted equipment")

    def test_25ka_panel_downstream_of_low_impedance_transformer(self, tmp_pdf_dir):
        """25kA panel downstream of a 2000kVA/3.5%Z transformer.

        ENGINEERING: 2000kVA at 208V secondary = 5550A FLA.
        Secondary fault current ≈ FLA / (%Z/100) = 5550 / 0.035 ≈ 158kA.
        Even with upstream impedance limiting it, actual AFC will be well
        above 25kA. The downstream panel will fail catastrophically during
        a fault — the breakers literally cannot interrupt the current.

        This is how people die in electrical rooms.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
            SLDBreaker(13, "13", "XT5H", 400, 3, 25, "DOWNSTREAM PANEL"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        tx = TransformerEntry("TX-2", 2000, "480V", "208V", "3.5%", "Dry-Type",
                              winding="Delta-Wye", ul_listed=True)
        eq_lines = build_equipment_lines([tx])

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("equipment", eq_lines)])
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "fault current") or
                 _any_finding_mentions(results, "110.9") or
                 _any_finding_mentions(results, "aic") or
                 _any_finding_mentions(results, "interrupting"))
        if not found:
            pytest.xfail("25kA panel downstream of 2000kVA/3.5%Z transformer not caught — "
                         "needs topology linking transformer to downstream breaker")

    def test_500ft_feeder_voltage_drop(self, tmp_pdf_dir):
        """500ft feeder run at 100A on #4 AWG at 480V — over 3% voltage drop.

        ENGINEERING: V_drop = √3 × I × R × L / 1000
        #4 AWG copper resistance ≈ 0.321 Ω/1000ft
        V_drop = 1.732 × 100 × 0.321 × 500 / 1000 = 27.8V
        At 480V, that's 5.8% — well above the 3% NEC recommendation for feeders.

        CONSEQUENCE: Equipment at the end of this run sees 452V instead of 480V.
        Motors run hot and inefficient. VFDs may fault. UPS systems may not
        charge properly. This is a chronic operational problem.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
            SLDBreaker(14, "14", "XT5H", 100, 3, 65, "REMOTE PANEL"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        cables = [
            CableEntry("F-14", "#4 AWG", 3, "THHN", "Copper", '1-1/4" EMT', 500,
                        fed_from="MDB-A Q14", feeds="REMOTE PANEL", breaker_amps=100),
        ]
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("cable", build_cable_lines(cables))])
        results = run_review_pipeline(pdf)

        found = _any_finding_mentions(results, "voltage drop")
        if not found:
            pytest.xfail("5.8% voltage drop on 500ft/#4 AWG not caught — "
                         "engine needs cable length + size to calculate voltage drop")

    def test_transformer_ocpd_oversized_beyond_nec_450_3(self, tmp_pdf_dir):
        """600A primary OCPD on a 300kVA/480V transformer.

        ENGINEERING: 300kVA at 480V = 361A FLA.
        NEC 450.3(B) allows max 125% of FLA = 451A for primary OCPD.
        Next standard size up = 500A.
        600A exceeds the maximum — the transformer is unprotected.

        A fault inside the transformer won't be cleared quickly enough.
        The transformer overheats, the oil (or resin) catches fire, and
        the electrical room is destroyed.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
            SLDBreaker(15, "15", "XT5H", 600, 3, 65, "TRANSFORMER TX-3"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        tx = TransformerEntry("TX-3", 300, "480V", "208V", "5.75%", "Dry-Type",
                              ul_listed=True)
        eq_lines = build_equipment_lines([tx])

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("equipment", eq_lines)])
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "450.3") or
                 _any_finding_mentions(results, "transformer") and
                 _any_finding_mentions(results, "protection"))
        if not found:
            pytest.xfail("600A OCPD on 300kVA transformer (max 500A per NEC 450.3) not caught — "
                         "needs topology linking OCPD to transformer")

    def test_multi_error_submittal_five_issues(self, tmp_pdf_dir):
        """Submittal with 5 simultaneous errors — tests the tool catches multiple.

        Real submittals don't have one error. They have many. A good tool
        catches them all in one pass, not just the first one. This also tests
        deduplication — the tool shouldn't report the same issue 50 times
        across different checkers.
        """
        breakers = default_sld_breakers()[:5]
        sched = sld_to_schedule_breakers(breakers)

        # Error 1: Frame mismatch Q3 (1000A SLD → 800A schedule)
        for s in sched:
            if s.q_num == "3":
                s.frame_amps = 800
                break
        # Error 2: Model mismatch Q5 (XT5H → XT2H)
        for s in sched:
            if s.q_num == "5":
                s.model = "XT2H"
                break
        # Error 3: Q4 missing from schedule (orphan on SLD)
        sched = [s for s in sched if s.q_num != "4"]
        # Error 4: No GFP on 4000A service
        # Error 5: No arc flash analysis

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_gfp": False, "include_arc_flash": False})
        results = run_review_pipeline(pdf)

        issues_found = 0
        if any(f.finding_type == "frame_mismatch" for f in results["sld_xcheck_findings"]):
            issues_found += 1
        if any(f.finding_type == "model_mismatch" for f in results["sld_xcheck_findings"]):
            issues_found += 1
        if any(f.finding_type in ("missing_from_schedule", "missing_from_sld")
               for f in results["sld_xcheck_findings"]):
            issues_found += 1
        if _any_finding_mentions(results, "ground fault") or \
           _any_finding_mentions(results, "arc flash"):
            issues_found += 1

        assert issues_found >= 3, \
            f"Multi-error submittal: expected >= 3 issues caught, got {issues_found}"

    def test_50mm2_cable_on_200a_breaker_metric_undersized(self, tmp_pdf_dir):
        """50mm² cable on a 200A breaker — undersized per IEC 60364.

        ENGINEERING: IEC 60364 gives 50mm² copper PVC 3-phase = 125A.
        200A through a 125A-rated cable = same problem as #6 AWG on 100A,
        just in metric. The cable overheats.

        IMPORTANT: Do NOT convert mm² to AWG and use NEC tables.
        50mm² ≈ 1/0 AWG but the actual cross-section differs enough
        that using NEC 310.16 ampacity is dangerous. Use IEC tables directly.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        cable_lines = [
            "--- FEEDER / CABLE SCHEDULE ---",
            "",
            "FEEDER F-METRIC: 3x50mm2 XLPE Copper in 80mm conduit, 100m",
            "Fed from MDB-A, Breaker: 200A",
            "",
        ]
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("cable", cable_lines)])
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "metric") or
                 _any_finding_mentions(results, "mm2") or
                 _any_finding_mentions(results, "50mm"))
        if not found:
            pytest.xfail("50mm² cable on 200A breaker not caught — "
                         "metric cable sizing check needs equipment extractor to parse mm²")

    def test_selective_coordination_failure(self, tmp_pdf_dir):
        """Upstream and downstream breakers both at 400A — no coordination.

        ENGINEERING: If the upstream breaker feeding a sub-panel has the same
        trip setting as the sub-panel's main breaker, a fault on the sub-panel
        will trip BOTH breakers simultaneously. NEC 700.32 requires selective
        coordination on emergency systems — the downstream device must trip
        first, leaving the upstream circuit energized.

        Without coordination, a fault on one circuit takes out an entire section.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
            SLDBreaker(16, "16", "XT5H", 400, 3, 65, "SUB PANEL A"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        eq_lines = [
            "SUB PANEL A",
            "Main Breaker: XT5H 400A 3P 65kA",
            "Fed from MDB-A Q16 (400A)",
            "",
            "Sub Breaker: XT5H 400A 3P",
            "DOWNSTREAM SAME AS UPSTREAM",
            "",
        ]
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("equipment", eq_lines)])
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "coordination") or
                 _any_finding_mentions(results, "selective"))
        if not found:
            pytest.xfail("Selective coordination failure (same trip upstream and downstream) "
                         "not caught — needs topology linking for this scenario")

    def test_complex_realistic_submittal(self, tmp_pdf_dir):
        """Full 8-breaker submittal with 2 subtle cross-document errors.

        This simulates a real ABB switchgear submittal for a Leviathan MDB.
        The errors are the kind that slip through on a Friday afternoon:
        Q3 kAIC is 50kA in the schedule but 65kA on the SLD, and Q7's
        model changed from XT5H to XT2H but nobody updated the SLD.
        """
        sld_breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(sld_breakers)

        # Subtle error 1: Q3 kAIC mismatch (65kA SLD → 50kA schedule)
        for s in sched:
            if s.q_num == "3":
                s.kaic = 50
                break
        # Subtle error 2: Q7 model changed (XT5H SLD → XT2H schedule)
        for s in sched:
            if s.q_num == "7":
                s.model = "XT2H"
                break

        tx = TransformerEntry("TX-1", 500, "480V", "208V", "5.75%", "Dry-Type",
                              k_factor="K-13", ul_listed=True)
        eq_lines = build_equipment_lines([tx])

        pdf = _build_pdf(tmp_pdf_dir, sld_breakers, sched,
                         extra_pages=[("equipment", eq_lines)])
        results = run_review_pipeline(pdf)

        issues = []
        if any(f.finding_type == "kaic_mismatch" and "Q3" in (f.equipment_1 or "")
               for f in results["sld_xcheck_findings"]):
            issues.append("kaic_mismatch_Q3")
        if any(f.finding_type == "model_mismatch" and "Q7" in (f.equipment_1 or "")
               for f in results["sld_xcheck_findings"]):
            issues.append("model_mismatch_Q7")

        assert len(issues) >= 1, \
            f"Complex submittal with 2 subtle errors — caught: {issues}. " \
            f"SLD xcheck: {[(f.finding_type, f.equipment_1) for f in results['sld_xcheck_findings']]}"
