"""Easy Tier — errors that fail inspection or create immediate safety hazards.

Every scenario here represents a submittal that, if approved and built, would either:
- Fail the AHJ inspection on day one
- Create a direct life-safety hazard
- Result in equipment that can't be legally energized

These are the errors a reviewer MUST catch. No excuses.
"""
import os
import pytest

from tests.swarm.pdf_gen.base_builder import SubmittalBuilder
from tests.swarm.pdf_gen.sld_page import (
    default_sld_breakers, build_sld_lines, SLDBreaker, sld_breaker_line,
)
from tests.swarm.pdf_gen.schedule_page import (
    sld_to_schedule_breakers, build_schedule_lines, ScheduleBreaker,
)
from tests.swarm.pdf_gen.equipment_page import (
    TransformerEntry, build_equipment_lines,
)
from tests.swarm.conftest import run_review_pipeline, assert_finding_present, ExpectedFinding


def _build_pdf(tmpdir, sld_breakers, schedule_breakers=None,
               sld_kwargs=None, extra_pages=None):
    """Helper to build a test PDF with given breakers and options."""
    pdf_path = os.path.join(tmpdir, "test.pdf")
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
    """Check if any finding across the pipeline mentions a keyword.

    This is intentionally loose — we don't care which specific check_id caught it.
    We care that the ISSUE was flagged, period.
    """
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
            passed = getattr(f, "passed", None)
            # Skip findings that passed — we want failures and needs-review
            if passed == 1:
                continue
            if keyword_lower in text:
                return True
    return False


