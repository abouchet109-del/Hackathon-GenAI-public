"""The agents. Each one owns one decision and writes what it did to the trace.

Intake      structures the item (deterministic) and runs the input guard
Researcher  reads senders, rules and profile from Zetaris, evaluates the rules
MemoryKeeper retrieves the owner's past corrections from H-MEM
Decider     proposes a decision with citations (Nightshift, deep lane)
Critic      checks the proposal: hard checks in code, then a rubric (Nightshift, judge lane)
"""
from __future__ import annotations

import importlib.util
import os
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .adapters.zetaris import DataError, quote
from .guard import screen
from .llm import LLM, parse_json
from .trace import Tracer


@dataclass
class Domain:
    path: Path
    config: dict
    logic: object
    decider_prompt: str
    critic_prompt: str

    @classmethod
    def load(cls, path: Path) -> "Domain":
        config = yaml.safe_load((path / "domain.yaml").read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location(f"domain_{config['name']}", path / "logic.py")
        logic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(logic)
        rubric = "\n".join(f"- {k}: {v}" for item in config["rubric"] for k, v in item.items())
        decisions = ", ".join(config["decisions"])
        return cls(
            path=path,
            config=config,
            logic=logic,
            decider_prompt=(path / "prompts" / "decider.md").read_text(encoding="utf-8").format(decisions=decisions),
            critic_prompt=(path / "prompts" / "critic.md").read_text(encoding="utf-8").format(
                rubric=rubric, pass_score=config["pass_score"]),
        )


    def tables_for(self, data) -> dict:
        """Table names: plain in sample mode; with Zetaris, a pack may map them to fully qualified names
        (several sources behind one SQL door: datasource.table, lightning_db.view...)."""
        names = dict(self.config.get("tables", {}))
        if getattr(data, "name", "") == "zetaris":
            names.update(self.config.get("zetaris_tables", {}))
            if os.getenv("ZETARIS_USE_USL", "").lower() == "true":
                names.update(self.config.get("zetaris_usl_tables", {}))
        return names


def qualify(schema: str, name: str) -> str:
    return name if "." in name else f"{schema}.{name}"


@dataclass
class Blocks:
    """Harness blocks that can be switched off for the ablation study."""
    guard: bool = True
    rules: bool = True     # Zetaris rules, senders and profile
    memory: bool = True    # Meterless H-MEM
    critic: bool = True

    @classmethod
    def profile(cls, name: str, path: Path) -> "Blocks":
        profiles = yaml.safe_load(path.read_text(encoding="utf-8"))["profiles"]
        return cls(**profiles[name])


@dataclass
class Context:
    item: dict
    mask: object = None  # the pack's mask_secrets, applied to the evidence sent to the model lanes
    facts: dict = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    matched_rules: list[dict] = field(default_factory=list)
    rules: list[dict] = field(default_factory=list)
    profile: dict = field(default_factory=dict)
    memories: list[dict] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)


def intake(ctx: Context, domain: Domain, blocks: Blocks, tr: Tracer) -> None:
    ctx.facts = domain.logic.intake(ctx.item)
    ctx.mask = getattr(domain.logic, "mask_secrets", None)  # how this pack masks a secret before a model sees it
    if blocks.guard:
        ctx.flags = screen(f"{ctx.item.get('subject', '')}\n{ctx.item.get('body', '')}\n{ctx.item.get('content', '')}")
    if hasattr(domain.logic, "trace_summary"):
        head, body = domain.logic.trace_summary(ctx.item, ctx.facts)
    else:
        head = f"{ctx.item.get('from')} | {ctx.item.get('subject')}"
        body = f"amount={ctx.facts['amount_eur']} due={ctx.facts['due_date']} links={ctx.facts['link_domains']}"
    tr.event("Intake", "structured_item", input_summary=head, output_summary=f"{body} guard_flags={ctx.flags}",
             target="Researcher", status="flagged" if ctx.flags else "success")


