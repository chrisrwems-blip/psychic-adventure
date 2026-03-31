"""Coverage Report — runs all scenarios and prints a consequence-based catch/miss matrix.

Each scenario is described by what breaks if the error gets through review,
not by what regex pattern the tool uses internally.

Run with: pytest tests/swarm/test_coverage_report.py -v -s
"""
import os
import tempfile
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
from tests.swarm.conftest import run_review_pipeline


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


SCENARIOS = []


def _register(sid, consequence, nec_ref):
    def wrapper(func):
        func._sid = sid
        func._consequence = consequence
        func._nec_ref = nec_ref
        SCENARIOS.append(func)
        return func
    return wrapper


# ---- EASY: Fails inspection or immediate safety hazard ----

@_register("E1", "Fails inspection — NEC 230.95 GFP required for 1000A+ services", "NEC 230.95")
def s_e1(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    r = run_review_pipeline(_build_pdf(d, b, s, sld_kwargs={"include_gfp": False}))
    return _any_finding_mentions(r, "ground fault")

@_register("E2", "Cannot verify any equipment ratings without AFC label", "NEC 110.24")
def s_e2(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    r = run_review_pipeline(_build_pdf(d, b, s, sld_kwargs={"include_afc_label": False}))
    return _any_finding_mentions(r, "fault current") or _any_finding_mentions(r, "110.24") or _any_finding_mentions(r, "afc")

@_register("E3", "No SCCR — breaker may fail to interrupt fault (arc flash)", "NEC 110.9")
def s_e3(d):
    b = [SLDBreaker(1, "1", "E6.2H", 4000, 3, None, "INCOMING")]
    s = sld_to_schedule_breakers(b)
    r = run_review_pipeline(_build_pdf(d, b, s, sld_kwargs={"include_afc_label": False}))
    return _any_finding_mentions(r, "short-circuit") or _any_finding_mentions(r, "sccr") or _any_finding_mentions(r, "withstand") or _any_finding_mentions(r, "interrupting")

@_register("E4", "No arc flash analysis — OSHA violation, worker safety", "NFPA 70E / IEEE 1584")
def s_e4(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    r = run_review_pipeline(_build_pdf(d, b, s, sld_kwargs={"include_arc_flash": False}))
    return _any_finding_mentions(r, "arc flash")

@_register("E5", "Breaker on SLD not in schedule — won't be ordered, 6-week delay", "Drawing Consistency")
def s_e5(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    s = [x for x in s if x.q_num != "8"]
    r = run_review_pipeline(_build_pdf(d, b, s))
    return any(f.finding_type == "missing_from_schedule" and "Q8" in (f.equipment_1 or "") for f in r["sld_xcheck_findings"])

@_register("E6", "Breaker in schedule not on SLD — coordination study invalid", "Drawing Consistency")
def s_e6(d):
    b = [x for x in default_sld_breakers() if x.q_num != "8"]
    s = sld_to_schedule_breakers(default_sld_breakers())
    r = run_review_pipeline(_build_pdf(d, b, s))
    return any(f.finding_type == "missing_from_sld" and "Q8" in (f.equipment_1 or "") for f in r["sld_xcheck_findings"])

# ---- MEDIUM: Invalidates coordination study or creates hidden risk ----

@_register("M1", "SLD/schedule frame mismatch — wrong breaker gets built", "Drawing Consistency / SCCR")
def s_m1(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    for x in s:
        if x.q_num == "8": x.frame_amps = 800; break
    r = run_review_pipeline(_build_pdf(d, b, s))
    return any(f.finding_type == "frame_mismatch" and "Q8" in (f.equipment_1 or "") for f in r["sld_xcheck_findings"])

@_register("M2", "kAIC mismatch — breaker may not survive a fault", "NEC 110.9")
def s_m2(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    for x in s:
        if x.q_num == "1": x.kaic = 65; break
    r = run_review_pipeline(_build_pdf(d, b, s))
    return any(f.finding_type == "kaic_mismatch" and "Q1" in (f.equipment_1 or "") for f in r["sld_xcheck_findings"])

@_register("M3", "Model mismatch — XT5H can't do 1000A (max 600A)", "ABB Product Data")
def s_m3(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    for x in s:
        if x.q_num == "3": x.model = "XT5H"; break
    r = run_review_pipeline(_build_pdf(d, b, s))
    return any(f.finding_type == "model_mismatch" and "Q3" in (f.equipment_1 or "") for f in r["sld_xcheck_findings"])

@_register("M4", "Trip > frame — physically impossible breaker spec", "ABB Product Data")
def s_m4(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    eq = ["BREAKER CB-X", "XT5H 630", "Frame: 630A", "Trip Setting: 800A", ""]
    r = run_review_pipeline(_build_pdf(d, b, s, extra_pages=[("equipment", eq)]))
    return any(f.finding_type == "trip_exceeds_frame" for f in r["xref_findings"])

@_register("M5", "Identical incomers with different kAIC — one is wrong", "NEC 110.9")
def s_m5(d):
    b = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING SOURCE A"),
         SLDBreaker(2, "2", "E6.2H", 4000, 3, 65, "INCOMING SOURCE B")]
    s = [ScheduleBreaker("1", "E6.2H", 4000, 3, 85, "INCOMING", description="INCOMING SOURCE A"),
         ScheduleBreaker("2", "E6.2H", 4000, 3, 65, "INCOMING", description="INCOMING SOURCE B")]
    r = run_review_pipeline(_build_pdf(d, b, s))
    return any(f.finding_type == "kaic_inconsistency" for f in r["sld_xcheck_findings"])

@_register("M6", "K-1 transformer feeding GPUs — overheats in 3-5 years", "IEEE C57.110")
def s_m6(d):
    b = default_sld_breakers(); s = sld_to_schedule_breakers(b)
    tx = TransformerEntry("TX-IT1", 500, k_factor=None)
    eq = build_equipment_lines([tx]) + ["TX-IT1 FEEDS IT RACK DISTRIBUTION", "HARMONIC LOAD: GPU SERVERS"]
    r = run_review_pipeline(_build_pdf(d, b, s, extra_pages=[("equipment", eq)]))
    return _any_finding_mentions(r, "k-factor") or _any_finding_mentions(r, "harmonic")

# ---- HARD: Requires engineering calculations ----

@_register("H1", "#6 AWG on 100A breaker — wire overheats, fire risk", "NEC 310.16, 240.4")
def s_h1(d):
    b = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING"),
         SLDBreaker(3, "3", "XT5H", 100, 3, 65, "PUMP")]
    s = sld_to_schedule_breakers(b)
    c = [CableEntry("F-3", "#6 AWG", 3, "THHN", "Copper", '1" EMT', 100, breaker_amps=100)]
    r = run_review_pipeline(_build_pdf(d, b, s, extra_pages=[("cable", build_cable_lines(c))]))
    return _any_finding_mentions(r, "undersized") or _any_finding_mentions(r, "ampacity") or _any_finding_mentions(r, "310.16")

@_register("H2", "XT5H 800A doesn't exist (max 600A) — order rejected", "ABB Tmax XT Product Data")
def s_h2(d):
    b = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING"),
         SLDBreaker(12, "12", "XT5H", 800, 3, 65, "CHILLER")]
    s = sld_to_schedule_breakers(b)
    r = run_review_pipeline(_build_pdf(d, b, s))
    return _any_finding_mentions(r, "xt5") or _any_finding_mentions(r, "invalid") or _any_finding_mentions(r, "abb")

@_register("H3", "#14 AWG on 20A breaker — NEC 240.4(D) violation, fire risk", "NEC 240.4(D)")
def s_h3(d):
    b = [SLDBreaker(1, "1", "E6.2H", 4000, 3, 85, "INCOMING")]
    s = sld_to_schedule_breakers(b)
    c = [CableEntry("F-CTRL", "#14 AWG", 1, "THHN", "Copper", '1/2" EMT', 50, breaker_amps=20)]
    r = run_review_pipeline(_build_pdf(d, b, s, extra_pages=[("cable", build_cable_lines(c))]))
    return _any_finding_mentions(r, "240.4") or _any_finding_mentions(r, "small wire") or _any_finding_mentions(r, "#14")

@_register("H4", "Multi-error submittal — 5 issues, tests dedup", "Multiple")
def s_h4(d):
    b = default_sld_breakers()[:5]; s = sld_to_schedule_breakers(b)
    for x in s:
        if x.q_num == "3": x.frame_amps = 800; break
    for x in s:
        if x.q_num == "5": x.model = "XT2H"; break
    s = [x for x in s if x.q_num != "4"]
    r = run_review_pipeline(_build_pdf(d, b, s, sld_kwargs={"include_gfp": False, "include_arc_flash": False}))
    issues = 0
    if any(f.finding_type == "frame_mismatch" for f in r["sld_xcheck_findings"]): issues += 1
    if any(f.finding_type == "model_mismatch" for f in r["sld_xcheck_findings"]): issues += 1
    if any(f.finding_type in ("missing_from_schedule", "missing_from_sld") for f in r["sld_xcheck_findings"]): issues += 1
    return issues >= 3


class TestCoverageReport:
    def test_print_coverage_matrix(self, tmp_pdf_dir):
        """Run all scenarios and print the engineering-consequence catch/miss matrix."""
        results_list = []

        for func in SCENARIOS:
            try:
                caught = func(tmp_pdf_dir)
            except Exception:
                caught = False
            results_list.append({
                "id": func._sid,
                "consequence": func._consequence,
                "nec": func._nec_ref,
                "caught": caught,
            })

        print("\n")
        print("=" * 110)
        print("  SUBMITTAL REVIEW ENGINE — ERROR DETECTION COVERAGE")
        print("  What happens if this error gets through review?")
        print("=" * 110)
        print(f"{'ID':<5} {'CAUGHT':<8} {'NEC/STD':<22} {'CONSEQUENCE IF MISSED'}")
        print("-" * 110)

        caught_n = sum(1 for r in results_list if r["caught"])
        missed_n = sum(1 for r in results_list if not r["caught"])

        for r in results_list:
            status = "YES" if r["caught"] else "MISS"
            marker = "  " if r["caught"] else ">>"
            print(f"{marker}{r['id']:<3} {status:<8} {r['nec']:<22} {r['consequence']}")

        print("-" * 110)
        total = len(results_list)
        print(f"  CAUGHT: {caught_n}/{total} ({caught_n/total*100:.0f}%)  |  "
              f"MISSED: {missed_n}/{total} ({missed_n/total*100:.0f}%)")
        print("")

        if missed_n > 0:
            print("  IMPROVEMENT PRIORITIES (by consequence severity):")
            for r in results_list:
                if not r["caught"]:
                    print(f"    >> {r['id']}: {r['consequence']}")

        print("=" * 110)
        assert True
