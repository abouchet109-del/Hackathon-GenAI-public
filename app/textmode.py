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
                "reject": "REJECTED", "redact": "REDACTED", "quarantine": "QUARANTINED"}
NEXT = {
    "store": "Nothing to do now. The record is in the shared truth.",
    "supersede": "Nothing to do now. The old value stays in the history, struck through.",
    "clarify": "Ask the user: was this an error or a real change? Send the answer with answer_clarification.",
    "escalate": "Nothing to do now. The CEO's ruling will appear in whats_new.",
    "reject": "Nothing to do now. Tell the user what the record says instead.",
    "redact": "Nothing to do now. The secret was masked; the fact is kept.",
    "quarantine": "Tell the user the text tried to instruct AI tools; it was isolated, not stored.",
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
    lines += _line("Why", res.get("why") or res.get("summary") or "")
    conf = res.get("confidence")
    if conf is not None:
        lines += _line("Confidence", f"{float(conf):.2f}")
    source = " · ".join(x for x in (author, department, f"via {ai_tool}" if ai_tool else "", _when(at)) if x)
    lines += _line("Source", source)
    nxt = NEXT.get(decision, "Nothing to do now.")
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
    return "; ".join(bits) + "." if bits else "Governance read live from Zetaris at this call; not re-checked since."


def context_text(ctx: dict, name: str, task: str) -> str:
    """A context result reads as composed: its first line is already `§ Steward · context for <who> · task: ...`
    (domains/project_memory/context.py::compose_context); each body line cites an [id]."""
    text = ctx.get("context") or ""
    if not text.startswith("§ Steward"):
        text = f"§ Steward · context for {name}" + (f" · task: {task}" if task else "") + "\n" + text
    return text


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
    plain = os.getenv("NO_COLOR") or not os.isatty(2)
    decision = res.get("decision") or "reject"
    word = VERDICT_WORD.get(decision, decision.upper())
    applied = res.get("applied") or {}
    ident = applied.get("memory_id") or applied.get("journal_id") or "pending"
    cites = " ".join(res.get("citations") or [])
    if plain:
        return f"§ steward  {word:<11} {ident:<18} {cites}"
    return f"§ steward  {COLOUR.get(decision, '')}{word:<11}{RST} {ident:<18} {DIM}{cites}{RST}"