def research(ctx: Context, domain: Domain, blocks: Blocks, data, tr: Tracer, schema: str) -> None:
    """Query Zetaris (or the SQLite sample) for the sender, the owner's profile and the rules."""
    if hasattr(domain.logic, "research"):  # the domain pack owns its queries
        if not blocks.rules:
            ctx.facts = domain.logic.enrich(ctx.facts, None)
            tr.event("Researcher", "skipped_rules_block", output_summary="rules block off (ablation)", target="MemoryKeeper",
                     status="skipped")
            return
        try:
            found = domain.logic.research(ctx.facts, data, schema, domain.tables_for(data))
        except DataError as error:
            ctx.facts = domain.logic.enrich(ctx.facts, None)
            tr.event("Researcher", "data_layer_error", output_summary=str(error), target="MemoryKeeper", status="error")
            return
        ctx.facts, ctx.profile, ctx.rules, ctx.queries = found["facts"], found["profile"], found["rules"], found["queries"]
        tr.event("Researcher", "queried_zetaris", input_summary=" ; ".join(q.split(' WHERE')[0] for q in ctx.queries),
                 output_summary=f"source={data.name} {found.get('summary', '')} rules_loaded={len(ctx.rules)}",
                 target="MemoryKeeper")
        return
    if not blocks.rules:
        ctx.facts = domain.logic.enrich_with_sender(ctx.facts, None)
        tr.event("Researcher", "skipped_rules_block", output_summary="rules block off (ablation)", target="Decider",
                 status="skipped")
        return
    t = domain.config["tables"]
    sql_sender = (f"SELECT sender_domain, organisation, category, verified FROM {schema}.{t['senders']} "
                  f"WHERE sender_domain = {quote(ctx.facts['sender_domain'])}")
    sql_profile = f"SELECT key, value FROM {schema}.{t['profile']}"
    try:
        sender_rows = data.run_sql(sql_sender, ["sender_domain", "organisation", "category", "verified"])
        ctx.profile = {r["key"]: r["value"] for r in data.run_sql(sql_profile, ["key", "value"])}
        ctx.facts = domain.logic.enrich_with_sender(ctx.facts, sender_rows[0] if sender_rows else None)
        sql_rules = (f"SELECT rule_id, item_type, condition, decision, rationale FROM {schema}.{t['rules']} "
                     f"WHERE item_type IN ({quote(ctx.facts['item_type'])}, 'any')")
        rules = data.run_sql(sql_rules, ["rule_id", "item_type", "condition", "decision", "rationale"])
        ctx.queries = [sql_sender, sql_profile, sql_rules]
    except DataError as error:
        ctx.facts = domain.logic.enrich_with_sender(ctx.facts, None)
        tr.event("Researcher", "data_layer_error", output_summary=str(error), target="Decider", status="error")
        return
    ctx.matched_rules = domain.logic.evaluate_rules(ctx.facts, rules, ctx.profile)
    tr.event("Researcher", "queried_zetaris", input_summary=" ; ".join(q.split(' WHERE')[0] for q in ctx.queries),
             output_summary=f"source={data.name} sender_verified={ctx.facts['sender_verified']} type={ctx.facts['item_type']} "
                            f"rules_considered={len(rules)} matched={[r['rule_id'] + '->' + r['decision'] for r in ctx.matched_rules]}",
             target="MemoryKeeper")


def recall(ctx: Context, domain: Domain, blocks: Blocks, memory, tr: Tracer) -> None:
    if not blocks.memory:
        tr.event("MemoryKeeper", "skipped_memory_block", output_summary="memory block off (ablation)", target="Decider",
                 status="skipped")
        return
    query = domain.logic.memory_query(ctx.facts)
    try:
        if hasattr(domain.logic, "recall"):
            ctx.memories = domain.logic.recall(ctx.facts, memory)
        else:
            ctx.memories = memory.query(query)
    except Exception as error:  # noqa: BLE001
        tr.event("MemoryKeeper", "memory_error", output_summary=str(error)[:200], target="Decider", status="error")
        return
    tr.event("MemoryKeeper", "recalled_memories", input_summary=query,
             output_summary=f"engine={memory.name} hits={[(m['id'], m.get('score', m.get('why'))) for m in ctx.memories]}",
             target="Decider")


