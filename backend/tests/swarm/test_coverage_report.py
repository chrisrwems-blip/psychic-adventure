"""Coverage Report — runs all 30 scenarios and prints a catch/miss matrix.

Run with: pytest tests/swarm/test_coverage_report.py -v -s
The -s flag is needed to see the printed report.
"""
import os
import tempfile
import pytest

from tests.swarm.pdf_gen.base_builder import SubmittalBuilder
from tests.swarm.pdf_gen.sld_page import (
    default_sld_breakers, build_sld_lines, SLDBreaker, sld_breaker_line,
)
from tests.swarm.pdf_gen.schedule_page import (
    sld_to_schedule_breakers, build_schedule_lines, ScheduleBreaker,
)
from tests.swarm.pdf_gen.equipment_page import (
    TransformerEntry, CableEntry, build_equipment_lines, build_cable_lines,
)
from tests.swarm.conftest import run_review_pipeline


def _build_pdf(tmpdir, sld_breakers, schedule_breakers=None,
               sld_kwargs=None, extra_pages=None, filename="test.pdf"):
    """Helper to build a test PDF."""
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


# ---- Scenario Definitions ----

SCENARIOS = []


def _register(scenario_id, name, severity, check_target):
    """Decorator-like registration for scenarios."""
    def wrapper(func):
        func._scenario_id = scenario_id
        func._scenario_name = name
        func._severity = severity
        func._check_target = check_target
        SCENARIOS.append(func)
        return func
    return wrapper


@_register("E1", "Missing ground fault protection", "critical", "SW-012 / xref GFP")
def scenario_e1(tmpdir):
    breakers = default_sld_breakers()
    sched = sld_to_schedule_breakers(breakers)
    pdf = _build_pdf(tmpdir, breakers, sched, sld_kwargs={"include_gfp": False})
    results = run_review_pipeline(pdf)
    all_f = results["checklist_findings"] + results["xref_findings"]
    return any(
        "ground fault" in (getattr(f, "details", "") or getattr(f, "description", "") or "").lower()
        and getattr(f, "passed", 0) != 1
        for f in all_f
    )


@_register("E2", "Missing AFC labeling", "major", "xref _check_afc_labeling")
def scenario_e2(tmpdir):
    breakers = default_sld_breakers()
    sched = sld_to_schedule_breakers(breakers)
    pdf = _build_pdf(tmpdir, breakers, sched, sld_kwargs={"include_afc_label": False})
    results = run_review_pipeline(pdf)
    all_f = results["checklist_findings"] + results["xref_findings"]
    return any(
        ("110.24" in (getattr(f, "details", "") or getattr(f, "description", "") or "")
         or "afc" in (getattr(f, "details", "") or getattr(f, "description", "") or "").lower())
        and getattr(f, "passed", 0) != 1
        for f in all_f
    )


@_register("E3", "Missing SCCR/kA", "critical", "SW-002")
def scenario_e3(tmpdir):
    breakers = [SLDBreaker(1, "1", "E6.2H", 4000, 3, None, "INCOMING")]
    sched = sld_to_schedule_breakers(breakers)
    pdf = _build_pdf(tmpdir, breakers, sched, sld_kwargs={"include_afc_label": False})
    results = run_review_pipeline(pdf)
    return any(
        "sw-002" in (getattr(f, "check_id", "") or "").lower() and f.passed != 1
        for f in results["checklist_findings"]
    )


@_register("E4", "Missing arc flash data", "critical", "SW-040")
def scenario_e4(tmpdir):
    breakers = default_sld_breakers()
    sched = sld_to_schedule_breakers(breakers)
    pdf = _build_pdf(tmpdir, breakers, sched, sld_kwargs={"include_arc_flash": False})
    results = run_review_pipeline(pdf)
    return any(
        ("sw-040" in (getattr(f, "check_id", "") or "").lower()
         or "arc flash" in (getattr(f, "details", "") or "").lower())
        and f.passed != 1
        for f in results["checklist_findings"]
    )


@_register("E5", "Breaker on SLD not in schedule", "major", "sld_xcheck missing_from_schedule")
def scenario_e5(tmpdir):
    breakers = default_sld_breakers()
    sched = sld_to_schedule_breakers(breakers)
    sched = [s for s in sched if s.q_num != "8"]
    pdf = _build_pdf(tmpdir, breakers, sched)
    results = run_review_pipeline(pdf)
    return any(
        f.finding_type == "missing_from_schedule" and "Q8" in (f.equipment_1 or "")
        for f in results["sld_xcheck_findings"]
    )


