"""Deterministic logic for the 'admin' domain: parse an item, evaluate the rules, read memory tags.

The model reasons on top of this; this code gives it reliable facts and gives the
harness a safe fallback when no model is reachable. Swap this file with the domain.
"""
from __future__ import annotations

import re
from datetime import date

AMOUNT = re.compile(r"amount due:\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*eur", re.I)
DUE = re.compile(r"(?:due date:|before)\s*(\d{4}-\d{2}-\d{2})", re.I)
INCREASE = re.compile(r"increase of\s*(\d{1,3})\s*%", re.I)
URL = re.compile(r"https?://([a-z0-9.\-]+)", re.I)
CREDENTIALS = re.compile(r"\b(password|card number|bank login|expiry date|login here|log in here)\b", re.I)
PAY_WORDS = re.compile(r"\b(pay|payment|fee|refund|settle)\b", re.I)
REQUEST_WORDS = re.compile(r"\b(reply|confirm|sign|return|send|answer|register)\b", re.I)
DOC_WORDS = re.compile(r"\b(documents?|receipt|proof|declaration)\b", re.I)


def sender_domain(address: str) -> str:
    return address.split("@")[-1].strip().lower()


def intake(item: dict) -> dict:
    """Structure an incoming item into facts. No model involved."""
    text = f"{item.get('subject', '')}. {item.get('body', '')}"
    amount = AMOUNT.search(text)
    due = DUE.search(text)
    increase = INCREASE.search(text)
    domain = sender_domain(item.get("from", ""))
    link_domains = sorted({m.group(1).lower() for m in URL.finditer(text)})
    return {
        "item_id": item.get("id"),
        "sender": item.get("from"),
        "sender_domain": domain,
        "subject": item.get("subject", ""),
        "amount_eur": float(amount.group(1).replace(",", ".")) if amount else None,
        "due_date": due.group(1) if due else None,
        "price_increase_pct": int(increase.group(1)) if increase else None,
        "link_domains": link_domains,
        "asks_credentials": bool(CREDENTIALS.search(text)),
        "mentions_payment": bool(PAY_WORDS.search(text)),
        "requests_action": bool(REQUEST_WORDS.search(text)),
        "mentions_documents": bool(DOC_WORDS.search(text)),
        "received_at": item.get("received_at"),
    }


def enrich_with_sender(facts: dict, sender_row: dict | None) -> dict:
    facts = dict(facts)
    facts["sender_known"] = sender_row is not None
    facts["sender_verified"] = bool(sender_row and str(sender_row.get("verified")).lower() == "yes")
    facts["organisation"] = sender_row.get("organisation") if sender_row else None
    facts["item_type"] = sender_row.get("category") if sender_row and sender_row.get("category") != "unknown" else _guess_type(facts)
    verified = sender_row.get("sender_domain") if facts["sender_verified"] else None
    facts["link_on_unverified_domain"] = any(d != verified and not (verified and d.endswith("." + verified))
                                             for d in facts["link_domains"])
    return facts


def _guess_type(facts: dict) -> str:
    if facts["amount_eur"] is not None:
        return "invoice"
    return "unknown"


def _days_until(due: str | None, today: str | None) -> int | None:
    if not due:
        return None
    try:
        return (date.fromisoformat(due) - date.fromisoformat(today or "2026-10-20")).days
    except ValueError:
        return None


def evaluate_rules(facts: dict, rules: list[dict], profile: dict) -> list[dict]:
    """Return the rules whose condition holds, each with its decision. Pure Python, auditable."""
    limit = float(profile.get("auto_pay_limit", 0) or 0)
    t = facts.get("item_type")
    amount = facts.get("amount_eur")
    days = _days_until(facts.get("due_date"), facts.get("received_at"))
    checks = {
        "R01": t == "invoice" and facts["sender_verified"] and amount is not None and amount <= limit and (days is None or days <= 21),
        "R02": t == "invoice" and facts["sender_verified"] and amount is not None and amount > limit,
        "R03": t == "invoice" and not facts["sender_verified"],
        "R04": facts["asks_credentials"] or (facts["link_on_unverified_domain"] and facts["mentions_payment"])
               or (facts["link_on_unverified_domain"] and not facts["sender_verified"]),
        "R05": t == "housing_aid" and facts["mentions_documents"],
        "R06": t == "tax_notice" and amount is None,
        "R07": t == "tax_notice" and amount is not None,
        "R08": t == "school_admin" and facts["requests_action"],
        "R09": t == "marketing",
        "R10": t == "insurance_renewal" and (facts.get("price_increase_pct") or 0) > 10,
        "R11": t == "insurance_renewal" and facts.get("price_increase_pct") is not None and facts["price_increase_pct"] <= 10,
        "R12": t == "bank_notice" and not facts["asks_credentials"],
        "R13": t == "appointment" and facts["requests_action"],
    }
    matched = [dict(r) for r in rules if checks.get(r["rule_id"], False)]
    # A scam rule overrides everything else.
    if any(r["rule_id"] == "R04" for r in matched):
        matched = [r for r in matched if r["rule_id"] == "R04"]
    return matched


def memory_override(facts: dict, memories: list[dict]) -> dict | None:
    """Read structured tags of owner corrections that apply to this sender and amount."""
    for mem in memories:
        tags = {t.split(":", 1)[0]: t.split(":", 1)[1] for t in mem.get("tags", []) if ":" in t}
        if tags.get("sender") != facts.get("sender_domain") or "override" not in tags:
            continue
        if "max_amount" in tags and (facts.get("amount_eur") is None or facts["amount_eur"] > float(tags["max_amount"])):
            continue
        if "max_increase" in tags and (facts.get("price_increase_pct") is None or facts["price_increase_pct"] > int(tags["max_increase"])):
            continue
        return {"decision": tags["override"], "memory_id": mem["id"], "content": mem["content"]}
    return None


def memory_query(facts: dict) -> str:
    return f"{facts.get('item_type')} from {facts.get('sender_domain')} {facts.get('organisation') or ''} {facts.get('subject')}"


def prepared_action(decision: str, facts: dict) -> str:
    org = facts.get("organisation") or facts.get("sender_domain")
    if decision == "pay":
        return f"Prepare a payment of {facts.get('amount_eur')} EUR to {org} before {facts.get('due_date') or 'the due date'} (owner confirms)."
    if decision == "reply":
        return f"Draft a reply to {facts.get('sender')} confirming the request before {facts.get('due_date') or 'the deadline'}."
    if decision == "submit_documents":
        return f"Gather the documents {org} asks for and prepare the upload before {facts.get('due_date') or 'the deadline'}."
    if decision == "block_scam":
        return "Do not click, pay or reply. Mark as phishing and delete."
    if decision == "escalate":
        return "Show the item to the owner with the facts and the open question."
    return "Archive. No action needed."