def match_rules(ctx: Context, domain: Domain, tr: Tracer) -> None:
    """Domains whose rules depend on memory (e.g. 'conflicts with an active decision') evaluate them here."""
    if not hasattr(domain.logic, "evaluate_with_memory") or not ctx.rules:
        return
    ctx.matched_rules = domain.logic.evaluate_with_memory(ctx.facts, ctx.rules, ctx.profile, ctx.memories)
    tr.event("Researcher", "evaluated_rules",
             output_summary=f"matched={[r['rule_id'] + '->' + r['decision'] for r in ctx.matched_rules]}",
             target="Decider")


def _evidence(ctx: Context) -> str:
    """What the model lanes see. Secrets are masked here too (the pack's mask_secrets, when it has one): a model
    call goes through Nightshift to a provider, and a password or a key must never travel that far."""
    item = {k: ctx.item.get(k) for k in ("from", "subject", "body", "author", "ai_tool", "kind", "topic", "content")
            if ctx.item.get(k) is not None}
    facts = dict(ctx.facts)
    mask = getattr(ctx, "mask", None)
    if mask:
        for k in ("body", "content", "subject"):
            if isinstance(item.get(k), str):
                item[k] = mask(item[k])
        for k in ("content", "body"):
            if isinstance(facts.get(k), str):
                facts[k] = mask(facts[k])
    return json.dumps({
        "item": item,
        "facts": facts,
        "guard_flags": ctx.flags,
        "owner_profile": ctx.profile,
        "applicable_rules": ctx.matched_rules,
        "owner_memories": [{"id": m["id"], "content": m["content"], "tags": m.get("tags", []),
                            **({"superseded_by": m["superseded_by"]} if m.get("superseded_by") else {})}
                           for m in ctx.memories],
    }, ensure_ascii=False, indent=1)


def decide(ctx: Context, domain: Domain, llm: LLM, tr: Tracer, critique: str | None = None, attempt: int = 0) -> dict:
    """The Arbiter. Hard cases (an injection, a secret: the pack's `code_decides`) never reach a model: code decides
    and the trace says so; everything else goes to the deep lane with masked evidence."""
    forced = domain.logic.code_decides(ctx.facts, ctx.matched_rules) if hasattr(domain.logic, "code_decides") else None
    if forced:
        proposal = {**forced, "model": None, "via": "code", "receipt_id": None,
                    "action_draft": domain.logic.prepared_action(forced["decision"], ctx.facts)}
        tr.event("Decider", "proposed_decision", input_summary=f"hard case decided in code: {forced.get('citations')}",
                 output_summary=f"{proposal['decision']}: {proposal.get('justification', '')}", target="Critic",
                 model=None, confidence=proposal.get("confidence"), retry=attempt, via="code", cached=False,
                 receipt_id=None, citations=proposal.get("citations", []))
        return proposal
    user = _evidence(ctx)
    if critique:
        user += f"\n\nThe Critic rejected your previous proposal. Fix to apply: {critique}"
    result = llm.chat("deep", domain.decider_prompt, user)
    proposal = parse_json(result.text) if result else None
    if proposal and proposal.get("decision") in domain.config["decisions"]:
        proposal["model"] = result.model
        proposal["via"] = result.source
        proposal["receipt_id"] = getattr(result, "receipt_id", None)  # Nightshift's receipt, when it sent one
    else:
        proposal = fallback_decision(ctx, domain)
    tr.event("Decider", "proposed_decision", input_summary=f"rules={len(ctx.matched_rules)} memories={len(ctx.memories)}"
             + (f" critique='{critique}'" if critique else ""),
             output_summary=f"{proposal['decision']}: {proposal.get('justification', '')}", target="Critic",
             model=proposal.get("model"), confidence=proposal.get("confidence"), retry=attempt,
             via=proposal.get("via"), cached=proposal.get("via") == "replay",
             receipt_id=proposal.get("receipt_id"), citations=proposal.get("citations", []))
    return proposal


