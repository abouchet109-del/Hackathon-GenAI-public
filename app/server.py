"""HTTP entry point: POST /run takes one item (JSON) and returns the structured decision."""
from __future__ import annotations

from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .console import router as console_router
from .pipeline import Harness

app = FastAPI(title="OSEF decision agent", version="0.1.0")
app.include_router(console_router)
CONSOLE_HTML = Path(__file__).resolve().parent / "static" / "console.html"
# Steward design-system kit (tokens, components, self-hosted fonts, icon sprite, logo).
app.mount("/static/brand", StaticFiles(directory=Path(__file__).resolve().parent / "static" / "brand"), name="brand")
_harness: Harness | None = None


@app.get("/console", include_in_schema=False)
def console() -> FileResponse:
    """OSEF Steward web console (CEO queue, shared truth, context preview, onboarding)."""
    return FileResponse(CONSOLE_HTML, media_type="text/html")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/console")


FINANCE_CSV = Path(__file__).resolve().parents[1] / "domains" / "project_memory" / "data" / "finance.csv"


@app.get("/finance/budgets")
def finance_budgets() -> dict:
    """The "Brikk finance API": a REST source that Zetaris federates next to Postgres and the MinIO drive."""
    import csv

    with FINANCE_CSV.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["budget_eur"] = float(r["budget_eur"])
        r["committed_eur"] = float(r["committed_eur"])
    return {"budgets": rows}


def harness() -> Harness:
    global _harness
    if _harness is None:
        _harness = Harness()
    return _harness


@app.get("/health")
def health() -> dict:
    return {"ok": True, "stack": harness().describe()}


@app.post("/run")
def run(payload: dict = Body(...)) -> dict:
    """Accepts {"run_id": "...", "input": {item}, "options": {"profile": "full"}} or a bare item."""
    item = payload.get("input", payload)
    options = payload.get("options", {}) or {}
    return harness().run(item, profile=options.get("profile", "full"), run_id=payload.get("run_id"))


@app.post("/learn")
def learn(payload: dict = Body(...)) -> dict:
    """Owner correction: {"input": {item}, "decision": "pay", "note": "..."}"""
    return harness().learn(payload["input"], payload["decision"], payload.get("note", ""))
