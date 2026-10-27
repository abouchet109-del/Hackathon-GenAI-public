"""Deterministic logic for the 'project_memory' domain: Steward.

Every member of a small team works with their own AI (Claude, ChatGPT, Cursor, Gemini...).
Those AIs propose facts and decisions to ONE shared project memory through MCP. For each
proposal the Steward decides: store, supersede, reject, redact, escalate (to the CEO) or
quarantine. This file gives the model reliable facts and gives the harness a safe fallback:

- intake        parses a proposal (kind, topic, amounts, dates, secrets, injection)
- research      reads the org chart, topic ownership and Steward rules through Zetaris
- recall        reads the project memory in H-MEM: active decisions on the topic, CEO policies,
                similar memories (duplicates)
- evaluate_with_memory  applies the Steward rules, which depend on that memory
- apply         writes the outcome to H-MEM (supersedes = replace, never delete) and to the
                Steward journal (escalation queue for the CEO)
"""
from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

AMOUNT = re.compile(r"(\d{1,3}(?:[ ,.]\d{3})+|\d+(?:\.\d+)?)\s*(k)?\s*(?:eur\b|euros?\b|€)", re.I)
DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
SECRET_PATTERNS = {
    "password": re.compile(r"\b(password|passcode|mot de passe)\b\s*(is|:|=)?\s*\S+", re.I),
    "api_key": re.compile(r"\b(sk-[a-z0-9\-_]{8,}|nvapi-[a-z0-9\-_]{8,}|api[_ ]?key\s*[:=]\s*\S+)", re.I),
    "token": re.compile(r"\btoken\s*[:=]\s*\S+", re.I),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b"),
    "phone": re.compile(r"(?<!\d)(?:\+33\s?|0)[1-9](?:[\s.]?\d{2}){4}(?!\d)"),
    "salary": re.compile(r"\b(salary|salaire|gross pay)\b", re.I),
    "health": re.compile(r"\b(sick leave|arrêt maladie|diagnos\w+|medical condition)\b", re.I),
}
INJECTION = re.compile(
    r"(note|message|instruction)s?\s+to\s+(all\s+)?(the\s+)?(ai|assistants?|agents?|ai agents|ai assistants)\b"
    r"|ignore\s+(all\s+|your\s+|the\s+)?(previous|prior)\s+instructions"
    r"|\bai\s+(assistants?|agents?|tools?)\s+(must|should|have to)\b"
    r"|\bfrom now on,?\s+(ai|you|assistants?|agents?)\b"
    r"|</?system>|\[/?inst\]", re.I)
PERSONAL = re.compile(r"\b(i prefer|i like|for me|my own|i want my)\b", re.I)
WORD = re.compile(r"[a-z0-9à-ÿ]+", re.I)
KINDS = {"decision", "fact", "task", "preference"}
TOPIC_HINTS = {
    "pricing": ["price", "pricing", "per user", "annual plan"],
    "launch_date": ["launch"],
    "marketing_spend": ["booth", "trade show", "ads", "sponsor", "campaign"],
    "marketing_budget": ["marketing cap", "marketing envelope"],
    "customer_deals": ["discount"],
    "customers": ["customer", "pilot"],
    "tech_stack": ["backend", "frontend", "hosting", "database", "api"],
    "hiring": ["hire", "recruit"],
    "support_policy": ["support"],
    "roadmap": ["roadmap", "feature", "mvp"],
    "brand": ["brand", "logo", "icon", "color", "tone"],
}


# ---------- small helpers ----------

def _amounts(text: str) -> list[float]:
    out = []
    for m in AMOUNT.finditer(text):
        raw = re.sub(r"[ ,]", "", m.group(1))
        if raw.count(".") == 1 and len(raw.split(".")[1]) == 3:  # 11.500 written the French way
            raw = raw.replace(".", "")
        value = float(raw) * (1000 if m.group(2) else 1)
        out.append(value)
    return out


