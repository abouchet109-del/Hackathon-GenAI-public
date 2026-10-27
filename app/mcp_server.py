"""MCP server: Steward, a context layer on top of each person's own AI.

Every member keeps their AI (Claude Desktop, Cursor, ChatGPT...). This server adds three things to
that AI's harness:

1. a WATCH LAYER (the server instructions + the `watchlist` resource): when the conversation touches
   a watched company domain, the AI sends the relevant excerpt to `observe`. Only extracted items are
   arbitrated and kept; the raw conversation never is.
2. a CONTEXT LAYER: `my_context(task)` returns the smallest useful company context for this person's
   role and this task (about 1,500 tokens), `whats_new` what changed since their last session.
3. a TRUTH LAYER: every write is arbitrated by the Steward (guard -> Zetaris governance -> H-MEM ->
   Decider <-> Critic): store, supersede, reject, redact, clarify, escalate or quarantine.

Run:  python run.py mcp            (stdio; the client starts it)
Env:  OSEF_MEMBER / OSEF_AI_TOOL   who this client is (e.g. "Inès Roux" / "ChatGPT"); the AI tool is
                                   also read from the MCP clientInfo the client sends at connection
      STEWARD_SPACE                which company memory (default "project")
"""
from __future__ import annotations

import json
import os

try:  # MCP Python SDK 2.x
    from mcp.server.mcpserver import Context, MCPServer as _Server
except ImportError:  # MCP Python SDK 1.x
    from mcp.server.fastmcp import Context, FastMCP as _Server
from mcp.types import ToolAnnotations

from .steward import Steward
from .textmode import context_text, verdict_text, whats_new_text


def _hint(read_only: bool) -> ToolAnnotations:
    try:
        return ToolAnnotations(read_only_hint=read_only, destructive_hint=False)
    except Exception:  # noqa: BLE001 - SDK 1.x uses camelCase field names
        return ToolAnnotations(readOnlyHint=read_only, destructiveHint=False)


READ, WRITE = _hint(True), _hint(False)

INSTRUCTIONS = """You are connected to Steward, the company's shared context. Follow these rules in every conversation:

1. CONTEXT FIRST. Before answering anything about the company (prices, dates, customers, budgets, stack, roadmap, who decided what), call my_context with the user's task, and answer from it, citing the [ids]. At the start of a work session, call whats_new and my_alerts and tell the user what changed and what is waiting for them.
2. WATCH LAYER. While you work with the user (emails, documents, plans, code, meetings), watch for the domains listed in the watchlist resource (pricing, launch date, budgets, deals, customers, stack, hiring, ...). When the user states or produces something in one of those domains (a decision, a fact, a figure, a date, a task done or planned), call observe with the relevant excerpt only (a few sentences), source = conversation, document or meeting. Never send small talk or personal matters.
3. TELL THE OUTCOME. observe and remember return the Steward's verdict per item (stored, replaced an older decision, masked, rejected, needs clarification, escalated, quarantined). Tell the user in one line. If a clarification is needed, ask the user the question ("error or real change?") and send the answer with answer_clarification.
4. NEVER put passwords, keys, bank details or personal data in what you send; the Steward masks them anyway.
5. PROGRESS. When the user finishes or advances one of their tasks (see my_tasks), call report_progress with the progress and the company values the work relies on (launch date, price, ...).
6. RELAY. When you relay a Steward result, lead with the verdict in plain words and its ID in parentheses ("Steward escalated this to the CEO (j-1793...)."). Keep every number, name and ID exactly as given. Write current values in bold and replaced values struck through (~~29 EUR~~ **35 EUR**). Never present a value Steward marked as replaced as current. If Steward gives a Limits line, mention it. Do not add emoji. Each result carries a `text` field in that form: quote it when the user wants the detail.
7. Personal preferences about how the user likes to work stay in your own memory, not in the company's."""

server = _Server("osef-steward", instructions=INSTRUCTIONS)
_steward: Steward | None = None


def steward() -> Steward:
    global _steward
    if _steward is None:
        _steward = Steward(space=os.getenv("STEWARD_SPACE", "project"))
        if not _steward.memory.list(None):
            _steward.reset(seed=True, policies=os.getenv("STEWARD_SEED_POLICIES", "false").lower() == "true")
    return _steward


