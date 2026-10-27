"""Steward + the team's coordination modules: progress per member, alerts when a decision changes."""
from app.coordination.bridge import value_of
from app.steward import Steward


def test_values_compare_by_date_or_amount():
    assert value_of("Public launch on 2026-12-01.") == "2026-12-01"
    assert value_of("Pricing: 29 EUR per user per month; annual plan 290 EUR") == value_of("29 EUR")
    assert value_of("1,500 EUR") == "1500 EUR"


def test_seeded_progress_flags_the_late_task_and_who_it_blocks():
    st = Steward(space="t-progress")
    st.reset()
    p = st.progress()
    late = {(f["member"], f["task_id"]) for f in p["findings"] if f["case"] == "late"}
    assert late == {("Léa Martin", "t01")}
    blocked = sorted(tuple(m["evidence"]) for m in p["meetings"])
    assert blocked == [("t01", "t02"), ("t01", "t03")]


def test_new_price_alerts_the_people_whose_work_relies_on_the_old_one():
    st = Steward(space="t-alerts")
    st.reset()
    res = st.remember("Pricing changes to 35 EUR per user per month from January 2027; annual plan 350 EUR per user.",
                      "Claire Morel", "Claude", "decision", "pricing")
    assert res["decision"] == "supersede"
    assert res["alerts_sent"] == ["Julie Caron", "Paul Lefèvre"]
    first = st.alerts("Julie Caron")
    assert len(first) == 1 and "35 EUR" in first[0]["message"]
    assert st.alerts("Julie Caron") == []  # returned once
    obsolete = {f["member"] for f in st.progress()["findings"] if f["case"] == "obsolete"}
    assert obsolete == {"Julie Caron", "Paul Lefèvre"}
    assert any(s["kind"] == "coordination" and "obsolete" in s["signal"] for s in st.signals())


def test_report_progress_is_checked_against_the_decisions_in_force():
    st = Steward(space="t-report")
    st.reset()
    out = st.report_progress("Inès Roux", "t04", 0.7, {"launch_date": "2026-11-15"}, "moved the countdown")
    f = next(f for f in out["findings"] if f["task_id"] == "t04")
    assert f["case"] == "obsolete" and "2026-12-01" in f["reason"]
    try:
        st.report_progress("Inès Roux", "t01", 0.9)
        raise AssertionError("someone else's task must be refused")
    except ValueError:
        pass
