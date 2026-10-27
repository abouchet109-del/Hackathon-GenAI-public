"""The project state (task 6): one JSON document, versioned, one writer.

The state is what the agents read and what brick 1 writes: roles, tasks,
milestones, tickets, progress reports, decisions and the other accepted
information. Every write that changes something creates a new version; a
source record already ingested changes nothing (S5).

StateStore is the interface. JsonStateStore keeps the state in a JSON file;
World Model (task 7) can sit behind the same two methods, load() and commit().
Only agent/writer.py calls commit(): it is the single writer.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from agent import decisions as rules
from agent.contracts import Evidence, InfoType
from agent.decisions import Decision
from agent.progress import Milestone, Report, Task
from agent.sources import RoleEntry, Ticket

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_DIR = ROOT / ".state"  # git-ignored

# Structured sources copied into the state by id; a changed record replaces
# the stored one, an identical one changes nothing.
RECORD_TABLES = {"roles": RoleEntry, "tasks": Task, "milestones": Milestone,
                 "tickets": Ticket, "reports": Report}


def record_key(table, record):
    return record.member if table == "roles" else record.id


class Fact(BaseModel):
    """Accepted information that is not a decision: observation, proposal,
    work declaration, task progress. Kept with its evidence."""
    model_config = ConfigDict(extra="forbid")
    id: str
    subject: str
    attribute: str
    value: str
    info_type: InfoType
    author: str
    stated_at: datetime
    evidence: list[Evidence] = Field(min_length=1)
    blocks: list[str] = []


class Change(BaseModel):
    """What one write brings. `refs` are the source records it ingests,
    e.g. "messages/MSG-007": a ref already ingested is never processed again."""
    refs: list[str] = []
    records: dict[str, list] = {}   # table -> records, upserted by id
    decisions: list[Decision] = []
    facts: list[Fact] = []
    summary: str = ""


class VersionEntry(BaseModel):
    version: int
    at: datetime
    refs: list[str]
    summary: str


class ProjectState(BaseModel):
    project: str
    version: int = 0
    roles: list[RoleEntry] = []
    tasks: list[Task] = []
    milestones: list[Milestone] = []
    tickets: list[Ticket] = []
    reports: list[Report] = []
    decisions: list[Decision] = []
    facts: list[Fact] = []
    ingested: list[str] = []
    history: list[VersionEntry] = []

    # --- reads used by the agents and the rules ---------------------------

    def is_ingested(self, ref):
        return ref in self.ingested

    def decision(self, decision_id):
        return next((d for d in self.decisions if d.id == decision_id), None)

    def in_force(self):
        return rules.in_force(self.decisions)

    def conflicts(self):
        return rules.conflicts(self.decisions)

    def role(self, member):
        return next((r for r in self.roles if r.member == member), None)

    def authorised(self, subject, attribute):
        """Members of this project allowed to approve (subject, attribute)."""
        return [r for r in self.roles
                if r.project == self.project and r.may_approve(subject, attribute)]

    def known_keys(self):
        """The (subject, attribute) pairs the state already talks about."""
        keys = {d.key for d in self.decisions}
        keys |= {(f.subject, f.attribute) for f in self.facts}
        keys |= {(m.subject, m.attribute) for m in self.milestones}
        for report in self.reports:
            keys |= {(a.subject, a.attribute) for a in report.assumptions}
        for role in self.roles:
            for rule in role.can_approve:
                subject, _, attribute = rule.partition("/")
                if attribute and attribute != "*":
                    keys.add((subject, attribute))
        return sorted(keys)

    def subjects(self):
        return sorted({k[0] for k in self.known_keys()} | {t.subject for t in self.tasks})

    def open_blockers(self):
        return [t for t in self.tickets
                if t.project == self.project and t.status == "open" and t.blocking]


def apply_change(state, change):
    """The state after `change`, or None when the change brings nothing new.

    Pure: the caller decides when to save. Refs already ingested, decisions
    and facts already present, and identical records are all no-ops (S5).
    """
    new = state.model_copy(deep=True)
    changed = False
    for table, records in sorted(change.records.items()):
        model = RECORD_TABLES[table]
        stored = {record_key(table, r): r for r in getattr(new, table)}
        for record in records:
            record = model.model_validate(record)
            key = record_key(table, record)
            if stored.get(key) != record:
                stored[key] = record
                changed = True
        setattr(new, table, [stored[k] for k in sorted(stored)])
    known_decisions = {d.id for d in new.decisions}
    for decision in change.decisions:
        if decision.id not in known_decisions:
            new.decisions.append(decision)
            known_decisions.add(decision.id)
            changed = True
    known_facts = {f.id for f in new.facts}
    for fact in change.facts:
        if fact.id not in known_facts:
            new.facts.append(fact)
            known_facts.add(fact.id)
            changed = True
    fresh_refs = [ref for ref in change.refs if ref not in new.ingested]
    if fresh_refs:
        new.ingested.extend(fresh_refs)
        changed = True
    if not changed:
        return None
    new.version = state.version + 1
    new.history.append(VersionEntry(version=new.version, at=datetime.now(timezone.utc),
                                    refs=fresh_refs, summary=change.summary))
    return new


class StateStore:
    """Interface of the project state. Implementations: JsonStateStore here,
    World Model later. Only agent/writer.py calls commit()."""

    def load(self) -> ProjectState:
        raise NotImplementedError

    def commit(self, change: Change) -> Optional[int]:
        """Apply `change`; return the new version, or None if nothing changed."""
        raise NotImplementedError


class JsonStateStore(StateStore):
    """The state as one JSON file per project, in .state/ (or ATLAS_STATE_DIR)."""

    def __init__(self, project, state_dir=None):
        self.project = project
        base = Path(state_dir or os.environ.get("ATLAS_STATE_DIR") or DEFAULT_STATE_DIR)
        self.path = base / f"state-{project}.json"

    def load(self):
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ProjectState(project=self.project)
        return ProjectState.model_validate_json(text)

    def commit(self, change):
        new = apply_change(self.load(), change)
        if new is None:
            return None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write then rename, so a reader never sees a half-written state.
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(new.model_dump_json(indent=1), encoding="utf-8")
        tmp.replace(self.path)
        return new.version