def fallback_decision(ctx: Context, domain: Domain) -> dict:
    """No model available: rules first, then owner corrections, else ask the owner."""
    override = domain.logic.memory_override(ctx.facts, ctx.memories) if ctx.memories else None
    rule = ctx.matched_rules[0] if ctx.matched_rules else None
    priority = set(domain.config.get("priority_decisions", ["block_scam"]))
    rule_cites = ([rule["rule_id"]] + ([rule["about_memory"]] if rule.get("about_memory") else [])) if rule else []
    if rule and rule["decision"] in priority:
        decision, cites, why, conf = rule["decision"], rule_cites, rule["rationale"], 0.9
    elif override:
        decision, cites, conf = override["decision"], [override["memory_id"]] + rule_cites, 0.8
        why = f"Past correction {override['memory_id']} applies: {override['content']}"
    elif rule:
        decision, cites, why, conf = rule["decision"], rule_cites, rule["rationale"], 0.75
    else:
        decision, cites, why, conf = "escalate", [], "No rule or past correction covers this item.", 0.4
    return {"decision": decision, "confidence": conf, "justification": why, "citations": cites,
            "action_draft": domain.logic.prepared_action(decision, ctx.facts), "model": None, "via": "deterministic-fallback"}


def critique(ctx: Context, proposal: dict, domain: Domain, llm: LLM, tr: Tracer, attempt: int) -> dict:
    """Hard checks in code first (they cannot be argued with), then the model's rubric."""
    problems, hard = [], False
    decision = proposal["decision"]
    known_ids = {r["rule_id"] for r in ctx.matched_rules} | {m["id"] for m in ctx.memories}
    invented = [c for c in proposal.get("citations", []) if c not in known_ids]
    if invented:
        problems.append(f"cites evidence that does not exist: {invented}")
        hard = True
    if ctx.flags and decision in domain.config["unsafe_when_flagged"]:
        problems.append(f"'{decision}' is not allowed when the guard raised {ctx.flags}; escalate instead")
        hard = True
    rule_decisions = {r["decision"] for r in ctx.matched_rules}
    cited_memory = any(c.startswith("mem") or c.startswith("lm-") for c in proposal.get("citations", []))
    if rule_decisions and decision not in rule_decisions and decision != "escalate" and not cited_memory:
        problems.append(f"contradicts the applicable rule(s) {sorted(rule_decisions)} without citing an owner correction")
        hard = True
    if decision == "pay" and ctx.facts.get("amount_eur") is None:
        problems.append("pay without a parsed amount")
        hard = True
    if hasattr(domain.logic, "hard_checks"):
        extra = domain.logic.hard_checks(ctx.facts, proposal, ctx.matched_rules, ctx.memories, ctx.flags)
        problems += extra
        hard = hard or bool(extra)

    scores, model, via, receipt_id = None, None, "rules-only", None
    result = llm.chat("judge", domain.critic_prompt, _evidence(ctx) + "\n\nPROPOSAL:\n" + json.dumps(proposal, ensure_ascii=False))
    judged = parse_json(result.text) if result else None
    if judged and isinstance(judged.get("scores"), dict):
        scores = {k: int(v) for k, v in judged["scores"].items() if isinstance(v, (int, float))}
        model, via, receipt_id = result.model, result.source, getattr(result, "receipt_id", None)
        if judged.get("fix"):
            problems.append(judged["fix"])
    total = sum(scores.values()) if scores else (9 - 3 * len(problems))
    if hard:
        total = min(total, 4)
    passed = total >= domain.config["pass_score"] and not hard
    verdict = {"passed": passed, "total": total, "scores": scores, "problems": problems, "model": model, "via": via}
    tr.event("Critic", "approved" if passed else "requested_revision",
             input_summary=f"proposal={decision} citations={proposal.get('citations')}",
             output_summary=f"score={total}/9 " + ("; ".join(problems) if problems else "no issue"),
             target="Reporter" if passed else "Decider", model=model, confidence=total / 9, retry=attempt,
             status="success" if passed else "needs_revision", via=via, cached=via == "replay", receipt_id=receipt_id)
    return verdict
