"""Web console for Steward: escalations, shared truth, clarifications, context preview, onboarding.

The people of the team keep working in their own AI (MCP); this page is for the CEO, for the
judges and for the demo. Every endpoint is a thin wrapper over app/steward.py.

The console is a trusted local surface: it has no login, so `run.py serve` binds 127.0.0.1 by default,
and the person behind it is named by STEWARD_CONSOLE_USER (the CEO of the team directory when unset).
Escalations are resolved only when that person is the CEO; a clarification is answered only by its author
or by the CEO. "Simulate an AI" takes the author from the form on purpose: it is a demo device that plays
another member's AI, and its proposals go through the same arbitration as an MCP call.
"""
from __future__ import annotations

import json
import os
import re

from fastapi import APIRouter, Body, HTTPException

from .steward import Steward

router = APIRouter(prefix="/api", tags=["steward-console"])
_steward: Steward | None = None


def steward() -> Steward:
    global _steward
    if _steward is None:
        _steward = Steward(space=os.getenv("STEWARD_SPACE", "project"))
        _steward.seed_if_empty(policies=os.getenv("STEWARD_SEED_POLICIES", "false").lower() == "true")
    return _steward


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error).strip("'\"")) from error


def operator() -> dict:
    """Who is behind the console: STEWARD_CONSOLE_USER, else the CEO of the team directory."""
    st = steward()
    name = os.getenv("STEWARD_CONSOLE_USER", "").strip()
    if not name:
        rows = st.data.run_sql(f"SELECT name FROM {st.schema}.members WHERE level = 'ceo'", ["name"])
        name = rows[0]["name"] if rows else ""
    return st.profile(name) if name else {"name": "", "level": "unknown"}


def _require_ceo() -> dict:
    who = operator()
    if who.get("level") != "ceo":
        raise HTTPException(status_code=403, detail=f"{who.get('name') or 'the console operator'} is not the CEO "
                            "in the team directory; escalations are answered by the CEO.")
    return who


@router.get("/stack")
def stack() -> dict:
    who = operator()
    return {**steward().describe(), "operator": {"name": who.get("name"), "level": who.get("level")}}


@router.get("/brief")
def brief() -> dict:
    return steward().brief()


@router.get("/escalations")
def escalations() -> dict:
    st = steward()
    return {"pending": st.escalations(), "signals": st.signals()}


@router.post("/resolve")
def resolve(payload: dict = Body(...)) -> dict:
    who = _require_ceo()
    return _guard(steward().resolve, payload.get("journal_id", ""), payload.get("decision", ""),
                  (payload.get("policy") or "").strip() or None, by=who["name"])


@router.get("/clarifications")
def clarifications() -> list[dict]:
    return steward().clarifications()


@router.post("/answer")
def answer(payload: dict = Body(...)) -> dict:
    who = operator()
    return _guard(steward().answer_clarification, payload.get("journal_id", ""), payload.get("answer", ""),
                  payload.get("note", ""), by=who.get("name") or "", ceo=who.get("level") == "ceo")


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
    """Simulate an AI: the operator plays a member's AI. Only the CEO may play someone else; the journal keeps
    who entered the proposal (`entered_by`) next to the author it was entered for."""
    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    who = operator()
    author = (payload.get("author") or who.get("name") or "unknown member").strip()
    if author.lower() != (who.get("name") or "").lower() and who.get("level") != "ceo":
        raise HTTPException(status_code=403, detail=f"{who.get('name') or 'the console operator'} is not the CEO: "
                            f"the console can only propose as {who.get('name')}, not as {author}.")
    return _guard(steward().remember, content, author, payload.get("ai_tool") or "unknown AI",
                  payload.get("kind") or "fact", payload.get("topic") or None, entered_by=who.get("name"))


_RUN_ID = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


@router.get("/trace/{run_id}")
def trace(run_id: str) -> dict:
    """One trace file, read-only, as the lines the harness wrote (logs/trace-<run_id>.jsonl)."""
    if not _RUN_ID.match(run_id):
        raise HTTPException(status_code=400, detail="run_id must be a file stem: letters, digits, . _ -")
    path = steward().h.s.log_dir / f"trace-{run_id}.jsonl"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"no trace {run_id}")
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            lines.append(json.loads(raw))
        except ValueError:
            continue
    return {"run_id": run_id, "file": str(path.relative_to(steward().h.s.log_dir.parent)), "lines": lines}


@router.get("/journal")
def journal() -> list[dict]:
    st = steward()
    rows = st.logic.journal(st.memory)
    return [{k: v for k, v in r.items() if k != "item"} for r in reversed(rows[-50:])]
