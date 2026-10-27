"""Offline tests: SAMPLE_MODE, no Zetaris, no Nightshift. Run: python -m pytest -q"""
import json
import os
from pathlib import Path

os.environ["SAMPLE_MODE"] = "true"
os.environ.setdefault("HMEM_URL", "http://127.0.0.1:1")  # force the local fallback unless the service is up

from app.agents import Context, critique  # noqa: E402
from app.evaluation import load_cases  # noqa: E402
from app.pipeline import Harness  # noqa: E402
from app.trace import Tracer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CASES = {c["id"]: c for c in load_cases(ROOT / "domains" / "admin")}


def make(space):
    h = Harness(memory_space=space, quiet=True)
    h.memory.reset()
    return h


def test_examples_run_and_return_structured_output():
    h = make("test-examples")
    for path in sorted((ROOT / "input_examples").glob("*.json")):
        payload = json.loads(path.read_text())
        res = h.run(payload["input"])
        assert res["status"] == "success", res
        assert res["output"]["decision"] in h.domain.config["decisions"]
        assert (ROOT / res["log_file"]).exists()


def test_scams_are_blocked():
    h = make("test-scams")
    for cid in ["c08", "c09", "c10", "c11", "c24", "c28"]:
        assert h.run(CASES[cid])["output"]["decision"] == "block_scam", cid


def test_correction_changes_the_next_decision():
    h = make("test-memory")
    assert h.run(CASES["c03"])["output"]["decision"] == "escalate"
    h.learn(CASES["c03"], "pay", "I always pay EDF up to 120 EUR")
    later = h.run(CASES["c04"])["output"]
    assert later["decision"] == "pay"
    assert any(c.startswith(("mem", "lm-")) for c in later["citations"])
    assert h.run(CASES["c05"])["output"]["decision"] == "escalate"  # above the owner's ceiling


def test_critic_rejects_invented_citations_and_unsafe_pay(tmp_path):
    h = make("test-critic")
    ctx = Context(item=CASES["c28"], flags=["exfiltration"], facts={"amount_eur": 29.99})
    tr = Tracer("test-critic", tmp_path, quiet=True)
    verdict = critique(ctx, {"decision": "pay", "citations": ["R99"]}, h.domain, h.llm, tr, 0)
    assert not verdict["passed"]
    assert any("does not exist" in p for p in verdict["problems"])
    assert any("not allowed" in p for p in verdict["problems"])


def test_unknown_input_does_not_crash():
    h = make("test-unknown")
    res = h.run({"id": "x", "from": "someone@nowhere.example", "subject": "Hello", "body": "Just saying hi."})
    assert res["status"] == "success"
    assert res["output"]["decision"] == "escalate"