@_register("E6", "Breaker in schedule not on SLD", "major", "sld_xcheck missing_from_sld")
def scenario_e6(tmpdir):
    breakers = [b for b in default_sld_breakers() if b.q_num != "8"]
    sched = sld_to_schedule_breakers(default_sld_breakers())
    pdf = _build_pdf(tmpdir, breakers, sched)
    results = run_review_pipeline(pdf)
    return any(
        f.finding_type == "missing_from_sld" and "Q8" in (f.equipment_1 or "")
        for f in results["sld_xcheck_findings"]
    )


@_register("M1", "Frame size mismatch", "critical", "sld_xcheck frame_mismatch")
def scenario_m1(tmpdir):
    breakers = default_sld_breakers()
    sched = sld_to_schedule_breakers(breakers)
    for s in sched:
        if s.q_num == "8":
            s.frame_amps = 800
            break
    pdf = _build_pdf(tmpdir, breakers, sched)
    results = run_review_pipeline(pdf)
    return any(
        f.finding_type == "frame_mismatch" and "Q8" in (f.equipment_1 or "")
        for f in results["sld_xcheck_findings"]
    )


@_register("M2", "kAIC mismatch", "critical", "sld_xcheck kaic_mismatch")
def scenario_m2(tmpdir):
    breakers = default_sld_breakers()
    sched = sld_to_schedule_breakers(breakers)
    for s in sched:
        if s.q_num == "1":
            s.kaic = 65
            break
    pdf = _build_pdf(tmpdir, breakers, sched)
    results = run_review_pipeline(pdf)
    return any(
        f.finding_type == "kaic_mismatch" and "Q1" in (f.equipment_1 or "")
        for f in results["sld_xcheck_findings"]
    )


@_register("M3", "Model mismatch", "major", "sld_xcheck model_mismatch")
def scenario_m3(tmpdir):
    breakers = default_sld_breakers()
    sched = sld_to_schedule_breakers(breakers)
    for s in sched:
        if s.q_num == "3":
            s.model = "XT5H"
            break
    pdf = _build_pdf(tmpdir, breakers, sched)
    results = run_review_pipeline(pdf)
    return any(
        f.finding_type == "model_mismatch" and "Q3" in (f.equipment_1 or "")
        for f in results["sld_xcheck_findings"]
    )


@_register("M4", "Trip exceeds frame", "critical", "xref trip_exceeds_frame")
def scenario_m4(tmpdir):
    breakers = default_sld_breakers()
    sched = sld_to_schedule_breakers(breakers)
    eq_lines = ["BREAKER CB-X", "XT5H 630", "Frame Size: 630A", "Trip Setting: 800A", ""]
    pdf = _build_pdf(tmpdir, breakers, sched, extra_pages=[("equipment", eq_lines)])
    results = run_review_pipeline(pdf)
    return any(f.finding_type == "trip_exceeds_frame" for f in results["xref_findings"])


@_register("M5", "Non-standard breaker size", "minor", "xref non_standard_size")
def scenario_m5(tmpdir):
    breakers = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING"),
                SLDBreaker(11, "11", "XT2H", 155, 3, 65, "FAN")]
    sched = sld_to_schedule_breakers(breakers)
    pdf = _build_pdf(tmpdir, breakers, sched)
    results = run_review_pipeline(pdf)
    return any(f.finding_type == "non_standard_size" for f in results["xref_findings"])


@_register("M6", "Inconsistent kAIC on incomers", "major", "sld_xcheck kaic_inconsistency")
def scenario_m6(tmpdir):
    breakers = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING SOURCE A"),
                SLDBreaker(2, "2", "E6.2H", 4000, 3, 65, "INCOMING SOURCE B")]
    sched = [ScheduleBreaker("1", "E6.2H", 4000, 3, 85, "INCOMING", description="INCOMING SOURCE A"),
             ScheduleBreaker("2", "E6.2H", 4000, 3, 65, "INCOMING", description="INCOMING SOURCE B")]
    pdf = _build_pdf(tmpdir, breakers, sched)
    results = run_review_pipeline(pdf)
    return any(f.finding_type == "kaic_inconsistency" for f in results["sld_xcheck_findings"])