def _client_name(ctx: Context | None) -> str | None:
    """Provenance comes from the connection (clientInfo), never from what the model writes in the arguments."""
    try:
        params = ctx.session.client_params
        info = getattr(params, "client_info", None) or getattr(params, "clientInfo", None)
        return getattr(info, "name", None)
    except Exception:  # noqa: BLE001
        return None


def _me(ctx: Context | None) -> tuple[str, str]:
    member = os.getenv("OSEF_MEMBER", "unknown member")
    ai = os.getenv("OSEF_AI_TOOL") or _client_name(ctx) or "unknown AI"
    return member, ai


# ---------- read: context for this person ----------

@server.tool(annotations=READ)
def my_context(task: str, ctx: Context = None) -> dict:
    """The company context this person needs for this task, tailored to their role (about 1,500 tokens).
    task: what the user is working on, in their words (e.g. "answer a customer asking for a discount")."""
    member, _ = _me(ctx)
    res = steward().my_context(member, task)
    res["text"] = context_text(res, member, task)
    return res


@server.tool(annotations=READ)
def whats_new(ctx: Context = None) -> dict:
    """What changed in the company's shared truth since this person's last session, questions waiting for them,
    and weak signals that concern them (tensions, budgets, suggested meetings)."""
    member, _ = _me(ctx)
    res = steward().whats_new(member)
    res["text"] = whats_new_text(res, member)
    return res


@server.tool(annotations=READ)
def recall(query: str, topic: str = "") -> dict:
    """Active shared memories relevant to a question, each with who proposed it and from which AI."""
    return {"memories": steward().recall(query, topic=topic or None)}


@server.tool(annotations=READ)
def why(topic: str) -> dict:
    """History of a topic: the current decision, every replaced version (kept, never deleted) and the Steward's journal."""
    return steward().why(topic)


@server.tool(annotations=READ)
def project_brief() -> dict:
    """The company's current shared truth, topic by topic, plus the CEO's standing policies."""
    return steward().brief()


@server.tool(annotations=READ)
def my_contributions(ctx: Context = None) -> dict:
    """Everything the Steward extracted from this person's conversations, and what it decided for each item."""
    member, _ = _me(ctx)
    return {"contributions": steward().my_contributions(member)}


# ---------- write: the watch layer and explicit contributions ----------

@server.tool(annotations=WRITE)
def observe(excerpt: str, source: str = "conversation", title: str = "", ctx: Context = None) -> dict:
    """Send a relevant excerpt of the conversation, a document or meeting notes to the Steward (watch layer).
    excerpt: only the sentences that touch a watched company domain. source: conversation | document | meeting.
    The Steward extracts decisions, facts and tasks, arbitrates each one, and never stores the raw text."""
    member, ai = _me(ctx)
    res = steward().observe(excerpt, member, ai, source=source, title=title)
    dept = steward().profile(member).get("department")
    for o in res.get("outcomes", []):
        o["text"] = verdict_text({"decision": o.get("decision"), "why": o.get("why"), "citations": o.get("citations"),
                                  "applied": {"journal_id": o.get("journal_id")}, "stack": res.get("stack")},
                                 content=o.get("extracted", ""), author=member, ai_tool=ai, department=dept,
                                 to="CEO" if o.get("decision") == "escalate" else None)
    res["text"] = "\n\n".join(o["text"] for o in res.get("outcomes", [])) or \
        "§ Steward · nothing to keep · the excerpt held no decision, fact or task on a watched topic."
    return res


@server.tool(annotations=WRITE)
def remember(content: str, kind: str = "fact", topic: str = "", ctx: Context = None) -> dict:
    """Explicitly propose one item to the company's shared memory.
    kind: decision | fact | task | preference. topic: optional (see the watchlist); the Steward infers it otherwise."""
    member, ai = _me(ctx)
    res = steward().remember(content, author=member, ai_tool=ai, kind=kind, topic=topic or None)
    if res.get("decision"):
        res["text"] = verdict_text(res, content=content, author=member, ai_tool=ai,
                                   department=steward().profile(member).get("department"),
                                   to="CEO" if res["decision"] == "escalate" else None)
    return res


