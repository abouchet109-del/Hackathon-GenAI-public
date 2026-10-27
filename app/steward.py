"""Steward as a service: one shared project memory, many AIs.

Wraps the harness with the 'project_memory' domain pack. Every write goes through the
full pipeline (guard -> Zetaris org data -> H-MEM recall -> Decider <-> Critic) and is
committed only after the decision; reads come straight from H-MEM with provenance.
Used by the MCP server (app/mcp_server.py), the CLI (run.py steward-*) and the tests.
"""
from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import json
import os
from collections import defaultdict

from .adapters.memory import load_seed
from .coordination import bridge
from .config import SETTINGS
from .pipeline import Harness

DOMAIN = "project_memory"


def _tags(mem: dict) -> dict:
    return {t.split(":", 1)[0]: t.split(":", 1)[1] for t in mem.get("tags", []) if ":" in t}


def _public(mem: dict) -> dict:
    tags = _tags(mem)
    return {"id": mem["id"], "content": mem["content"], "topic": tags.get("topic"), "kind": tags.get("kind"),
            "author": tags.get("author"), "department": tags.get("department"), "ai": tags.get("ai"),
            "source": mem.get("source"), "supersedes": mem.get("supersedes"),
            "superseded_by": mem.get("superseded_by"), "is_policy": "policy" in mem.get("tags", [])}


