"""Text mode: how Steward's results read inside a person's AI, in a terminal and in the console's text panel.

The format is the one of the Steward design rules (section 12): a header `§ Steward · VERDICT · ID`, then labels
aligned on 12 characters in a fixed order (Proposal, Conflicts, Why, Confidence, Source, Next, Limits), nothing
wider than 80 characters, no colour and no emoji. Current values are written **bold**, replaced ones ~~struck~~.
"""
from __future__ import annotations

import os
import textwrap
from datetime import datetime

WIDTH = 80
LABEL = 12
VERDICT_WORD = {"store": "STORED", "supersede": "SUPERSEDED", "clarify": "CLARIFY", "escalate": "ESCALATED",
                "reject": "REJECTED", "redact": "REDACTED", "quarantine": "QUARANTINED", "withdrawn": "REJECTED"}
NEXT = {
    "store": "Nothing to do now. The record is in the shared truth.",
    "supersede": "Nothing to do now. The old value stays in the history, struck through.",
    "clarify": "Ask the user: was this an error or a real change? Send the answer with answer_clarification.",
    "escalate": "Nothing to do now. The CEO's ruling will appear in whats_new.",
    "reject": "Nothing to do now. Tell the user what the record says instead.",
    "redact": "Nothing to do now. The secret was masked; the fact is kept.",
    "quarantine": "Tell the user the text tried to instruct AI tools; it was isolated, not stored.",
    "withdrawn": "Nothing to do now. The proposal was withdrawn; the record is unchanged.",
}


def _line(label: str, value: str) -> list[str]:
    """One labelled line, wrapped under 80 characters with the continuation lines indented."""
    value = " ".join(str(value).split())
    if not value:
        return []
    wrapped = textwrap.wrap(value, WIDTH - LABEL) or [""]
    out = [f"{label:<{LABEL}}{wrapped[0]}"]
    out += [" " * LABEL + w for w in wrapped[1:]]
    return out


def _when(ts: str | None) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%d %b %H:%M") if ts else ""
    except ValueError:
        return ts or ""


def verdict_text(res: dict, *, content: str, author: str, ai_tool: str, department: str | None = None,
                 at: str | None = None, to: str | None = None) -> str:
    """A tool result with a verdict (remember, observe items, resolve, answer)."""
    decision = res.get("decision") or "reject"
    word = VERDICT_WORD.get(decision, decision.upper())
    applied = res.get("applied") or {}
    ident = applied.get("memory_id") or applied.get("journal_id") or "pending"
    head = f"§ Steward · {word}" + (f" to {to}" if to else "") + f" · {ident}"
    lines = [head]
    lines += _line("Proposal", content)
    cites = [c for c in (res.get("citations") or []) if c]
    rules = [c for c in cites if c[:1] in "SP" and c[1:].isdigit()]
    records = [c for c in cites if c not in rules]
    if records:
        lines += _line("Conflicts" if decision in {"clarify", "escalate", "reject"} else "Record", " ".join(records))
    if rules:
        lines += _line("Rule", " ".join(rules))
    why = " ".join(str(res.get("why") or res.get("summary") or "").split())
    if why and why[-1] not in ".!?":
        why += "."
    lines += _line("Why", why)
    conf = res.get("confidence")
    if conf is not None:
        lines += _line("Confidence", f"{float(conf):.2f}")
    dept = str(department).capitalize() if department else ""
    source = " · ".join(x for x in (author, dept, f"via {ai_tool}" if ai_tool else "", _when(at)) if x)
    lines += _line("Source", source)
    nxt = NEXT.get(decision, "Nothing to do now.")
    if decision == "clarify" and res.get("current_record"):
        nxt = f"The record says: {res['current_record']} " + nxt
    if res.get("alerts_sent"):
        nxt += " Alerts sent to " + ", ".join(res["alerts_sent"]) + "."
    lines += _line("Next", nxt)
    lines += _line("Limits", limits_line(res.get("stack")))
    return "\n".join(lines)


def limits_line(stack: dict | None) -> str:
    if not stack:
        return ""
    bits = []
    if stack.get("data", "").startswith("sample"):
        bits.append("governance data read from the sample copy, not Zetaris")
    if "fallback" in stack.get("memory", ""):
        bits.append("memory is the local fallback, not H-MEM")
    if stack.get("llm", "").startswith("offline"):
        bits.append("no model call (offline path)")
    if not bits:
        return "Governance read live from Zetaris at this call; not re-checked since."
    text = "; ".join(bits) + "."
    return text[0].upper() + text[1:]


def context_text(ctx: dict, name: str, task: str) -> str:
    """A context result reads as composed: its first line is already `§ Steward · context for <who> · task: ...`
    (domains/project_memory/context.py::compose_context); each body line cites an [id]."""
    text = ctx.get("context") or ""
    if not text.startswith("§ Steward"):
        text = f"§ Steward · context for {name}" + (f" · task: {task}" if task else "") + "\n" + text
    return text


def _prov(rec: dict) -> str:
    bits = [rec.get("author") or rec.get("source") or "", rec.get("ai") or rec.get("ai_tool") or "", _when(rec.get("at"))]
    return " · ".join(b for b in bits if b)


def history_text(why: dict) -> str:
    """why(topic): current value highlighted, replaced values struck through, oldest first, never collapsed."""
    lines = [f"§ Steward · history · {why.get('topic', '')}"]
    for h in why.get("history") or []:
        if h.get("is_policy"):
            lines += _line("Policy", f"[{h['id']}] {h['content']}")
        elif h.get("superseded_by"):
            lines += _line("Replaced", f"[{h['id']}] ~~{h['content']}~~ by {h['superseded_by']}")
        else:
            lines += _line("Current", f"[{h['id']}] **{h['content']}**" + (f" ({_prov(h)})" if _prov(h) else ""))
    for j in why.get("steward_journal") or []:
        word = VERDICT_WORD.get(j.get("decision"), str(j.get("decision") or "").upper())
        lines += _line("Journal", f"{j.get('journal_id', '')} {word}: {j.get('reason') or ''} ({j.get('author') or ''}"
                                  f"{', ' + j['ai_tool'] if j.get('ai_tool') else ''})")
    if len(lines) == 1:
        lines += _line("Current", "no record on this topic yet.")
    return "\n".join(lines)


