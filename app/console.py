"""Web console for the OSEF Steward: CEO queue, shared truth, clarifications, context preview, onboarding.

The people of the team keep working in their own AI (MCP); this page is for the CEO, for the
judges and for the demo. Every endpoint is a thin wrapper over app/steward.py.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Body, HTTPException

from .steward import Steward

router = APIRouter(prefix="/api", tags=["steward-console"])
_steward: Steward | None = None


def steward() -> Steward:
    global _steward
    if _steward is None:
        _steward = Steward(space=os.getenv("STEWARD_SPACE", "project"))
        if not _steward.memory.list(None):
            _steward.reset(seed=True, policies=os.getenv("STEWARD_SEED_POLICIES", "false").lower() == "true")
    return _steward


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error).strip("'\"")) from error


@router.get("/stack")
def stack() -> dict:
    return steward().describe()


@router.get("/brief")
def brief() -> dict:
    return steward().brief()


@router.get("/escalations")
def escalations() -> dict:
    st = steward()
    return {"pending": st.escalations(), "signals": st.signals()}


@router.post("/resolve")
def resolve(payload: dict = Body(...)) -> dict:
    return _guard(steward().resolve, payload.get("journal_id", ""), payload.get("decision", ""),
                  (payload.get("policy") or "").strip() or None)


@router.get("/clarifications")
def clarifications() -> list[dict]:
    return steward().clarifications()


@router.post("/answer")
def answer(payload: dict = Body(...)) -> dict:
    return _guard(steward().answer_clarification, payload.get("journal_id", ""), payload.get("answer", ""),
                  payload.get("note", ""))


@router.get("/why/{topic}")
def why(topic: str) -> dict:
    return steward().why(topic)


@router.get("/watchlist")
def watchlist() -> list[dict]:
    return steward().watchlist()


@router.get("/members")
def members() -> list[dict]:
    st = steward()
    cols = ["member_id", "name", "department", "role", "ai_tool", "level"]
    return st.data.run_sql(f"SELECT {', '.join(cols)} FROM {st.schema}.members", cols)


@router.get("/context")
def context(name: str, task: str = "") -> dict:
    return _guard(steward().my_context, name, task)


@router.get("/whats_new")
def whats_new(name: str) -> dict:
    return _guard(steward().whats_new, name, advance=False)


@router.get("/onboarding")
def onboarding() -> list[dict]:
    return steward().onboarding_questions()


@router.post("/onboard")
def onboard(payload: dict = Body(...)) -> dict:
    return _guard(steward().onboard, payload.get("answers", payload))


@router.post("/remember")
def remember(payload: dict = Body(...)) -> dict:
    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    return _guard(steward().remember, content, payload.get("author") or "unknown member",
                  payload.get("ai_tool") or "unknown AI", payload.get("kind") or "fact", payload.get("topic") or None)


@router.get("/journal")
def journal() -> list[dict]:
    st = steward()
    rows = st.logic.journal(st.memory)
    return [{k: v for k, v in r.items() if k != "item"} for r in reversed(rows[-50:])]
