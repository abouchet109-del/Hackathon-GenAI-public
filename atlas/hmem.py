"""H-MEM client: the memories of the project and of the organisation.

H-MEM (Meterless engine) keeps what happened and why (architecture, section 6):
decisions with their provenance and confidence, the trust ledger that records
every change ("why does the system say 10 November?"), helpful / wrong
feedback that moves the confidence, and the lessons of past projects (S9).

Two backends behind the same interface:
- the H-MEM service (services/hmem/, the Meterless reference implementation
  served over local HTTP), the real engine;
- a local Python fallback that mirrors its contracts (provenance mandatory,
  append-only ledger, the exact feedback deltas), used with SAMPLE_MODE=true
  or when the service cannot be reached. Once the client falls back, it stays
  on the fallback for its lifetime, so what it wrote is still what it reads;
  `origin` says which backend answered.

Decisions are written as they were validated by the controller: H-MEM's
automatic conflict resolution is never called on them (architecture,
section 6: conflicts on decisions are arbitrated by a person, rule 3).

Command line:
    python -m atlas.hmem health
    python -m atlas.hmem explain <subject> <attribute>
"""
import json
import os
import re
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Literal, Optional

import requests
from pydantic import BaseModel

from atlas.decisions import Decision
from atlas.zetaris import sample_mode

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "http://127.0.0.1:8765"
DEFAULT_TIMEOUT = 5  # seconds: a local service either answers fast or is down
# Recall threshold on the reference's final score (relevance x confidence).
# Its default, 0.35, is tuned for chat memories; with its hash embedder, a
# French lesson matched by its situation tags scores about 0.2 (Orion, S9).
RECALL_THRESHOLD = 0.15

Layer = Literal["short_term", "working", "long_term"]
FeedbackKind = Literal["helpful", "not_helpful", "wrong"]
# Same deltas as the reference (H-MEM AGENTS.md, section 9.2).
FEEDBACK_DELTAS = {"helpful": 0.05, "not_helpful": -0.03, "wrong": -0.2}
# Decision sources mapped to H-MEM provenance origins.
ORIGIN_OF_SOURCE = {"meeting": "document", "channel": "chat_message",
                    "register": "document", "report": "chat_message"}


class HMemError(Exception):
    """The H-MEM service refused a request, or could not be reached.

    unavailable is True for a timeout, a network error or a 5xx: only those
    switch the client to the local fallback, so a bad request is never hidden.
    """

    def __init__(self, message, unavailable=False):
        super().__init__(message)
        self.unavailable = unavailable


# --- records as the agents see them -------------------------------------------

def _to_ms(at):
    if isinstance(at, datetime):
        moment = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    else:
        moment = datetime.combine(at, time(), tzinfo=timezone.utc)
    return int(moment.timestamp() * 1000)


def _from_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


class Provenance(BaseModel):
    origin: str        # H-MEM origin, e.g. "document", "chat_message"
    label: str         # e.g. "register REG-2026-021"
    refs: list[str] = []
    learned_at: datetime


class Memory(BaseModel):
    id: str            # H-MEM memory id, e.g. "mem-4"
    external_id: str   # the project's id, e.g. "DEC-004", "LES-ORION-1"
    content: str
    layer: Layer
    tags: list[str]
    confidence: float
    source: str
    provenance: Provenance
    recorded_at: datetime
    supersedes: Optional[str] = None      # memory id
    superseded_by: Optional[str] = None   # memory id

    def tag(self, prefix):
        """Value of the first "prefix:value" tag, or None."""
        for tag in self.tags:
            if tag.startswith(prefix + ":"):
                return tag[len(prefix) + 1:]
        return None

    @classmethod
    def from_engine(cls, raw):
        tags = raw.get("tags", [])
        provenance = raw["provenance"]
        external = next((t[4:] for t in tags if t.startswith("ext:")), raw["id"])
        return cls(id=raw["id"], external_id=external, content=raw["content"],
                   layer=raw["layer"], tags=tags, confidence=raw["confidence"],
                   source=raw["source"],
                   provenance=Provenance(origin=provenance["origin"],
                                         label=provenance["label"],
                                         refs=provenance.get("refs") or [],
                                         learned_at=_from_ms(provenance["learnedAt"])),
                   recorded_at=_from_ms(raw["timestamp"]),
                   supersedes=raw.get("supersedes"),
                   superseded_by=raw.get("supersededBy"))