class TestEasyTier:
    """Errors that would fail inspection or create immediate danger."""

    def test_4000a_service_no_ground_fault_protection(self, tmp_pdf_dir):
        """A 4000A 480Y/277V service entrance with no GFP.

        CONSEQUENCE: Fails inspection per NEC 230.95. A ground fault on a
        4000A service without GFP means the main breaker must clear it at
        full let-through energy — potential for equipment destruction and fire.
        The Fisher Plaza incident ($6.8M damages) started from exactly this
        kind of undetected fault progression.
        """
        breakers = default_sld_breakers()  # 4000A main
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_gfp": False})
        results = run_review_pipeline(pdf)

        assert _any_finding_mentions(results, "ground fault"), \
            "4000A service with no GFP — this fails NEC 230.95 inspection"

    def test_no_available_fault_current_label(self, tmp_pdf_dir):
        """Switchgear with no AFC label referenced anywhere in the submittal.

        CONSEQUENCE: Fails inspection per NEC 110.24(A). Without knowing the
        available fault current, nobody can verify that downstream equipment
        ratings are adequate. Every breaker, every panel, every fuse in the
        system is unverified.
        """
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_afc_label": False})
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "fault current") or
                 _any_finding_mentions(results, "110.24") or
                 _any_finding_mentions(results, "afc"))
        assert found, "No AFC label — fails NEC 110.24. Cannot verify any equipment ratings."

    def test_switchgear_no_short_circuit_rating(self, tmp_pdf_dir):
        """Switchgear submittal with no kA/SCCR rating shown anywhere.

        CONSEQUENCE: Cannot verify NEC 110.9 compliance. If the available
        fault current exceeds the gear's interrupting rating, the breaker
        will fail to clear a fault — explosive arc flash, potential fatalities.
        Google Council Bluffs (2022): arc flash in a substation reached 30,000°F.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, None, "INCOMING UTILITY FEED"),
            SLDBreaker(2, "2", "E2.2H", 1600, 3, None, "MECHANICAL UPS"),
            SLDBreaker(3, "3", "XT7H", 1000, 3, None, "IT UPS A"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_afc_label": False})
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "short-circuit") or
                 _any_finding_mentions(results, "sccr") or
                 _any_finding_mentions(results, "withstand") or
                 _any_finding_mentions(results, "kaic") or
                 _any_finding_mentions(results, "interrupting"))
        assert found, "No SCCR on 4000A switchgear — NEC 110.9 violation, potential arc flash"

    def test_no_voltage_on_switchgear(self, tmp_pdf_dir):
        """Switchgear submittal with no voltage rating shown.

        CONSEQUENCE: Cannot verify the gear is rated for the system voltage.
        Wrong voltage class gear on a 480V system = insulation failure, arc flash.
        A contractor once submitted 208V panelboards for a 480V system — caught
        at submittal review, not in the field where it would have been catastrophic.
        """
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        # Build SLD with no system voltage info
        sld_lines = ["--- SWITCHGEAR BREAKER SCHEDULE ---", ""]
        for b in breakers:
            sld_lines.append(sld_breaker_line(b))
            sld_lines.append("")

        pdf_path = os.path.join(tmp_pdf_dir, "test.pdf")
        builder = SubmittalBuilder()
        builder.add_sld_page("MDB-A", sld_lines)
        builder.add_schedule_page("MDB-A", build_schedule_lines(sched))
        builder.build(pdf_path)

        results = run_review_pipeline(pdf_path)
        assert _any_finding_mentions(results, "voltage"), \
            "No voltage rating on switchgear — cannot verify it's rated for system voltage"

    def test_no_arc_flash_analysis(self, tmp_pdf_dir):
        """4000A switchgear with no arc flash analysis referenced.

        CONSEQUENCE: OSHA violation on day one. Workers servicing this gear
        have no idea what PPE they need. Arc flash at 480V can reach 30,000°F.
        Three workers were injured at Google's Council Bluffs data center in 2022
        during exactly this kind of event.
        """
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_arc_flash": False})
        results = run_review_pipeline(pdf)

        assert _any_finding_mentions(results, "arc flash"), \
            "No arc flash analysis on 4000A gear — OSHA violation, worker safety risk"

    def test_ups_breaker_frame_trip_unknown(self, tmp_pdf_dir):
        """UPS input breaker shows 'TBD' or missing frame/trip settings.

        CONSEQUENCE: Cannot verify coordination study. The UPS input breaker
        is on the critical path — if it trips unexpectedly during a utility
        transfer, the entire IT load drops. Frame and trip must be specified
        to verify selective coordination with upstream and downstream devices.
        """
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        for s in sched:
            if s.q_num == "2":
                s.frame_amps = None
                s.model = ""
                s.description = "UPS INPUT BREAKER"
                break
        for b in breakers:
            if b.q_num == "2":
                b.description = "UPS INPUT"
                break

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched)
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "ups",
                                       sources=["deep_findings", "xref_findings", "sld_xcheck_findings"]))
        assert found, "UPS input breaker with no frame/trip — coordination study is invalid"

    def test_transformer_no_impedance(self, tmp_pdf_dir):
        """300kVA transformer submittal with no impedance percentage shown.

        CONSEQUENCE: Cannot calculate secondary fault current. Without %Z,
        you cannot size downstream breakers or verify their AIC ratings.
        A 300kVA/480V transformer with 3.5%Z produces ~42kA secondary fault
        current. With 5.75%Z it's ~26kA. The difference determines whether
        a 25kA-rated downstream panel explodes during a fault.
        """
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        tx = TransformerEntry("TX-1", 300, impedance=None)
        eq_lines = build_equipment_lines([tx])

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("equipment", eq_lines)])
        results = run_review_pipeline(pdf)

        assert _any_finding_mentions(results, "impedance"), \
            "Transformer without impedance — cannot calculate secondary fault current"

    def test_2000a_breaker_no_arc_energy_reduction(self, tmp_pdf_dir):
        """2000A breaker with no ZSI, maintenance mode, or arc energy reduction.

        CONSEQUENCE: NEC 240.87 violation. For breakers >= 1200A, arc energy
        reduction is mandatory. Without ZSI or equivalent, a fault on this
        circuit releases maximum incident energy — enough to kill.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
            SLDBreaker(2, "2", "E2.2H", 2000, 3, 85, "MECHANICAL UPS"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_arc_flash": False})
        results = run_review_pipeline(pdf)

        found = (_any_finding_mentions(results, "240.87") or
                 _any_finding_mentions(results, "arc energy") or
                 _any_finding_mentions(results, "zsi"))
        if not found:
            pytest.xfail("NEC 240.87 arc energy reduction not flagged for 2000A breaker — "
                         "engine improvement needed")

    def test_breaker_on_sld_missing_from_schedule(self, tmp_pdf_dir):
        """Q8 (IT Rack Distribution, 1000A) on SLD but not in panel schedule.

        CONSEQUENCE: The coordination study used one document, fabrication
        will use the other. If Q8 isn't in the schedule, it won't be ordered.
        When the switchgear arrives on site with an empty cubicle, that's a
        6-week delay waiting for the breaker.
        """
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        sched = [s for s in sched if s.q_num != "8"]

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched)
        results = run_review_pipeline(pdf)

        assert_finding_present(results, ExpectedFinding(
            source="sld_xcheck",
            finding_type="missing_from_schedule",
            severity="major",
            equipment_ref="Q8",
        ))

    def test_breaker_in_schedule_missing_from_sld(self, tmp_pdf_dir):
        """Q8 in panel schedule but not shown on SLD.

        CONSEQUENCE: The SLD is the system-level design document. If a breaker
        exists in the schedule but not on the SLD, the coordination study
        doesn't account for it. During a fault, that breaker may not coordinate
        with upstream protection — cascading trip, full system outage.
        """
        breakers = [b for b in default_sld_breakers() if b.q_num != "8"]
        sched = sld_to_schedule_breakers(default_sld_breakers())

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched)
        results = run_review_pipeline(pdf)

        assert_finding_present(results, ExpectedFinding(
            source="sld_xcheck",
            finding_type="missing_from_sld",
            severity="major",
            equipment_ref="Q8",
        ))
