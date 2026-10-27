"""The HTTP surface in SAMPLE_MODE: /health, POST /run on the Steward pack, the finance source, the console."""
import os

os.environ["SAMPLE_MODE"] = "true"
os.environ.setdefault("HMEM_URL", "http://127.0.0.1:1")
os.environ["STEWARD_SPACE"] = "t-server"

from fastapi.testclient import TestClient  # noqa: E402

from app.server import app  # noqa: E402

client = TestClient(app)


def test_health_names_the_stack():
    body = client.get("/health").json()
    assert body["ok"] is True
    assert body["stack"]["sample_mode"] is True and body["stack"]["domain"] == "project_memory"


def test_run_arbitrates_a_proposal():
    payload = {"run_id": "t-server-1", "input": {
        "content": "Book a booth at Batimat Paris for 11,500 EUR.", "author": "Inès Roux",
        "ai_tool": "ChatGPT", "kind": "decision", "topic": "marketing_spend"}, "options": {"profile": "full"}}
    res = client.post("/run", json=payload).json()
    assert res["status"] == "success"
    assert res["output"]["decision"] == "escalate"
    assert "S05" in res["output"]["citations"]


def test_finance_source_and_console():
    budgets = client.get("/finance/budgets").json()["budgets"]
    assert {b["department"] for b in budgets} >= {"marketing", "ops"}
    page = client.get("/console")
    assert page.status_code == 200 and "Steward" in page.text