class TrustEntry(BaseModel):
    """One line of the trust ledger: who changed what, when, and how."""
    memory_id: str
    action: str        # one of the 17 ledger actions: create, update, feedback...
    actor: str
    at: datetime
    confidence_before: Optional[float] = None
    confidence_after: Optional[float] = None
    details: dict = {}

    @classmethod
    def from_engine(cls, raw):
        before = raw.get("previousState") or {}
        after = raw.get("newState") or {}
        return cls(memory_id=raw["memoryId"], action=raw["action"], actor=raw["actor"],
                   at=_from_ms(raw["timestamp"]),
                   confidence_before=before.get("confidence"),
                   confidence_after=after.get("confidence"),
                   details=raw.get("details") or {})


class Recalled(BaseModel):
    memory: Memory
    relevance: float


class Explanation(BaseModel):
    """Answer to "why this value?": the value in force, its history, its ledger."""
    subject: str
    attribute: str
    current: Optional[Memory]        # approved and not superseded
    history: list[Memory]            # oldest first
    trust_log: list[TrustEntry]      # every ledger entry of those memories, in ledger order

    def text(self):
        if self.current is None:
            return f"No decision in memory for {self.subject}/{self.attribute}."
        current = self.current
        lines = [f"{self.subject}/{self.attribute} = {current.tag('value')}: "
                 f"decision {current.external_id} by {current.tag('author')}, "
                 f"source {current.provenance.label}, confidence {current.confidence:.2f}."]
        by_id = {m.id: m for m in self.history}
        replaced = by_id.get(current.supersedes) if current.supersedes else None
        while replaced is not None:
            lines.append(f"It replaces {replaced.external_id} ({replaced.tag('value')}, "
                         f"source {replaced.provenance.label}).")
            replaced = by_id.get(replaced.supersedes) if replaced.supersedes else None
        external = {m.id: m.external_id for m in self.history}
        for entry in self.trust_log:
            change = ""
            if entry.confidence_before is not None and entry.confidence_after is not None \
                    and entry.confidence_before != entry.confidence_after:
                change = f" confidence {entry.confidence_before:.2f} -> {entry.confidence_after:.2f}"
            lines.append(f"  {entry.at.date()} {entry.action} {external[entry.memory_id]} "
                         f"by {entry.actor}{change}")
        return "\n".join(lines)


# --- backends -------------------------------------------------------------------
# Both take and return the engine's own JSON shapes (camelCase), so the facade
# below is the only place that knows the project's records.