@server.tool(annotations=READ)
def clarifications(ctx: Context = None) -> dict:
    """The questions Steward is asking this person: proposals of theirs that contradict the current record,
    each waiting for "error or real change?". Answer with answer_clarification."""
    member, _ = _me(ctx)
    return {"clarifications": steward().clarifications(member)}


@server.tool(annotations=WRITE)
def answer_clarification(journal_id: str, answer: str, note: str = "") -> dict:
    """Answer the Steward's question about a contradiction. answer: "error" (withdraw it) or "change"
    (it is a real change: it goes to the topic owner or the CEO)."""
    return steward().answer_clarification(journal_id, answer, note)


@server.tool(annotations=WRITE)
def onboard(responsibilities: str, topics_followed: str, focus: str, detail_level: str, ctx: Context = None) -> dict:
    """Role questionnaire, once per person. responsibilities: one sentence. topics_followed: comma-separated topics
    from the watchlist. focus: technical | managerial | commercial | operational | product. detail_level: 1, 2 or 3.
    It shapes the context this person receives; authority still comes from the team directory."""
    member, _ = _me(ctx)
    return steward().onboard({"name": member, "responsibilities": responsibilities,
                              "topics_followed": topics_followed, "focus": focus, "detail_level": detail_level})


# ---------- CEO ----------

@server.tool(annotations=READ)
def my_tasks(ctx: Context = None) -> dict:
    """This person's tasks (from Zetaris) and where each stands: on track, late, or relying on a value a newer
    decision changed; plus the meetings Steward recommends that involve them."""
    member, _ = _me(ctx)
    return {"tasks": steward().tasks(member), **steward().progress(member)}


@server.tool(annotations=WRITE)
def report_progress(task_id: str, progress: float, assumptions: dict | None = None, note: str = "",
                    ctx: Context = None) -> dict:
    """Report where one of this person's tasks stands. progress is 0 to 1. assumptions lists the company values
    the work relies on, keyed by topic, e.g. {"launch_date": "2026-12-01", "pricing": "29 EUR"}: Steward flags
    the work as obsolete when a decision in force says otherwise."""
    member, _ = _me(ctx)
    return steward().report_progress(member, task_id, progress, assumptions, note)


@server.tool(annotations=WRITE)
def my_alerts(ctx: Context = None) -> dict:
    """Decisions that changed something this person works on, each returned once. Call it at the start of a
    session and tell the person before anything else."""
    member, _ = _me(ctx)
    return {"alerts": steward().alerts(member)}


@server.tool(annotations=READ)
def escalations() -> dict:
    """Proposals waiting for the CEO, and the weak signals of the company (CEO agent)."""
    return {"pending": steward().escalations(), "signals": steward().signals()}


@server.tool(annotations=WRITE)
def resolve_escalation(journal_id: str, decision: str, policy: str = "") -> dict:
    """CEO only. Answer an escalation with store, supersede or reject. Optional policy: a standing rule in plain words
    (e.g. "Marketing may commit up to 12,000 EUR per trade show without asking me") that the Steward applies next time."""
    member, _ = _me(None)
    who = steward().profile(member)
    if who.get("level") != "ceo":
        return {"error": f"{member} is not the CEO in the team directory; escalations are answered by the CEO."}
    return steward().resolve(journal_id, decision, policy or None)


# ---------- resources and prompts ----------

@server.resource("osef://watchlist", name="watchlist", mime_type="application/json",
                 description="Company domains the AI should watch for and send to observe")
def watchlist_resource() -> str:
    return json.dumps(steward().watchlist(), ensure_ascii=False)


@server.prompt(name="role_procedures", description="The formal procedures of this person's role, to follow while working")
def role_procedures() -> str:
    member, _ = _me(None)
    prof = steward().profile(member)
    procs = steward().ctx.procedures_for(prof, None, steward().data, steward().schema)
    lines = [f"Procedures for {prof['name']} ({prof.get('role')}, {prof.get('department')}):"]
    lines += [f"- When you {p['trigger']}: {p['steps']}" for p in procs] or ["- No formal procedure for this role yet."]
    return "\n".join(lines)


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