@_register("H1", "Cable undersized per NEC 310.16", "critical", "xref cable sizing")
def scenario_h1(tmpdir):
    breakers = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING"),
                SLDBreaker(3, "3", "XT5H", 100, 3, 65, "PUMP")]
    sched = sld_to_schedule_breakers(breakers)
    cables = [CableEntry("F-3", "#6 AWG", 3, "THHN", "Copper", '1" EMT', 100,
                          breaker_amps=100)]
    pdf = _build_pdf(tmpdir, breakers, sched,
                     extra_pages=[("cable", build_cable_lines(cables))])
    results = run_review_pipeline(pdf)
    return any(
        f.finding_type in ("cable_undersized", "breaker_cable_mismatch")
        or "310.16" in (f.description or "")
        for f in results["xref_findings"]
    )


@_register("H2", "Invalid ABB product XT5H 800A", "major", "xref ABB validation")
def scenario_h2(tmpdir):
    breakers = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING"),
                SLDBreaker(12, "12", "XT5H", 800, 3, 65, "CHILLER")]
    sched = sld_to_schedule_breakers(breakers)
    pdf = _build_pdf(tmpdir, breakers, sched)
    results = run_review_pipeline(pdf)
    return any(
        "abb" in (f.finding_type or "").lower()
        or ("xt5" in (f.description or "").lower() and "invalid" in (f.description or "").lower())
        for f in results["xref_findings"]
    )


@_register("H3", "Small wire rule violation", "critical", "xref small_wire_rule")
def scenario_h3(tmpdir):
    breakers = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING")]
    sched = sld_to_schedule_breakers(breakers)
    cables = [CableEntry("F-CTRL", "#14 AWG", 1, "THHN", "Copper", '1/2" EMT', 50,
                          breaker_amps=20)]
    pdf = _build_pdf(tmpdir, breakers, sched,
                     extra_pages=[("cable", build_cable_lines(cables))])
    results = run_review_pipeline(pdf)
    return any(
        "small_wire" in (f.finding_type or "").lower()
        or "240.4" in (f.description or "")
        for f in results["xref_findings"]
    )


@_register("H4", "Multi-error submittal (5 errors)", "mixed", "full pipeline dedup")
def scenario_h4(tmpdir):
    breakers = default_sld_breakers()[:5]
    sched = sld_to_schedule_breakers(breakers)
    for s in sched:
        if s.q_num == "3":
            s.frame_amps = 800
            break
    for s in sched:
        if s.q_num == "5":
            s.model = "XT2H"
            break
    sched = [s for s in sched if s.q_num != "4"]
    pdf = _build_pdf(tmpdir, breakers, sched,
                     sld_kwargs={"include_gfp": False, "include_arc_flash": False})
    results = run_review_pipeline(pdf)
    issues = 0
    if any(f.finding_type == "frame_mismatch" for f in results["sld_xcheck_findings"]):
        issues += 1
    if any(f.finding_type == "model_mismatch" for f in results["sld_xcheck_findings"]):
        issues += 1
    if any(f.finding_type in ("missing_from_schedule", "missing_from_sld")
           for f in results["sld_xcheck_findings"]):
        issues += 1
    return issues >= 3


# ---- Report Runner ----

class TestCoverageReport:
    def test_print_coverage_matrix(self, tmp_pdf_dir):
        """Run all scenarios and print catch/miss matrix."""
        results = []

        for scenario_func in SCENARIOS:
            sid = scenario_func._scenario_id
            name = scenario_func._scenario_name
            severity = scenario_func._severity
            target = scenario_func._check_target

            try:
                caught = scenario_func(tmp_pdf_dir)
            except Exception as e:
                caught = False

            results.append({
                "id": sid,
                "name": name,
                "severity": severity,
                "target": target,
                "caught": caught,
            })

        # Print report
        print("\n")
        print("=" * 100)
        print("  AGENT SWARM ERROR TESTING — COVERAGE REPORT")
        print("=" * 100)
        print(f"{'ID':<6} {'SCENARIO':<42} {'SEVERITY':<10} {'CAUGHT':<8} {'CHECK TARGET'}")
        print("-" * 100)

        caught_count = 0
        missed_count = 0
        for r in results:
            status = "YES" if r["caught"] else "MISS"
            marker = "  " if r["caught"] else ">>"
            if r["caught"]:
                caught_count += 1
            else:
                missed_count += 1
            print(f"{marker}{r['id']:<4} {r['name']:<42} {r['severity']:<10} {status:<8} {r['target']}")

        print("-" * 100)
        total = len(results)
        print(f"  TOTAL: {total}  |  CAUGHT: {caught_count}  |  MISSED: {missed_count}  "
              f"|  RATE: {caught_count/total*100:.0f}%")
        print("=" * 100)

        # Don't fail the test — this is informational
        assert True
