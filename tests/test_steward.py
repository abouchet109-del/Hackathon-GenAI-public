"""Offline tests for the OSEF Steward (domain project_memory). Run: python -m pytest -q"""
import json
import os
from pathlib import Path

os.environ["SAMPLE_MODE"] = "true"
os.environ.setdefault("HMEM_URL", "http://127.0.0.1:1")  # local fallback unless the H-MEM service is up

from app.steward import Steward  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CASES = {json.loads(l)["id"]: json.loads(l) for l in
         (ROOT / "domains" / "project_memory" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}


def fresh(space, policies=True):
    st = Steward(space=space)
    st.reset(seed=True, policies=policies)
    return st


def propose(st, cid):
    c = CASES[cid]
    return st.remember(c["content"], c["author"], c["ai_tool"], c["kind"], c["topic"])


def test_every_decision_type_is_reachable():
    st = fresh("t-types")
    expected = {"c01": "store", "c05": "supersede", "c15": "reject", "c13": "redact", "c04": "escalate",
                "c06": "clarify", "c23": "quarantine"}
    for cid, decision in expected.items():
        assert propose(st, cid)["decision"] == decision, cid


def test_supersede_keeps_the_old_decision_as_history():
    st = fresh("t-supersede")
    res = propose(st, "c05")
    assert res["decision"] == "supersede" and res["applied"]["supersedes"]
    history = st.why("pricing")["history"]
    old = next(h for h in history if h["id"] == res["applied"]["supersedes"])
    assert old["superseded_by"] == res["applied"]["memory_id"]          # replaced, never deleted
    assert [c["content"] for c in st.why("pricing")["current"]] == [CASES["c05"]["content"]]


def test_ceo_policy_changes_the_next_decision():
    st = fresh("t-policy", policies=False)
    first = propose(st, "c03")
    assert first["decision"] == "escalate"
    pending = st.escalations()
    st.resolve(pending[-1]["journal_id"], "store", policy="Marketing may commit up to 12,000 EUR per trade show without asking me.")
    later = st.remember("Book a booth at Bois & Bati Lyon for 11,800 EUR.", "Tom Girard", "Gemini", "decision", "marketing_spend")
    assert later["decision"] == "store"
    assert any(c.startswith(("mem", "lm-")) for c in later["citations"])
    assert propose(st, "c04")["decision"] == "escalate"                   # above the CEO's ceiling


def test_secrets_and_injections_never_reach_memory_in_clear():
    st = fresh("t-safety")
    assert propose(st, "c14")["decision"] == "redact"
    assert propose(st, "c23")["decision"] == "quarantine"
    everything = " ".join(r["content"] for r in st.records())
    assert "sk-live" not in everything and "Brikk2026" not in everything
    assert "ignore previous instructions" not in everything.lower()


def test_without_memory_the_steward_lets_contradictions_in():
    """The ablation in one test: the same contradiction is caught with memory, stored without it."""
    st = fresh("t-ablation")
    c = CASES["c31"]
    item = {"content": c["content"], "author": c["author"], "ai_tool": c["ai_tool"], "kind": c["kind"], "topic": c["topic"]}
    assert st.h.run(item, profile="full")["output"]["decision"] == "clarify"
    assert st.h.run(item, profile="no_memory")["output"]["decision"] == "store"


def test_clarify_then_author_confirms_or_withdraws():
    st = fresh("t-clarify")
    first = propose(st, "c06")                                            # Head of Sales contradicts the CEO's price
    assert first["decision"] == "clarify"
    jid = first["applied"]["journal_id"]
    assert [c["journal_id"] for c in st.clarifications("Paul Lefèvre")] == [jid]
    st.answer_clarification(jid, "change", "We agreed it with two pilots")
    assert [e["journal_id"] for e in st.escalations()] == [jid]           # a confirmed change goes up
    second = propose(st, "c31")
    st.answer_clarification(second["applied"]["journal_id"], "error")
    assert second["applied"]["journal_id"] not in [e["journal_id"] for e in st.escalations()]


def test_trust_weight_follows_role_and_domain():
    st = fresh("t-trust")
    low = propose(st, "c33")                                              # intern, outside marketing: 0.1
    assert low["decision"] == "store"
    rec = next(r for r in st.memory.list("topic:metrics") if r["id"] == low["applied"]["memory_id"])
    assert "trust:0.1" in rec["tags"] and rec["confidence"] <= 0.11
    assert propose(st, "c32")["decision"] == "escalate"                   # interns do not decide


def test_observe_extracts_only_watched_items_and_never_stores_raw_text():
    st = fresh("t-observe")
    text = ("Lunch was great today. I told Martin Plomberie the price is 19 EUR per user per month. "
            "I'll send Batir Plus the contract by 2026-10-30.")
    res = st.observe(text, "Julie Caron", "ChatGPT")
    decisions = {o["extracted"]: o["decision"] for o in res["outcomes"]}
    assert "Lunch was great today." not in decisions
    assert decisions["I told Martin Plomberie the price is 19 EUR per user per month."] == "clarify"
    assert res["raw_text_stored"] is False
    assert "Lunch" not in " ".join(r["content"] for r in st.records())


def test_context_is_tailored_to_the_role_and_within_budget():
    st = fresh("t-context")
    cto = st.my_context("Sami Haddad", "where do we host the backend?")
    sales = st.my_context("Paul Lefèvre", "a customer asks for a discount")
    assert "tech_stack" in cto["task_topics"] and "customer_deals" in sales["task_topics"]
    assert any("FastAPI" in line for line in cto["context"].splitlines())
    assert "P01" in sales["context"]                                      # the sales discount procedure
    assert cto["approx_tokens"] <= 1500 and sales["approx_tokens"] <= 1500


def test_whats_new_reports_a_replaced_decision_once():
    st = fresh("t-new")
    st.whats_new("Karim Diallo")                                          # first session: sets the cursor
    propose(st, "c05")                                                    # the CEO changes the price
    news = st.whats_new("Karim Diallo")
    assert any(c["topic"] == "pricing" and c["replaces"] for c in news["changes"])
    assert st.whats_new("Karim Diallo")["changes"] == []                  # already seen


def test_onboarding_shapes_the_profile_but_not_the_authority():
    st = fresh("t-onboard")
    prof = st.onboard({"name": "Tom Girard", "responsibilities": "Paid ads", "topics_followed": "metrics, pricing",
                       "focus": "commercial", "detail_level": "3"})
    assert prof["topics_followed"] == ["metrics", "pricing"] and prof["detail_level"] == 3
    assert prof["level"] == "member"                                      # the questionnaire cannot make him a lead