class HttpBackend:
    """The H-MEM service (services/hmem/)."""
    name = "hmem-service"

    def __init__(self, base_url, timeout, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _request(self, method, path, body=None, params=None):
        try:
            response = self.session.request(method, self.base_url + path, json=body,
                                            params=params, timeout=self.timeout)
        except requests.RequestException as error:
            raise HMemError(f"cannot reach the H-MEM service at {self.base_url}: "
                            f"{type(error).__name__}", unavailable=True) from error
        if response.status_code != 200:
            raise HMemError(f"H-MEM service: HTTP {response.status_code}: "
                            f"{' '.join(response.text.split())[:300]}",
                            unavailable=response.status_code >= 500)
        return response.json()

    def health(self):
        return self._request("GET", "/health")

    def add(self, payload):
        reply = self._request("POST", "/memories", payload)
        return reply["memory"], reply["created"]

    def find(self, tags):
        return self._request("GET", "/memories", params={"tag": tags})["memories"]

    def ledger(self, memory_ids):
        return self._request("GET", "/ledger", params={"memoryId": memory_ids})["entries"]

    def feedback(self, memory_id, kind, at_ms, actor):
        body = {"kind": kind, "at": at_ms, "actor": actor}
        return self._request("POST", f"/memories/{memory_id}/feedback", body)["memory"]

    def query(self, text, top_n, layer, at_ms):
        body = {"query": text, "topN": top_n, "layer": layer, "at": at_ms,
                "threshold": RECALL_THRESHOLD}
        return [(item["memory"], item["relevance"])
                for item in self._request("POST", "/query", body)["memories"]]


def _tokens(text):
    return {t for t in re.split(r"[^\w]+", text.lower()) if len(t) > 2}


class LocalBackend:
    """In-process fallback with the same contracts as the reference.

    Recall is a keyword overlap times the confidence: simpler than the
    reference's hybrid ranking, enough to find a lesson by its situation.
    """
    name = "local"

    def __init__(self):
        self.records = {}
        self.entries = []
        self.seq = 0

    def health(self):
        return {"ok": True, "engine": "local-fallback", "memories": len(self.records)}

    def _log(self, memory_id, action, actor, at_ms, before=None, after=None, details=None):
        self.entries.append({"memoryId": memory_id, "action": action, "actor": actor,
                             "timestamp": at_ms, "previousState": before,
                             "newState": after, "details": details or {}})

    def _by_ext(self, external_id):
        tag = "ext:" + external_id
        return next((r for r in self.records.values() if tag in r["tags"]), None)

    def add(self, payload):
        if not payload.get("source", "").strip():
            raise HMemError("a memory record with no source is rejected (H-MEM, section 2)")
        existing = self._by_ext(payload["externalId"])
        if existing is not None:
            return dict(existing), False
        self.seq += 1
        at = payload["at"]
        record = {"id": f"mem-{self.seq}", "content": payload["content"],
                  "layer": payload["layer"],
                  "tags": ["ext:" + payload["externalId"], *payload["tags"]],
                  "confidence": min(1.0, max(0.0, payload["confidence"])),
                  "source": payload["source"],
                  "provenance": {**payload["provenance"], "learnedAt": at},
                  "timestamp": at, "supersedes": None, "supersededBy": None}
        old = self._by_ext(payload["supersedesExternalId"]) \
            if payload.get("supersedesExternalId") else None
        if old is not None:
            record["supersedes"] = old["id"]
        self.records[record["id"]] = record
        self._log(record["id"], "create", payload["actor"], at, after=dict(record))
        if old is not None:
            before = dict(old)
            old["supersededBy"] = record["id"]
            self._log(old["id"], "update", payload["actor"], at, before=before,
                      after=dict(old), details={"reason": "superseded", "by": record["id"]})
        return dict(record), True

    def find(self, tags):
        return [dict(r) for r in self.records.values() if all(t in r["tags"] for t in tags)]

    def ledger(self, memory_ids):
        return [e for e in self.entries if e["memoryId"] in memory_ids]

    def feedback(self, memory_id, kind, at_ms, actor):
        record = self.records.get(memory_id)
        if record is None:
            raise HMemError(f"unknown memory id {memory_id}")
        before = dict(record)
        record["confidence"] = min(1.0, max(0.0, record["confidence"] + FEEDBACK_DELTAS[kind]))
        if kind == "wrong" and "review" not in record["tags"]:
            record["tags"] = [*record["tags"], "review"]
        self._log(memory_id, "feedback", actor, at_ms, before=before, after=dict(record),
                  details={"kind": kind, "delta": FEEDBACK_DELTAS[kind]})
        return dict(record)

    def query(self, text, top_n, layer, at_ms):
        wanted = _tokens(text)
        scored = []
        for record in self.records.values():
            if layer and record["layer"] != layer:
                continue
            words = _tokens(record["content"] + " " + " ".join(record["tags"]))
            overlap = len(wanted & words) / len(wanted) if wanted else 0.0
            if overlap > 0:
                scored.append((dict(record), round(overlap * record["confidence"], 4)))
        scored.sort(key=lambda item: (-item[1], item[0]["id"]))
        return scored[:top_n]


# --- the facade the agents use ----------------------------------------------------

class HMem:
    """Project and organisation memory, on the H-MEM service or its fallback."""

    def __init__(self, base_url=None, timeout=DEFAULT_TIMEOUT, sample=None,
                 backend=None, actor="atlas"):
        self.actor = actor
        if backend is not None:
            self.backend = backend
        elif (sample_mode() if sample is None else sample):
            self.backend = LocalBackend()
        else:
            self.backend = HttpBackend(base_url or os.environ.get("ATLAS_HMEM_URL", DEFAULT_URL),
                                       timeout)
        self.fallback_reason = None

    @property
    def origin(self):
        """"hmem-service", "local" (SAMPLE_MODE) or "local-fallback"."""
        return "local-fallback" if self.fallback_reason else self.backend.name

    def _call(self, method, *args):
        try:
            return getattr(self.backend, method)(*args)
        except HMemError as error:
            if not (error.unavailable and isinstance(self.backend, HttpBackend)):
                raise
            # From here on, every read and write goes to the fallback, so the
            # run stays consistent; the reason is kept for the trace.
            self.fallback_reason = str(error)
            self.backend = LocalBackend()
            return getattr(self.backend, method)(*args)

    def health(self):
        return {**self._call("health"), "origin": self.origin}

    def remember(self, external_id, content, layer, tags, source, provenance_origin,
                 provenance_label, refs, confidence, at, supersedes=None):
        """Write one memory, idempotently on external_id; return (Memory, created)."""
        payload = {"externalId": external_id, "content": content, "layer": layer,
                   "tags": list(tags), "source": source, "confidence": confidence,
                   "provenance": {"origin": provenance_origin, "label": provenance_label,
                                  "refs": list(refs)},
                   "supersedesExternalId": supersedes, "at": _to_ms(at),
                   "actor": self.actor}
        raw, created = self._call("add", payload)
        return Memory.from_engine(raw), created

    def record_decision(self, decision: Decision, project: str, evidence_refs=()):
        """Write a decision validated by the controller, with its provenance.

        Idempotent on the decision id. A decision that supersedes another one
        marks the old memory as superseded (kept, never deleted).
        """
        label = f"{decision.source.type} {decision.source.ref}"
        # Plain structured wording: the reference reads words such as
        # "instead" as a correction and would link memories on its own.
        content = (f"Decision {decision.id} on {decision.subject} {decision.attribute}: "
                   f"{decision.value} (status {decision.status}, by {decision.author}). "
                   f"{decision.summary}").strip()
        tags = [f"project:{project}", "kind:decision", f"subject:{decision.subject}",
                f"attribute:{decision.attribute}", f"value:{decision.value}",
                f"status:{decision.status}", f"author:{decision.author}"]
        return self.remember(decision.id, content, "working", tags, label,
                             ORIGIN_OF_SOURCE[decision.source.type], label,
                             [decision.source.ref, *evidence_refs], decision.confidence,
                             decision.date, supersedes=decision.supersedes)

    def record_lesson(self, lesson_id, text, project, situation, source, learned_on,
                      confidence=0.9):
        """Write a lesson of a past project in the organisation's memory (long term)."""
        tags = [f"project:{project}", "kind:lesson", *situation]
        return self.remember(lesson_id, text, "long_term", tags, source, "document",
                             source, [source], confidence, learned_on)

    def explain(self, subject, attribute):
        """Why does the system hold this value? History and trust ledger."""
        memories = [Memory.from_engine(raw) for raw in self._call(
            "find", ["kind:decision", f"subject:{subject}", f"attribute:{attribute}"])]
        memories.sort(key=lambda m: (m.recorded_at, m.id))
        in_force = [m for m in memories
                    if m.superseded_by is None and m.tag("status") == "approved"]
        # Entries come in ledger order, which is the order of the changes.
        log = [TrustEntry.from_engine(raw)
               for raw in self._call("ledger", [m.id for m in memories])] if memories else []
        # Two approved values in force are a conflict for a person to arbitrate:
        # memory never picks one, so there is no current value then.
        current = in_force[0] if len(in_force) == 1 else None
        return Explanation(subject=subject, attribute=attribute, current=current,
                           history=memories, trust_log=log)

    def feedback(self, memory_id, kind: FeedbackKind, at):
        """Record a helpful / not_helpful / wrong feedback; return the memory."""
        return Memory.from_engine(self._call("feedback", memory_id, kind, _to_ms(at),
                                             self.actor))

    def recall(self, query, top_n=3, layer: Optional[Layer] = "long_term", at=None):
        """Precedents and lessons that match a situation, best first.

        A recalled lesson is a recommendation, never a fact about this project.
        """
        at_ms = _to_ms(at) if at is not None else None
        return [Recalled(memory=Memory.from_engine(raw), relevance=relevance)
                for raw, relevance in self._call("query", query, top_n, layer, at_ms)]


def load_org_lessons(memory: HMem, past_projects):
    """Write every lesson of the past projects in the organisation's memory.

    Idempotent: a lesson already in memory is not written again. Returns the
    number of lessons written.
    """
    written = 0
    for project in past_projects:
        for lesson in project.lessons:
            _, created = memory.record_lesson(
                lesson.id, lesson.text, project.name.lower(), lesson.situation,
                f"past_projects {project.id}", project.ended)
            written += created
    return written


def main(argv):
    memory = HMem()
    if argv[1:2] == ["health"]:
        print(json.dumps(memory.health(), indent=1))
        return 0
    if len(argv) == 4 and argv[1] == "explain":
        print(memory.explain(argv[2], argv[3]).text())
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
