"""Expected scenario results (data/expected/), for evaluation only.

The agents never import this module: it only checks the system's outputs.
"""
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_FILE = ROOT / "data" / "expected" / "scenarios.json"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InForce(Strict):
    key: str  # "subject/attribute"
    value: str
    decision: str


class DecisionConflict(Strict):
    key: str
    decisions: list[str]


class NotApplied(Strict):
    record: str
    reason: str


class ObsoleteWork(Strict):
    member: str
    task: str
    key: str
    decision: str


class MemberConflict(Strict):
    key: str
    members: list[str]
    evidence: list[str]
    arbiter: str


class StaleClaim(Strict):
    document: str
    key: str
    claimed: str
    expected: str
    contradicted_by: list[str]


class NotCorrected(Strict):
    document: str
    key: str
    reason: str


class Meeting(Strict):
    participants: list[str]
    evidence: list[str]
    precedent: Optional[str] = None


class Escalation(Strict):
    rule: Literal["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    level: Literal["P1", "P2", "P3"]
    subject: str
    recipient: str
    evidence: list[str]


class ClientView(Strict):
    launch_date: str
    sources: list[str]
    state_version_increases: bool


class Scenario(Strict):
    id: str
    title: str
    inputs: list[str]
    in_force: list[InForce] = []
    decision_conflicts: list[DecisionConflict] = []
    open_blockers: list[str] = []
    late_tasks: list[str] = []
    not_applied: list[NotApplied] = []
    obsolete_work: list[ObsoleteWork] = []
    member_conflicts: list[MemberConflict] = []
    stale_claims: list[StaleClaim] = []
    not_corrected_in_brief: list[NotCorrected] = []
    meetings: list[Meeting] = []
    escalations: list[Escalation] = []
    lessons_recalled: list[str] = []
    client_view: Optional[ClientView] = None
    notes: str = ""


def load_expected(path=None):
    payload = json.loads(Path(path or EXPECTED_FILE).read_text(encoding="utf-8"))
    return {s.id: s for s in (Scenario.model_validate(r) for r in payload["records"])}