@contextlib.contextmanager
def _exclusive(path):
    """One writer at a time per company memory, across processes (each AI client runs its own MCP server):
    otherwise two contradictory values could both pass the arbitration and both be stored."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as handle:
        if os.name == "nt":  # Windows: lock the first byte (blocking, retried by msvcrt every second)
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


class Steward:
    def __init__(self, space: str = "project", settings=SETTINGS):
        self.settings = dataclasses.replace(settings, domain=DOMAIN)
        self.h = Harness(self.settings, memory_space=space, quiet=True)
        self.memory = self.h.memory
        self.logic = self.h.domain.logic
        spec = importlib.util.spec_from_file_location("steward_context", self.h.domain.path / "context.py")
        self.ctx = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.ctx)
        self.ctx.logic = self.logic
        self.data, self.schema = self.h.data, self.settings.data_schema
        self.ctx.TABLES = self.h.domain.tables_for(self.data)
        self._state_dir = self.settings.log_dir.parent / "data"
        self._lock_path = self._state_dir / f"steward-{space}.lock"
        self.space = space
        self.progress_store = bridge.ProgressStore(space, self._state_dir)
        self.inbox = bridge.inbox(space, self._state_dir)

    # ----- setup -----
    def reset(self, seed: bool = True, policies: bool = True) -> int:
        self.memory.reset()
        journal = self.logic._journal_path(self.memory)
        if journal.exists():
            journal.write_text("", encoding="utf-8")  # emptied, not deleted
        self.ctx.reset_state(self.memory)
        self.progress_store.reset(self.h.domain.path / "progress_seed.jsonl" if seed else None)
        if self.inbox.path.exists():
            self.inbox.path.write_text("[]", encoding="utf-8")
        if not seed:
            return 0
        name = "memory_seed.jsonl" if policies else "memory_seed_no_policies.jsonl"
        rows = load_seed(self.h.domain.path / name)
        for m in rows:
            self.memory.add(m["content"], m["tags"], m["source"], m.get("confidence", 0.9), event="seed")
        return len(rows)

    def describe(self) -> dict:
        return self.h.describe()

    # ----- write path: every proposal is arbitrated -----
    def remember(self, content: str, author: str, ai_tool: str, kind: str = "fact", topic: str | None = None,
                 run_id: str | None = None) -> dict:
        if not topic:  # the watchlist in Zetaris decides the topic, not the client
            found = self.ctx.topics_in(content, self.watchlist())
            topic = found[0] if found else ""
        item = {"content": content, "author": author, "ai_tool": ai_tool, "kind": kind, "topic": topic or ""}
        waiting = next((e for e in self.logic.journal(self.memory)
                        if e["status"] in {"pending", "awaiting_author"} and e.get("topic") == (topic or "")
                        and e.get("content", "").strip().lower() == content.strip().lower()), None)
        if waiting:  # the same proposal is already waiting: answer with it instead of queuing it twice
            return {"decision": waiting["decision"], "why": "Already waiting for a person: " + (waiting.get("reason") or ""),
                    "citations": waiting.get("citations", []),
                    "applied": {"journal_id": waiting["journal_id"], "memory_id": None, "status": waiting["status"]},
                    "needs_ceo": waiting["status"] == "pending", "critic_score": None, "trace": None,
                    "stack": self.describe()}
        with _exclusive(self._lock_path):
            res = self.h.run(item, run_id=run_id, commit=True)
        if res["status"] != "success":
            return {"status": "error", "error": res.get("error"), "trace": res.get("log_file")}
        out = res["output"]
        alerts = self._alert_on((out.get("applied") or {}).get("memory_id"))
        return {"decision": out["decision"], "why": out["summary"], "citations": out["citations"],
                "applied": out.get("applied"), "needs_ceo": out["decision"] == "escalate", "alerts_sent": alerts,
                "critic_score": (out.get("critic") or {}).get("total"), "trace": res["log_file"],
                "stack": res["stack"]}

    # ----- read path -----
    def records(self, topic: str | None = None) -> list[dict]:
        return [_public(m) for m in self.memory.list(f"topic:{topic}" if topic else None)]

    def recall(self, query: str, topic: str | None = None, top_n: int = 5) -> list[dict]:
        """Active memories only (superseded ones are history, see why())."""
        hits = [] if not query else self.memory.query(query, top_n=top_n * 2, threshold=0.15)
        active = [m for m in hits if not m.get("superseded_by")]
        if topic:
            listed = [m for m in self.memory.list(f"topic:{topic}") if not m.get("superseded_by")]
            listed_ids = {m["id"] for m in listed}
            active = listed + [m for m in active if m["id"] not in listed_ids]
        out = []
        for m in active[:top_n]:
            row = _public(m)
            if "score" in m:
                row["score"] = m["score"]
            out.append(row)
        return out

    def brief(self) -> dict:
        """The current shared truth: active decisions and facts per topic, plus the CEO policies."""
        by_topic: dict[str, list] = defaultdict(list)
        policies = []
        for m in self.memory.list(None):
            if m.get("superseded_by"):
                continue
            row = _public(m)
            (policies if row["is_policy"] else by_topic[row["topic"] or "general"]).append(
                {k: row[k] for k in ("id", "content", "kind", "author", "ai")})
        pending = [e for e in self.logic.journal(self.memory) if e["status"] == "pending"]
        return {"topics": dict(sorted(by_topic.items())), "ceo_policies": [{"id": p["id"], "content": p["content"]}
                                                                         for p in policies],
                "pending_escalations": len(pending)}

    def why(self, topic: str) -> dict:
        """The full history of a topic: every version with who proposed it from which AI, and the Steward's journal."""
        history = self.records(topic)
        journal = [{k: e.get(k) for k in ("journal_id", "at", "decision", "author", "ai_tool", "content", "reason",
                                          "memory_id", "supersedes", "status")}
                   for e in self.logic.journal(self.memory) if e["topic"] == topic]
        current = [h for h in history if not h["superseded_by"] and not h["is_policy"]]
        return {"topic": topic, "current": current, "history": history, "steward_journal": journal}

    def escalations(self) -> list[dict]:
        return [{k: e.get(k) for k in ("journal_id", "at", "author", "department", "ai_tool", "topic", "kind",
                                       "content", "reason", "citations")}
                for e in self.logic.journal(self.memory) if e["status"] == "pending"]

    def resolve(self, journal_id: str, decision: str, policy: str | None = None) -> dict:
        if decision not in {"store", "supersede", "reject"}:
            raise ValueError("decision must be store, supersede or reject")
        with _exclusive(self._lock_path):
            entry = self.logic.resolve(journal_id, decision, self.memory, policy)
        out = {k: entry.get(k) for k in ("journal_id", "status", "memory_id", "supersedes", "policy_id", "content")}
        out["alerts_sent"] = self._alert_on(entry.get("memory_id"))
        return out


    # ----- v2: the watch layer, role context, clarifications, CEO agent, onboarding -----
    def watchlist(self) -> list[dict]:
        return self.ctx.watchlist(self.data, self.schema)

    def observe(self, text: str, author: str, ai_tool: str, source: str = "conversation", title: str = "") -> dict:
        """An excerpt (or a document, or meeting notes) from someone's AI. Only extracted items are arbitrated and
        possibly stored; the raw text is never kept."""
        items = self.ctx.extract(text, self.watchlist(), self.h.llm)
        outcomes = []
        for i, it in enumerate(items[:12]):
            res = self.remember(it["content"], author, ai_tool, it.get("kind", "fact"), it.get("topic") or None)
            outcomes.append({"extracted": it["content"], "kind": it.get("kind"), "topic": it.get("topic"),
                             "decision": res.get("decision"), "why": res.get("why"),
                             "journal_id": (res.get("applied") or {}).get("journal_id"),
                             "extracted_by": it.get("extracted_by"), "trace": res.get("trace")})
        return {"source": source, "title": title, "items_found": len(items), "outcomes": outcomes,
                "stored": sum(o["decision"] in {"store", "supersede", "redact"} for o in outcomes),
                "raw_text_stored": False}

    def my_context(self, name: str, task: str = "", budget_tokens: int = 1500) -> dict:
        return self.ctx.compose_context(name, task, self.data, self.schema, self.memory,
                                        self.logic.journal(self.memory), budget_tokens)

    def whats_new(self, name: str, advance: bool = True) -> dict:
        return self.ctx.whats_new(name, self.data, self.schema, self.memory, self.logic.journal(self.memory), advance)

    def clarifications(self, name: str | None = None) -> list[dict]:
        return [{k: e.get(k) for k in ("journal_id", "at", "author", "ai_tool", "topic", "content", "question",
                                       "about_memory")}
                for e in self.logic.journal(self.memory)
                if e["status"] == "awaiting_author" and (name is None or e.get("author") == name)]

    def answer_clarification(self, journal_id: str, answer: str, note: str = "") -> dict:
        with _exclusive(self._lock_path):
            entry = self.logic.answer_clarification(journal_id, answer, self.memory, note)
        return {k: entry.get(k) for k in ("journal_id", "status", "topic", "content", "reason")}

    def my_contributions(self, name: str) -> list[dict]:
        return [{k: e.get(k) for k in ("journal_id", "at", "ai_tool", "topic", "kind", "content", "decision",
                                       "status", "memory_id")}
                for e in self.logic.journal(self.memory) if e.get("author") == name]

    def signals(self) -> list[dict]:
        signals = self.ctx.weak_signals(self.data, self.schema, self.memory, self.logic.journal(self.memory))
        prog = self.progress()
        for m in prog["meetings"]:
            signals.append({"kind": "coordination", "topic": "team progress", "severity": "high",
                            "signal": m["reason"].capitalize() + ".", "concerned": m["participants"],
                            "suggested_meeting": {"participants": m["participants"], "minutes": 15,
                                                  "agenda": "Agree on what changes for each task: " + ", ".join(m["evidence"]) + "."}})
        for f in prog["findings"]:
            if f["case"] in {"late", "obsolete"}:
                signals.append({"kind": f["case"], "topic": f"{f['task_id']} {f.get('title') or ''}".strip(),
                                "severity": "medium", "signal": f"{f['member']}: {f['reason']}.",
                                "concerned": [f["member"]], "suggested_meeting": None})
        return signals

    # ----- team coordination (ported from the team's Atlas modules, app/coordination) -----
    def _today(self):
        return bridge.as_of(self.ctx._rows(self.data, self.schema, "project", ["key", "value"]))

    def _tasks(self):
        rows = self.ctx._rows(self.data, self.schema, "tasks", ["task_id", "member", "topic", "title", "due", "depends_on"])
        return bridge.tasks_from_rows(rows)

    def _decisions(self):
        singles = {r["topic"] for r in self.ctx._rows(self.data, self.schema, "topics", ["topic", "singleton"])
                   if str(r["singleton"]).lower() in {"yes", "true", "1"}}
        return bridge.decisions_from_memory(self.memory, singles, self._today())

    def tasks(self, name: str | None = None) -> list[dict]:
        return [t.model_dump(mode="json") for t in self._tasks() if name is None or t.member == name]

    def progress(self, name: str | None = None) -> dict:
        out = bridge.classification(self._tasks(), self.progress_store.reports(), self._decisions(), self._today())
        if name:
            out["findings"] = [f for f in out["findings"] if f["member"] == name]
            out["meetings"] = [m for m in out["meetings"] if name in m["participants"]]
        return out

    def report_progress(self, name: str, task_id: str, progress: float, assumptions: dict | None = None,
                        note: str = "") -> dict:
        """A person's AI reports where a task stands, and the values the work relies on (e.g. launch_date)."""
        task = next((t for t in self._tasks() if t.id == task_id), None)
        if task is None:
            raise ValueError(f"unknown task {task_id}")
        if task.member != name:
            raise ValueError(f"{task_id} belongs to {task.member}, not {name}")
        from datetime import datetime
        self.progress_store.add({"member": name, "task_id": task_id, "progress": max(0.0, min(1.0, float(progress))),
                                 "reported_at": datetime.now().replace(microsecond=0).isoformat(),
                                 "assumptions": {k: str(v) for k, v in (assumptions or {}).items()}, "note": note})
        return self.progress(name)

    def alerts(self, name: str) -> list[dict]:
        """Alerts waiting for this person, returned once."""
        return [a.model_dump(mode="json") for a in self.inbox.pending(name)]

    def _alert_on(self, memory_id: str | None) -> list[str]:
        """After a decision is stored or replaces another, alert everyone whose work it touches."""
        if not memory_id:
            return []
        decision = next((d for d in self._decisions() if d.id == memory_id), None)
        if decision is None:
            return []
        # Task.subject holds the task's topic; the register files every decision under the project, so the tasks
        # on the decision's topic are re-filed under the project for the inbox's "who is affected" rule.
        touched = [t.model_copy(update={"subject": bridge.SUBJECT}) for t in self._tasks()
                   if t.subject == decision.attribute]
        new = self.inbox.notify(decision, touched, self.progress_store.reports())
        return sorted({a.member for a in new})

    def onboarding_questions(self) -> list[dict]:
        topics = [t["topic"] for t in self.watchlist()]
        return [{**q, "options": topics if q.get("options") == "topics" else q.get("options")}
                for q in self.ctx.ONBOARDING]

    def onboard(self, answers: dict) -> dict:
        return self.ctx.onboard(answers, self.data, self.schema, self.memory)

    def profile(self, name: str) -> dict:
        return self.ctx.member_profile(name, self.data, self.schema, self.memory)


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)
