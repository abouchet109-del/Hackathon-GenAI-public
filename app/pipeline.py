"""Orchestration: Intake -> Researcher -> MemoryKeeper -> Decider <-> Critic (bounded) -> Reporter."""
from __future__ import annotations

import uuid
from dataclasses import asdict

from .adapters.memory import make_memory
from .adapters.zetaris import make_data_source
from .agents import Blocks, Context, Domain, critique, decide, intake, match_rules, recall, research
from .config import ROOT, SETTINGS
from .llm import LLM
from .trace import Tracer

AGENTS = [
    {"name": "Intake", "role": "Structures the item and screens it for prompt injection"},
    {"name": "Researcher", "role": "Reads senders, rules and profile through Zetaris and evaluates the rules"},
    {"name": "MemoryKeeper", "role": "Recalls the owner's past corrections from Meterless H-MEM"},
    {"name": "Decider", "role": "Proposes a decision with citations (Nemotron via Nightshift, deep lane)"},
    {"name": "Critic", "role": "Hard checks plus a 9-point rubric; sends weak proposals back (judge lane)"},
    {"name": "Reporter", "role": "Returns the decision, the prepared action and the evidence"},
]


class Harness:
    """Holds the long-lived pieces so many runs can share them (server, evaluation)."""

    def __init__(self, settings=SETTINGS, memory_space: str | None = None, quiet: bool = False):
        self.s = settings
        self.domain = Domain.load(settings.domain_dir)
        self.data = make_data_source(settings)
        self.memory = make_memory(settings, memory_space)
        self.llm = LLM(settings)
        self.quiet = quiet

    def describe(self) -> dict:
        return {"data": self.data.name, "memory": self.memory.name,
                "llm": "nightshift" if self.llm.online else "offline (replay + deterministic fallback)",
                "sample_mode": self.s.sample_mode, "domain": self.domain.config["name"]}

    def run(self, item: dict, profile: str = "full", run_id: str | None = None, commit: bool = False) -> dict:
        run_id = run_id or f"{item.get('id', 'item')}-{uuid.uuid4().hex[:6]}"
        tr = Tracer(run_id, self.s.log_dir, quiet=self.quiet)
        blocks = Blocks.profile(profile, ROOT / "config" / "harness.yaml")
        tr.event("Orchestrator", "run_started", input_summary=f"profile={profile} blocks={asdict(blocks)}",
                 output_summary=str(self.describe()), target="Intake")
        ctx = Context(item=item)
        try:
            intake(ctx, self.domain, blocks, tr)
            research(ctx, self.domain, blocks, self.data, tr, self.s.data_schema)
            recall(ctx, self.domain, blocks, self.memory, tr)
            match_rules(ctx, self.domain, tr)

            proposal, verdict, fix = None, None, None
            max_rounds = 1 + (self.domain.config["max_revisions"] if blocks.critic else 0)
            for attempt in range(max_rounds):
                proposal = decide(ctx, self.domain, self.llm, tr, critique=fix, attempt=attempt)
                if not blocks.critic:
                    break
                verdict = critique(ctx, proposal, self.domain, self.llm, tr, attempt)
                if verdict["passed"]:
                    break
                fix = "; ".join(verdict["problems"]) or "Strengthen the justification with the evidence given."
            escalated = bool(blocks.critic and verdict and not verdict["passed"])
            if escalated:
                tr.event("Orchestrator", "escalated_to_owner",
                         output_summary=f"Critic still rejects after {max_rounds} proposals: {verdict['problems']}",
                         target="Reporter", status="escalated")
            final = "escalate" if escalated else proposal["decision"]
            action = (self.domain.logic.prepared_action("escalate", ctx.facts) if escalated
                      else proposal.get("action_draft") or self.domain.logic.prepared_action(final, ctx.facts))
            output = {
                "decision": final,
                "confidence": proposal.get("confidence"),
                "summary": proposal.get("justification"),
                "prepared_action": action,
                "needs_owner_approval": final in set(self.domain.config.get(
                    "needs_approval", ["pay", "reply", "submit_documents", "escalate"])),
                "citations": proposal.get("citations", []),
                "evidence": {"facts": ctx.facts, "rules": ctx.matched_rules,
                             "memories": [{"id": m["id"], "content": m["content"]} for m in ctx.memories],
                             "guard_flags": ctx.flags, "zetaris_queries": ctx.queries},
                "critic": verdict,
                "escalation_reason": verdict["problems"] if escalated else None,
            }
            tr.event("Reporter", "final_decision", output_summary=f"{final} | {action}",
                     model=proposal.get("model"), confidence=proposal.get("confidence"))
            if commit and hasattr(self.domain.logic, "apply"):
                output["applied"] = self.domain.logic.apply(final, ctx.item, ctx.facts, ctx.memories, self.memory, output)
                tr.event("Steward", "committed", output_summary=str(output["applied"])[:300],
                         target="Memory", status="success")
            status = "success"
        except Exception as error:  # noqa: BLE001 - a run must never crash silently
            tr.event("Orchestrator", "run_failed", output_summary=f"{type(error).__name__}: {error}", status="error")
            return {"run_id": run_id, "status": "error",
                    "error": {"type": type(error).__name__, "message": str(error), "recoverable": True},
                    "trace_id": f"trace-{run_id}", "log_file": str(tr.path.relative_to(ROOT)),
                    "execution_time_seconds": tr.elapsed}
        return {"run_id": run_id, "status": status, "profile": profile, "stack": self.describe(), "output": output,
                "agents": AGENTS, "trace_id": f"trace-{run_id}", "log_file": str(tr.path.relative_to(ROOT)),
                "execution_time_seconds": tr.elapsed}

    def learn(self, item: dict, correct_decision: str, note: str = "") -> dict:
        """Owner correction -> durable memory (H-MEM user_correction). The next similar item will cite it."""
        if hasattr(self.domain.logic, "learn"):
            content, tags = self.domain.logic.learn(item, correct_decision, note)
            record = self.memory.add(content, tags, source="user_correction", confidence=0.95)
            return {"memory": record, "tags": tags, "content": content, "engine": self.memory.name}
        facts = self.domain.logic.intake(item)
        tags = [f"override:{correct_decision}", f"sender:{facts['sender_domain']}"]
        if facts.get("amount_eur") is not None:
            ceiling = note and next((w for w in note.replace("EUR", " ").split() if w.replace('.', '', 1).isdigit()), None)
            tags.append(f"max_amount:{ceiling or facts['amount_eur']}")
        content = (f"Owner correction: for {facts['sender_domain']} ('{item.get('subject')}'), the right decision is "
                   f"'{correct_decision}'. {note}").strip()
        record = self.memory.add(content, tags, source="user_correction", confidence=0.95)
        return {"memory": record, "tags": tags, "content": content, "engine": self.memory.name}