def _numbers(text: str) -> set[str]:
    """Dates and amounts, normalised: what a fact can contradict a decision on."""
    return set(DATE.findall(text)) | {f"{a:g}" for a in _amounts(text)}


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in WORD.findall(text) if len(w) > 2}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / max(1, len(ta | tb))


def _tags(mem: dict) -> dict:
    out: dict = {}
    for t in mem.get("tags", []):
        if ":" in t:
            k, v = t.split(":", 1)
            out.setdefault(k, v)
        else:
            out[t] = True
    return out


def mask_secrets(text: str) -> str:
    masked = text
    for name, pattern in SECRET_PATTERNS.items():
        if name in {"salary", "health"}:
            continue  # a word, not a value: the Decider decides how to rephrase
        masked = pattern.sub(f"[{name} removed]", masked)
    return masked


def _member_lookup(ref: str) -> dict | None:
    """Used only by learn(), which runs outside a harness run (no data source at hand)."""
    with (HERE / "data" / "members.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if ref and ref.lower() in {row["name"].lower(), row["member_id"].lower()}:
                return row
    return None


# ---------- harness hooks ----------

def intake(item: dict) -> dict:
    content = str(item.get("content") or item.get("body") or "")
    kind = str(item.get("kind") or "fact").lower()
    if kind not in KINDS:
        kind = "fact"
    topic = str(item.get("topic") or "").strip().lower() or _guess_topic(content)
    secrets = [name for name, p in SECRET_PATTERNS.items() if p.search(content)]
    amounts = _amounts(content)
    return {
        "item_id": item.get("id"),
        "author": item.get("author"),
        "author_id": item.get("author_id"),
        "ai_tool": item.get("ai_tool"),
        "kind": kind,
        "topic": topic,
        "content": content,
        "amount_eur": max(amounts) if amounts else None,
        "dates": DATE.findall(content),
        "secrets": secrets,
        # the excerpt's own flags (context.guard_source) count as the item's: a model cannot launder them away
        "injection": bool(INJECTION.search(content)) or "injection" in (item.get("source_flags") or []),
        "personal": kind == "preference" or bool(PERSONAL.search(content)),
        "received_at": item.get("received_at"),
    }


def _guess_topic(content: str) -> str:
    low = content.lower()
    for topic, hints in TOPIC_HINTS.items():
        if any(h in low for h in hints):
            return topic
    return "general"


def trace_summary(item: dict, facts: dict) -> tuple[str, str]:
    head = f"{facts.get('author')} via {facts.get('ai_tool')} | {facts['kind']} on {facts['topic']}"
    body = (f"amount={facts['amount_eur']} dates={facts['dates']} secrets={facts['secrets']} "
            f"injection={facts['injection']} personal={facts['personal']}")
    return head, body


def enrich(facts: dict, member: dict | None, topic: dict | None = None, trust: dict | None = None) -> dict:
    facts = dict(facts)
    facts["author_known"] = member is not None
    facts["department"] = member.get("department") if member else None
    facts["level"] = member.get("level") if member else None
    facts["role"] = member.get("role") if member else None
    facts["topic_known"] = topic is not None
    facts["topic_owner"] = topic.get("owner_department") if topic else None
    facts["singleton_topic"] = bool(topic and str(topic.get("singleton")).lower() == "yes")
    limit = topic.get("budget_limit_eur") if topic else None
    facts["budget_limit_eur"] = float(limit) if limit not in (None, "") else None
    is_ceo = facts["level"] == "ceo"
    in_owner_dept = bool(member and topic and facts["department"] == facts["topic_owner"])
    facts["author_owns_topic"] = bool(member and topic and (is_ceo or (in_owner_dept and facts["level"] != "intern")))
    facts["author_has_authority"] = bool(member and topic and (
        is_ceo or (facts["department"] == facts["topic_owner"] and facts["level"] == "lead")))
    # Trust weight = role x domain (Zetaris table 'trust'): how much this source counts as truth on this topic.
    if trust:
        own = is_ceo or in_owner_dept
        facts["trust_weight"] = float(trust["own_domain_weight" if own else "other_domain_weight"])
    else:
        facts["trust_weight"] = 0.1 if member is None else 0.25
    return facts


def research(facts: dict, data, schema: str, tables: dict) -> dict:
    """Three reads through Zetaris: who the author is, who owns the topic, and the Steward rules."""
    from app.adapters.zetaris import quote  # local import: the pack stays importable on its own
    from app.agents import qualify

    who = facts.get("author_id") or facts.get("author") or ""
    sql_member = (f"SELECT member_id, name, department, role, ai_tool, level FROM {qualify(schema, tables['members'])} "
                  f"WHERE name = {quote(who)} OR member_id = {quote(who)}")
    sql_topic = (f"SELECT topic, owner_department, singleton, budget_limit_eur, description FROM {qualify(schema, tables['topics'])} "
                 f"WHERE topic = {quote(facts['topic'])}")
    sql_rules = (f"SELECT rule_id, item_type, condition, decision, rationale FROM {qualify(schema, tables['rules'])} "
                 f"WHERE item_type IN ({quote(facts['kind'])}, 'any')")
    sql_project = f"SELECT key, value FROM {qualify(schema, tables['project'])}"
    members = data.run_sql(sql_member, ["member_id", "name", "department", "role", "ai_tool", "level"])
    level = members[0]["level"] if members else "unknown"
    sql_trust = (f"SELECT level, own_domain_weight, other_domain_weight FROM {qualify(schema, tables['trust'])} "
                 f"WHERE level = {quote(level)}")
    trust = data.run_sql(sql_trust, ["level", "own_domain_weight", "other_domain_weight"])
    topics = data.run_sql(sql_topic, ["topic", "owner_department", "singleton", "budget_limit_eur", "description"])
    rules = data.run_sql(sql_rules, ["rule_id", "item_type", "condition", "decision", "rationale"])
    project = {r["key"]: r["value"] for r in data.run_sql(sql_project, ["key", "value"])}
    facts = enrich(facts, members[0] if members else None, topics[0] if topics else None, trust[0] if trust else None)
    summary = (f"author={facts['author']} dept={facts['department']} level={facts['level']} "
               f"topic={facts['topic']} owner={facts['topic_owner']} limit={facts['budget_limit_eur']} "
               f"authority={facts['author_has_authority']} trust={facts['trust_weight']}")
    return {"facts": facts, "profile": project, "rules": rules,
            "queries": [sql_member, sql_trust, sql_topic, sql_rules, sql_project], "summary": summary}


def memory_query(facts: dict) -> str:
    return f"{facts.get('topic')} {facts.get('content')}"


def recall(facts: dict, memory) -> list[dict]:
    """Structured + semantic recall from H-MEM:
    - every record on this topic (active and superseded: the history matters),
    - the CEO policies that mention this topic,
    - the 3 most similar memories (duplicate detection)."""
    seen: dict[str, dict] = {}
    for m in memory.list(f"topic:{facts['topic']}"):
        if "policy" in m.get("tags", []):
            seen[m["id"]] = {**m, "why": "ceo_policy"}
        elif not m.get("superseded_by"):
            seen[m["id"]] = {**m, "why": "active_on_topic"}
    for m in memory.query(memory_query(facts), top_n=3, threshold=0.25):
        if m["id"] not in seen and not m.get("superseded_by"):
            seen[m["id"]] = {**m, "why": "similar"}
    return list(seen.values())


def trust_of(mem: dict) -> float:
    try:
        return float(_tags(mem).get("trust", mem.get("confidence", 0.9)))
    except (TypeError, ValueError):
        return 0.9


def _active_decisions(facts: dict, memories: list[dict]) -> list[dict]:
    return [m for m in memories if _tags(m).get("topic") == facts["topic"] and _tags(m).get("kind") == "decision"
            and not m.get("superseded_by") and "policy" not in m.get("tags", [])]


def evaluate_with_memory(facts: dict, rules: list[dict], profile: dict, memories: list[dict]) -> list[dict]:
    """Return the Steward rules that hold, most important first. Pure Python, auditable."""
    kind = facts["kind"]
    active = _active_decisions(facts, memories)
    duplicate = next((m for m in memories if not m.get("superseded_by") and "policy" not in m.get("tags", [])
                      and similarity(facts["content"], m["content"]) >= 0.7
                      and _numbers(facts["content"]) <= _numbers(m["content"])), None)  # a new figure is not a duplicate
    changes_singleton = facts["singleton_topic"] and bool(active) and duplicate is None
    limit = facts.get("budget_limit_eur")
    over_limit = limit is not None and facts.get("amount_eur") is not None and facts["amount_eur"] > limit
    fact_numbers = _numbers(facts["content"])
    decision_numbers = set().union(*(_numbers(m["content"]) for m in active)) if active else set()
    contradicts = bool(facts["singleton_topic"] and active and fact_numbers and not fact_numbers <= decision_numbers)
    outweighs = bool(active) and facts.get("trust_weight", 0) >= max(trust_of(m) for m in active)
    can_change = facts["author_has_authority"] and outweighs

    checks = {
        "S01": facts["injection"],
        "S02": bool(facts["secrets"]),
        "S03": kind == "preference" or (facts["personal"] and kind != "decision"),
        "S04": duplicate is not None,
        "S05": kind == "decision" and over_limit,
        "S06": kind == "decision" and changes_singleton and not can_change,
        "S07": kind == "decision" and changes_singleton and can_change,
        "S08": kind == "decision" and not changes_singleton and facts["author_owns_topic"],
        "S09": kind == "decision" and not changes_singleton and not facts["author_owns_topic"],
        "S10": kind == "fact" and contradicts,
        "S11": kind == "fact" and not contradicts,
        "S12": kind == "task",
    }
    order = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S10", "S09", "S08", "S11", "S12"]
    by_id = {r["rule_id"]: dict(r) for r in rules}
    matched = [by_id[rid] for rid in order if checks.get(rid) and rid in by_id]
    for r in matched:  # tell the Decider which memory a rule is about
        if r["rule_id"] == "S04" and duplicate:
            r["about_memory"] = duplicate["id"]
        if r["rule_id"] in {"S06", "S07", "S10"} and active:
            r["about_memory"] = active[-1]["id"]
    # Hard rules first: nothing else matters when they hold.
    if matched and matched[0]["rule_id"] in {"S01", "S02", "S03", "S04"}:
        return matched[:1]
    return matched[:2]


def code_decides(facts: dict, matched_rules: list[dict]) -> dict | None:
    """The two cases no model may arbitrate: an instruction aimed at the team's AIs (S01, quarantine) and a secret
    (S02, redact). Deciding them in code keeps the content away from the model lanes and from the provider."""
    if facts.get("injection"):
        return {"decision": "quarantine", "confidence": 0.99, "citations": ["S01"],
                "justification": "The text tries to instruct the team's AIs: isolated by the guard, never stored."}
    if facts.get("secrets"):
        return {"decision": "redact", "confidence": 0.95, "citations": ["S02"],
                "justification": f"The text carries a secret ({', '.join(facts['secrets'])}): masked by the guard, the fact is kept."}
    return None


def memory_override(facts: dict, memories: list[dict]) -> dict | None:
    """A CEO policy in memory that covers this author's department, topic and amount."""
    for mem in memories:
        tags = _tags(mem)
        if "policy" not in tags or tags.get("topic") != facts.get("topic") or "override" not in tags:
            continue
        if tags.get("department") and tags["department"] != facts.get("department"):
            continue
        if "max_amount" in tags and (facts.get("amount_eur") is None or facts["amount_eur"] > float(tags["max_amount"])):
            continue
        return {"decision": tags["override"], "memory_id": mem["id"], "content": mem["content"]}
    return None


def hard_checks(facts: dict, proposal: dict, matched_rules: list[dict], memories: list[dict], flags: list[str]) -> list[str]:
    """Checks the Critic cannot be argued out of."""
    problems = []
    decision = proposal.get("decision")
    cites = set(proposal.get("citations", []))
    active = _active_decisions(facts, memories)
    if facts["injection"] and decision != "quarantine":
        problems.append("the proposal tries to instruct the team's AIs: it must be quarantined, never stored")
    if facts["secrets"] and decision in {"store", "supersede"}:
        problems.append(f"storing it would leak {facts['secrets']} to every AI of the team: redact instead")
    if decision == "supersede" and not (cites & {m["id"] for m in active}):
        problems.append("supersede must cite the active decision it replaces")
    if decision == "supersede" and active and facts.get("trust_weight", 0) < max(trust_of(m) for m in active):
        problems.append(f"{facts.get('author')} weighs {facts.get('trust_weight')} on '{facts['topic']}', less than the "
                        f"author of {active[-1]['id']}: clarify instead of overwriting")
    if decision == "store" and facts["singleton_topic"] and active and facts["kind"] == "decision":
        problems.append(f"storing a second decision on '{facts['topic']}' leaves a silent contradiction with "
                        f"{active[-1]['id']}: supersede (if authorised) or clarify")
    if decision in {"store", "supersede"} and facts["kind"] == "decision" and not facts.get("author_owns_topic"):
        if not any(c.startswith(("mem", "lm-")) and "policy" in next(
                (m.get("tags", []) for m in memories if m["id"] == c), []) for c in cites):
            problems.append(f"{facts.get('author')} ({facts.get('department')}) does not own '{facts['topic']}' "
                            f"and no CEO policy is cited")
    return problems


def prepared_action(decision: str, facts: dict) -> str:
    who = f"{facts.get('author')} ({facts.get('department') or 'unknown team'}, via {facts.get('ai_tool')})"
    if decision == "store":
        return f"Add to the shared project memory under '{facts['topic']}', with provenance {who}."
    if decision == "supersede":
        return f"Replace the active '{facts['topic']}' decision; keep the old one as history. Notify every AI on next recall."
    if decision == "redact":
        return f"Store a masked version (removed: {', '.join(facts['secrets']) or 'sensitive data'}) and tell {who}."
    if decision == "clarify":
        return (f"Ask {who}: 'This contradicts the current {facts['topic']} decision. Is it an error, or a real change?' "
                f"A real change goes to the topic owner.")
    if decision == "escalate":
        return f"Add to the CEO's queue: '{facts['content'][:120]}' proposed by {who}, with the conflicting memory."
    if decision == "quarantine":
        return f"Do not store. Log as a memory-poisoning attempt from {who}'s AI session."
    return f"Do not store. Tell {who} why (personal preference or duplicate)."


# ---------- writing the outcome ----------

def _journal_path(memory) -> Path:
    space = getattr(memory, "space", "default")
    return HERE.parents[1] / "data" / f"steward-journal-{space}.jsonl"


def journal(memory) -> list[dict]:
    path = _journal_path(memory)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _journal_write(memory, rows: list[dict]) -> None:
    path = _journal_path(memory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _tags_for(facts: dict) -> list[str]:
    tags = [f"topic:{facts['topic']}", f"kind:{facts['kind']}", f"trust:{facts.get('trust_weight', 0.25):g}"]
    for key, value in (("author", facts.get("author")), ("department", facts.get("department")),
                       ("ai", facts.get("ai_tool"))):
        if value:
            tags.append(f"{key}:{value}")
    return tags


def apply(decision: str, item: dict, facts: dict, memories: list[dict], memory, output: dict) -> dict:
    """Commit the Steward's decision. Rejected and quarantined proposals never reach the project memory."""
    source = f"{facts.get('author') or 'unknown'} via {facts.get('ai_tool') or 'unknown AI'}"
    record, replaced = None, None
    if decision in {"store", "redact", "supersede"}:
        content = mask_secrets(facts["content"]) if decision == "redact" else facts["content"]
        if decision == "supersede":
            active = _active_decisions(facts, memories)
            replaced = next((c for c in output.get("citations", []) if c in {m["id"] for m in active}),
                            active[-1]["id"] if active else None)
        # H-MEM multiplies every ranking score by confidence: an intern's fact ranks below the CEO's.
        record = memory.add(content, _tags_for(facts), source=source,
                            confidence=max(0.1, min(1.0, facts.get("trust_weight", 0.25))),
                            event="agent_proposal", supersedes=replaced)
    entry = {"journal_id": f"j-{int(time.time() * 1000)}", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "decision": decision, "author": facts.get("author"), "department": facts.get("department"),
             "ai_tool": facts.get("ai_tool"), "topic": facts["topic"], "kind": facts["kind"],
             "content": mask_secrets(facts["content"]), "memory_id": record["id"] if record else None,
             "supersedes": replaced, "reason": output.get("summary"), "citations": output.get("citations", []),
             "question": prepared_action("clarify", facts) if decision == "clarify" else None,
             "about_memory": next((r.get("about_memory") for r in output.get("evidence", {}).get("rules", [])
                                   if r.get("about_memory")), None),
             "confidence": output.get("confidence"), "amount_eur": facts.get("amount_eur"),
             "status": {"escalate": "pending", "clarify": "awaiting_author"}.get(decision, "done"),
             "item": {**item, "content": mask_secrets(
                 str(item.get("content", "")))}}
    rows = journal(memory) + [entry]
    _journal_write(memory, rows)
    about = next((m for m in memory.list(None) if m["id"] == entry.get("about_memory")), None) \
        if entry.get("about_memory") else None
    return {"memory_id": entry["memory_id"], "supersedes": replaced, "journal_id": entry["journal_id"],
            "status": entry["status"], "about_memory": entry.get("about_memory"),
            "current_record": about["content"] if about else None}


ANSWER_WORDS = {"error": "error", "mistake": "error", "typo": "error", "withdraw": "error", "no": "error",
                "an error": "error", "it was an error": "error", "wrong": "error",
                "change": "change", "real change": "change", "a real change": "change", "its a real change": "change",
                "yes": "change", "changed": "change", "real": "change", "confirm": "change", "confirmed": "change"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def resolve(journal_id: str, decision: str, memory, policy: str | None = None, by: str | None = None) -> dict:
    """The CEO answers an escalation: store / supersede / reject, and optionally turns the answer into a policy.
    `by` names the person who answered; the callers (MCP tool, console) check that this person is the CEO."""
    rows = journal(memory)
    entry = next((r for r in rows if r["journal_id"] == journal_id), None)
    if entry is None:
        raise KeyError(f"unknown escalation {journal_id}")
    if entry["status"] != "pending":
        raise ValueError(f"{journal_id} is already {entry['status']}")
    facts = intake(entry["item"])
    facts.update({"department": entry.get("department"), "author": entry.get("author"),
                  "trust_weight": 1.0})  # approved by the CEO: it now carries the CEO's weight
    record, replaced = None, None
    if decision in {"store", "supersede"}:
        if decision == "supersede":
            active = [m for m in memory.list(f"topic:{facts['topic']}")
                      if "kind:decision" in m.get("tags", []) and not m.get("superseded_by")]
            replaced = active[-1]["id"] if active else None
        record = memory.add(entry["content"], _tags_for(facts) + ["approved:ceo"],
                            source=f"{entry['author']} via {entry['ai_tool']}, approved by the CEO",
                            confidence=0.95, event="ceo_decision", supersedes=replaced)
    policy_record = None
    if policy:
        content, tags = learn(entry["item"], decision, policy, department=entry.get("department"))
        policy_record = memory.add(content, tags, source="CEO", confidence=0.95, event="user_correction")
    who = by or "the CEO"
    ruled = {"store": f"Approved once by {who}", "supersede": f"Made the record by {who}, replacing {replaced or 'nothing'}",
             "reject": f"Rejected by {who}"}[decision] + (f"; policy {policy_record['id']} raised." if policy_record else ".")
    entry.update({"status": f"resolved:{decision}", "memory_id": record["id"] if record else None,
                  "supersedes": replaced, "policy_id": policy_record["id"] if policy_record else None,
                  "resolved_by": by, "resolved_at": _now(), "ruling": decision,
                  "reason": f"{ruled} Before the ruling: {entry.get('reason') or ''}".strip()})
    _journal_write(memory, rows)
    return entry


def answer_clarification(journal_id: str, answer: str, memory, note: str = "", *, by: str,
                         ceo: bool = False) -> dict:
    """The author answers 'error or real change?'. An error withdraws the proposal; a real change goes to the CEO.
    Only the author of the proposal may answer (the CEO may answer from the console); `by` is kept in the journal."""
    rows = journal(memory)
    entry = next((r for r in rows if r["journal_id"] == journal_id), None)
    if entry is None:
        raise KeyError(f"unknown clarification {journal_id}")
    if entry["status"] != "awaiting_author":
        raise ValueError(f"{journal_id} is {entry['status']}, not awaiting the author")
    answer = ANSWER_WORDS.get(re.sub(r"[^a-z ]", "", (answer or "").strip().lower()), answer)
    if answer not in {"error", "change"}:
        raise ValueError("answer must be 'error' (withdraw the proposal) or 'change' (a real change, sent to the CEO)")
    if not ceo and (by or "").strip().lower() != (entry.get("author") or "").strip().lower():
        raise PermissionError(f"{journal_id} waits for its author, {entry.get('author')}; {by or 'this person'} "
                              "cannot answer for them.")
    if answer == "error":
        entry.update({"status": "resolved:withdrawn_by_author", "author_note": note, "answered_by": by,
                      "answered_at": _now()})
    else:
        entry.update({"status": "pending", "decision": "escalate", "author_note": note, "answered_by": by,
                      "answered_at": _now(),
                      "reason": f"Author confirms a real change. {entry.get('reason') or ''}".strip()})
    _journal_write(memory, rows)
    return entry


DEPARTMENT_WORDS = {"marketing": "marketing", "sales": "sales", "tech": "tech", "engineering": "tech",
                    "ops": "ops", "operations": "ops", "finance": "finance", "product": "product",
                    "support": "support", "customer success": "support", "executive": "executive"}


def policy_scope(note: str, fallback_topic: str, fallback_department: str | None) -> tuple[str, str | None]:
    """The scope of a policy is read from its wording when it names a department or a topic ("Marketing may
    commit up to 12,000 EUR per trade show" covers marketing / marketing_spend); otherwise it is the scope of the
    escalation it answers. The scope is written into the policy's text so every screen shows it."""
    low = " " + re.sub(r"[^a-z ]", " ", (note or "").lower()) + " "
    department = next((d for word, d in DEPARTMENT_WORDS.items() if f" {word} " in low), fallback_department)
    guessed = _guess_topic(note or "")
    topic = guessed if guessed != "general" else fallback_topic
    return topic, department


def learn(item: dict, decision: str, note: str, department: str | None = None) -> tuple[str, list[str]]:
    """A CEO policy becomes a durable memory that changes the next arbitrations."""
    facts = intake(item)
    if department is None:
        member = _member_lookup(str(item.get("author_id") or item.get("author") or ""))
        department = member["department"] if member else None
    topic, department = policy_scope(note, facts["topic"], department)
    tags = ["policy", f"topic:{topic}", f"override:{'store' if decision in {'store', 'supersede'} else decision}"]
    if department:
        tags.append(f"department:{department}")
    ceiling = _amounts(note)
    if ceiling:
        tags.append(f"max_amount:{max(ceiling):g}")
    scope = f"{department or 'any department'} · {topic}"
    return f"CEO policy ({scope}): {note.strip()}", tags
