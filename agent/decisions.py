"""Decision records and the rules that say which decision is in force.

A decision is one structured record (docs/architecture.md, section 6), so the
controller and the algorithms compare fields, not free text.
"""
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

Status = Literal["proposal", "approved", "superseded"]
SourceType = Literal["meeting", "channel", "register", "report"]


class Source(BaseModel):
    type: SourceType
    ref: str  # id of the meeting, message or register entry


class Decision(BaseModel):
    id: str
    subject: str  # what the decision is about, e.g. "atlas-launch"
    attribute: str  # e.g. "launch_date", "scope", "owner", "deadline"
    value: str
    status: Status
    author: str
    source: Source
    date: date
    confidence: float = Field(ge=0.0, le=1.0)  # H-MEM requires a confidence
    supersedes: Optional[str] = None  # id of the decision this one replaces
    summary: str = ""  # the register's wording, for people; rules use the fields

    @property
    def key(self):
        return (self.subject, self.attribute)


class Conflict(BaseModel):
    key: tuple[str, str]
    decisions: list[Decision]


def _replaced_ids(decisions):
    return {d.supersedes for d in decisions if d.supersedes and d.status == "approved"}


def applicable(decisions):
    """Approved decisions that no approved decision replaces."""
    replaced = _replaced_ids(decisions)
    return [d for d in decisions
            if d.status == "approved" and d.id not in replaced]


def conflicts(decisions):
    """Applicable decisions that disagree on the same subject and attribute.

    Two applicable, incompatible decisions are a conflict to arbitrate:
    the latest one never wins on its own.
    """
    by_key = {}
    for decision in applicable(decisions):
        by_key.setdefault(decision.key, []).append(decision)
    return [Conflict(key=key, decisions=group)
            for key, group in by_key.items()
            if len({d.value for d in group}) > 1]


def in_force(decisions):
    """The decision in force for each (subject, attribute) without a conflict."""
    disputed = {c.key for c in conflicts(decisions)}
    return {d.key: d for d in applicable(decisions) if d.key not in disputed}