def recall_text(memories: list[dict], query: str) -> str:
    lines = [f"§ Steward · recall · {query[:60]}"]
    for m in memories:
        kind = "Policy" if m.get("is_policy") else (m.get("kind") or "record").capitalize()
        lines += _line(kind, f"[{m['id']}] {m['content']}" + (f" ({_prov(m)})" if _prov(m) else ""))
    if len(lines) == 1:
        lines += _line("Record", "nothing in the shared truth matches; the answer is not company knowledge.")
    return "\n".join(lines)


def brief_text(brief: dict) -> str:
    lines = ["§ Steward · shared truth · Brikk"]
    for topic, records in (brief.get("topics") or {}).items():
        for r in records:
            lines += _line((r.get("kind") or "record").capitalize(), f"[{r['id']}] {topic}: {r['content']}")
    for p in brief.get("ceo_policies") or []:
        lines += _line("Policy", f"[{p['id']}] {p['content']}" + (f" (covers {p['scope']})" if p.get("scope") else ""))
    n = brief.get("pending_escalations") or 0
    lines += _line("Queue", f"{n} {'escalation waits' if n == 1 else 'escalations wait'} for the CEO.")
    return "\n".join(lines)


def alerts_text(alerts: list[dict], name: str) -> str:
    lines = [f"§ Steward · alerts for {name}"]
    for a in alerts:
        lines += _line("Alert", f"{a.get('decision_id', '')} {a.get('message', '')}".strip())
    if not alerts:
        lines += _line("Alert", "No decision changed your work since your last session.")
    lines += _line("Next", "Tell the user before anything else, then call whats_new." if alerts
                   else "Nothing to do now. Call whats_new for the rest.")
    return "\n".join(lines)


def profile_text(prof: dict) -> str:
    lines = [f"§ Steward · profile saved · {prof.get('name', '')}"]
    lines += _line("Role", f"{prof.get('role', '')} ({prof.get('department', '')}), level {prof.get('level', '')}")
    lines += _line("Follows", ", ".join(prof.get("topics_followed") or []) or "the topics of the role")
    lines += _line("Context", f"{prof.get('focus', '')} focus, detail level {prof.get('detail_level', '')}")
    for w in prof.get("warnings") or []:
        lines += _line("Ignored", w)
    lines += _line("Limits", "The questionnaire shapes the context; authority still comes from the team directory.")
    lines += _line("Next", "Start each session with my_alerts, then whats_new; call my_context with the user's task.")
    return "\n".join(lines)


def whats_new_text(news: dict, name: str) -> str:
    lines = [f"§ Steward · what's new for {name}" + (f" · since {news['since']}" if news.get("since") else " · first visit")]
    for c in news.get("changes") or []:
        what = c.get("what") or ""
        if c.get("replaces"):
            what = f"~~{c['replaces']}~~ **{what}**"
        lines += _line("Recent", f"{c.get('id', '')} {what}".strip())
    for w in news.get("waiting_for_you") or []:
        lines += _line("Open", f"{w.get('journal_id', '')} {w.get('question') or w.get('content', '')}".strip())
    for s in news.get("signals") or []:
        lines += _line("Signal", s.get("signal") or "")
    if len(lines) == 1:
        lines += _line("Recent", "nothing changed since your last session.")
    lines += _line("Ask why", 'why("<topic>") for the full history of a topic')
    return "\n".join(lines)


# ----- terminal: the same header, three ANSI styles only (design rules, section 12) -----
HL, ST = "\x1b[30;103m", "\x1b[9;2m"
REC, HUM, BLK, DIM, RST = "\x1b[32m", "\x1b[35m", "\x1b[31m", "\x1b[2m", "\x1b[0m"
COLOUR = {"store": REC, "supersede": REC, "clarify": HUM, "escalate": HUM, "quarantine": BLK, "redact": BLK,
          "reject": DIM}


def cli_line(res: dict, content: str = "") -> str:
    """The terminal line: the same header as text mode, then the Proposal highlighted (HL) when it entered the
    record, struck (ST) when the record replaced an older value, and the citations dimmed."""
    plain = os.getenv("NO_COLOR") or not os.isatty(2)
    decision = res.get("decision") or "reject"
    word = VERDICT_WORD.get(decision, decision.upper())
    applied = res.get("applied") or {}
    ident = applied.get("memory_id") or applied.get("journal_id") or "pending"
    head = f"§ Steward · {word}" + (" to CEO" if decision == "escalate" else "") + f" · {ident}"
    cites = " ".join(res.get("citations") or [])
    value = " ".join(str(content or "").split())[:60]
    if plain:
        return f"{head}" + (f"  {value}" if value else "") + (f"  [{cites}]" if cites else "")
    styled = f"{HL}{value}{RST}" if decision in {"store", "supersede", "redact"} and value else value
    if decision == "supersede" and applied.get("supersedes"):
        styled = f"{ST}{applied['supersedes']}{RST} {styled}"
    return (f"§ Steward · {COLOUR.get(decision, '')}{word}{RST}" + (" to CEO" if decision == "escalate" else "")
            + f" · {ident}" + (f"  {styled}" if styled else "") + (f"  {DIM}[{cites}]{RST}" if cites else ""))
