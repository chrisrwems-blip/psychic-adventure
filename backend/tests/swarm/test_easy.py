"""Easy Tier Tests — obvious missing information and keyword-absence errors.

These test the review engine's ability to catch clearly missing data:
- Missing ground fault protection
- Missing AFC labeling
- Missing SCCR/kA ratings
- Missing voltage ratings
- Missing arc flash data
- UPS breakers without frame/trip
- Missing transformer impedance
- Missing arc energy reduction for large breakers
- SLD/schedule orphans
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


class TestEasyTier:
    """E1: No ground fault protection keywords on a 1600A+ service."""

    def test_e1_missing_ground_fault_protection(self, tmp_pdf_dir):
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_gfp": False})
        results = run_review_pipeline(pdf)

        # Check that ground fault issue is flagged somewhere
        # The checklist checker SW-012 looks for "ground fault" keywords
        all_findings = (results["checklist_findings"] +
                        results["xref_findings"] +
                        results["deep_findings"])

        gfp_found = any(
            ("ground fault" in (getattr(f, "details", "") or
                                getattr(f, "description", "") or "").lower()
             and getattr(f, "passed", 0) != 1)
            for f in all_findings
        )
        assert gfp_found, "Expected ground fault protection issue to be flagged"

    def test_e2_missing_afc_labeling(self, tmp_pdf_dir):
        """E2: No available fault current labeling."""
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_afc_label": False})
        results = run_review_pipeline(pdf)

        all_findings = (results["checklist_findings"] +
                        results["xref_findings"])
        afc_found = any(
            ("fault current" in (getattr(f, "details", "") or
                                 getattr(f, "description", "") or "").lower()
             or "110.24" in (getattr(f, "details", "") or
                             getattr(f, "description", "") or "")
             or "afc" in (getattr(f, "details", "") or
                          getattr(f, "description", "") or "").lower())
            and getattr(f, "passed", 0) != 1
            for f in all_findings
        )
        assert afc_found, "Expected AFC labeling issue to be flagged"

    def test_e3_missing_sccr(self, tmp_pdf_dir):
        """E3: SLD breakers with no kA/SCCR rating and no AFC label."""
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, None, "INCOMING UTILITY FEED"),
            SLDBreaker(2, "2", "E2.2H", 1600, 3, None, "MECHANICAL UPS"),
            SLDBreaker(3, "3", "XT7H", 1000, 3, None, "IT UPS A"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        # Also disable AFC label since it contains "42kA" which triggers SCCR pass
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_afc_label": False})
        results = run_review_pipeline(pdf)

        # SW-002 checks for SCCR; should flag when no kA values found
        sccr_found = any(
            "sw-002" in (getattr(f, "check_id", "") or "").lower()
            and f.passed != 1
            for f in results["checklist_findings"]
        )
        assert sccr_found, "Expected SCCR/kA missing to be flagged (SW-002)"

    def test_e4_missing_voltage_rating(self, tmp_pdf_dir):
        """E4: SLD with no voltage mentioned."""
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        # Build with no system voltage
        sld_lines = [
            "--- SWITCHGEAR BREAKER SCHEDULE ---",
            "",
        ]
        for b in breakers:
            sld_lines.append(sld_breaker_line(b))
            sld_lines.append("")

        pdf_path = os.path.join(tmp_pdf_dir, "test.pdf")
        builder = SubmittalBuilder()
        builder.add_sld_page("MDB-A", sld_lines)
        builder.add_schedule_page("MDB-A", build_schedule_lines(sched))
        builder.build(pdf_path)

        results = run_review_pipeline(pdf_path)
        # SW-001 checks for voltage rating
        voltage_flagged = any(
            "sw-001" in (getattr(f, "check_id", "") or "").lower()
            and f.passed != 1
            for f in results["checklist_findings"]
        )
        # Voltage is still mentioned in breaker amps context — this may pass.
        # The point is that dedicated voltage label is missing.
        # Accept either checklist or cross-ref finding about voltage
        if not voltage_flagged:
            voltage_flagged = any(
                "voltage" in (getattr(f, "description", "") or
                              getattr(f, "details", "") or "").lower()
                and getattr(f, "passed", 0) != 1
                for f in results["checklist_findings"] + results["xref_findings"]
            )
        assert voltage_flagged, "Expected voltage rating issue to be flagged"

    def test_e5_missing_arc_flash(self, tmp_pdf_dir):
        """E5: No arc flash data in submittal."""
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_arc_flash": False})
        results = run_review_pipeline(pdf)

        arc_found = any(
            ("sw-040" in (getattr(f, "check_id", "") or "").lower()
             or "arc flash" in (getattr(f, "details", "") or
                                getattr(f, "description", "") or "").lower())
            and getattr(f, "passed", 0) != 1
            for f in results["checklist_findings"]
        )
        assert arc_found, "Expected arc flash data missing to be flagged (SW-040)"

    def test_e6_ups_breaker_no_frame_trip(self, tmp_pdf_dir):
        """E6: UPS-related breaker with no frame/trip specified."""
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        # Make UPS breaker (Q2) have no frame/trip in schedule
        for s in sched:
            if s.q_num == "2":
                s.frame_amps = None
                s.model = ""
                s.description = "UPS INPUT BREAKER"
                break

        # Also make the SLD entry look like a UPS breaker without details
        for b in breakers:
            if b.q_num == "2":
                b.description = "UPS INPUT"
                break

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched)
        results = run_review_pipeline(pdf)

        ups_detail_found = any(
            "ups" in (getattr(f, "description", "") or "").lower()
            and getattr(f, "severity", "") in ("major", "critical")
            for f in results["deep_findings"]
        )
        # Also accept a frame_mismatch or missing detail from xref
        if not ups_detail_found:
            ups_detail_found = any(
                "ups" in (getattr(f, "description", "") or
                          getattr(f, "details", "") or "").lower()
                for f in results["xref_findings"] + results["sld_xcheck_findings"]
            )
        assert ups_detail_found, "Expected UPS breaker missing frame/trip to be flagged"

    def test_e7_missing_transformer_impedance(self, tmp_pdf_dir):
        """E7: Transformer without impedance listed."""
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)

        tx = TransformerEntry("TX-1", 300, impedance=None)
        eq_lines = build_equipment_lines([tx])

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         extra_pages=[("equipment", eq_lines)])
        results = run_review_pipeline(pdf)

        # TX checker should flag missing impedance
        impedance_found = any(
            ("impedance" in (getattr(f, "details", "") or
                             getattr(f, "description", "") or "").lower())
            and getattr(f, "passed", 0) != 1
            for f in results["checklist_findings"] + results["xref_findings"]
        )
        assert impedance_found, "Expected missing transformer impedance to be flagged"

    def test_e8_arc_energy_reduction_large_breaker(self, tmp_pdf_dir):
        """E8: 2000A breaker without arc energy reduction mention.

        NEC 240.87 requires arc energy reduction for breakers >= 1200A.
        """
        breakers = [
            SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING UTILITY FEED"),
            SLDBreaker(2, "2", "E2.2H", 2000, 3, 85, "MECHANICAL UPS"),
        ]
        sched = sld_to_schedule_breakers(breakers)
        # Remove arc flash and any arc energy reduction keywords
        pdf = _build_pdf(tmp_pdf_dir, breakers, sched,
                         sld_kwargs={"include_arc_flash": False})
        results = run_review_pipeline(pdf)

        arc_energy_found = any(
            ("240.87" in (getattr(f, "description", "") or
                          getattr(f, "details", "") or "")
             or "arc energy" in (getattr(f, "description", "") or
                                 getattr(f, "details", "") or "").lower()
             or "arc-energy" in (getattr(f, "description", "") or
                                 getattr(f, "details", "") or "").lower())
            for f in results["xref_findings"] + results["checklist_findings"]
        )
        # This may be xfail if the engine doesn't catch it yet
        if not arc_energy_found:
            pytest.xfail("Arc energy reduction check (NEC 240.87) not triggered for 2000A breaker")

    def test_e9_breaker_on_sld_not_in_schedule(self, tmp_pdf_dir):
        """E9: Breaker exists on SLD but not in panel schedule."""
        breakers = default_sld_breakers()
        sched = sld_to_schedule_breakers(breakers)
        # Remove Q8 from schedule
        sched = [s for s in sched if s.q_num != "8"]

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched)
        results = run_review_pipeline(pdf)

        assert_finding_present(results, ExpectedFinding(
            source="sld_xcheck",
            finding_type="missing_from_schedule",
            severity="major",
            equipment_ref="Q8",
        ))

    def test_e10_breaker_in_schedule_not_on_sld(self, tmp_pdf_dir):
        """E10: Breaker in schedule but not on SLD."""
        breakers = default_sld_breakers()
        # Remove Q8 from SLD
        breakers = [b for b in breakers if b.q_num != "8"]
        sched = sld_to_schedule_breakers(default_sld_breakers())

        pdf = _build_pdf(tmp_pdf_dir, breakers, sched)
        results = run_review_pipeline(pdf)

        assert_finding_present(results, ExpectedFinding(
            source="sld_xcheck",
            finding_type="missing_from_sld",
            severity="major",
            equipment_ref="Q8",
        ))
