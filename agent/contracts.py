"""Contracts: the objects passed between components (PLAN, section 5.1).

Agents exchange structured records, never full source text (architecture,
section 4). Every record carries its evidence so each output can cite it.

Flow (architecture, sections 2 and 3):
  extractor ──CandidateInfo──> update agent ──UpdateProposal──> controller
  controller ──ControllerResult──> state writer, or escalation (brick 7)
  MCP report_progress ──Report (agent/progress.py)──> update agent
  extractor, deliverable type ──DeliverableClaim──> comparison ──StaleClaim──> drafter
  escalation rules (brick 7) ──Escalation──> escalation inbox ──> manager's AI

Authority is never decided here: the controller derives a decision's status
from the information type, the role table and the conflicts (D13, "the LLM
qualifies, the code decides").
"""
import hashlib
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent.decisions import Decision
from agent.progress import Assumption, Report

__all__ = [
    "Evidence", "InfoType", "CandidateInfo", "UpdateProposal", "Check",
    "ControllerResult", "Escalation", "Gap", "Report", "Assumption",
    "DeliverableClaim", "StaleClaim",
]

# Zetaris tables the agents read, plus the MCP progress reports.
SourceTable = Literal["documents", "messages", "tickets", "decisions", "tasks",
                      "milestones", "reports", "roles", "past_projects",
                      "mcp_report"]

# Information types of the use case (use-case-atlas.md, section 3).
InfoType = Literal[
    "proposal",           # "we could move to 12 November": not authoritative
    "decision",           # approved by someone: authority checked by the code
    "observation",        # "the CSV test failed": authoritative as a fact
    "historical",         # a replaced decision: kept for history
    "work_declaration",   # "I am writing the brief with SSO": state to watch
    "task_progress",      # "CSV export 70%, due yesterday": dated fact
    "lesson",             # from a past project: a recommendation only
]


class Contract(BaseModel):
    # Unknown fields are refused, so a malformed LLM output fails validation.
    model_config = ConfigDict(extra="forbid")


class Evidence(Contract):
    """Where a piece of information comes from."""
    table: SourceTable
    record_id: str          # stable id, e.g. "MSG-007", "TCK-QA-012"
    quote: str = ""         # the passage that supports the claim, verbatim


# --- brick 1: extractor -> update agent ------------------------------------

class CandidateInfo(Contract):
    """One piece of information found in a source by the extractor."""
    id: str                 # e.g. "CAND-MSG-007-1"
    project: str            # project the source says it is about (S4)
    subject: str            # e.g. "atlas-launch"
    attribute: str          # e.g. "launch_date", "scope", "qa_status"
    value: str              # e.g. "2026-11-10", "csv; sso:v2", "failing"
    info_type: InfoType
    author: str             # member id as written in the source
    stated_at: datetime     # when the source said it
    evidence: list[Evidence] = Field(min_length=1)
    blocks: list[str] = []  # task or milestone ids an observation blocks
    confidence: float = Field(ge=0.0, le=1.0)


# --- brick 1: update agent -> controller ------------------------------------

ProposalKind = Literal[
    "new_decision",   # a decision on a subject with none in force
    "supersede",      # a decision that replaces the one in force
    "observation",    # a dated fact (ticket, test result, blocker)
    "progress",       # task progress, structured fields of a report
    "work_declaration",
    "no_change",      # restates what the state already holds
]


class UpdateProposal(Contract):
    """A proposed change to the project state, with its evidence.

    The update agent links the information to a subject, an attribute and the
    decision it would replace; it never sets the decision's status.
    """
    id: str
    candidate_ids: list[str] = Field(min_length=1)
    kind: ProposalKind
    project: str
    subject: str
    attribute: str
    value: str
    info_type: InfoType
    author: str
    stated_at: datetime
    supersedes: Optional[str] = None  # decision id this would replace
    rationale: str                     # why this subject, attribute and kind
    evidence: list[Evidence] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    revision: int = Field(default=0, ge=0, le=1)  # one revision at most


# --- brick 1: controller -> state writer or escalation ------------------------

CheckName = Literal[
    "schema", "author_authorised", "same_project", "not_duplicate",
    "no_conflict", "evidence_supports",  # the last one is the LLM check
]


class Check(Contract):
    name: CheckName
    passed: bool
    detail: str = ""


class ControllerResult(Contract):
    """The controller's verdict on one proposal.

    accepted  - `decision` (for decisions) is the record the writer applies,
                with its status set by the code
    revision  - sent back to the update agent once, with what to fix
    escalated - to the authorised person; brick 7 turns it into an R2
    ignored   - other project (S4) or duplicate (S5): logged, not written
    """
    proposal_id: str
    verdict: Literal["accepted", "revision", "escalated", "ignored"]
    checks: list[Check]
    decision: Optional[Decision] = None
    revision_request: Optional[str] = None
    escalate_to: Optional[str] = None   # member id from the role table
    reason: str


# --- brick 4: deliverable claims ----------------------------------------------

class DeliverableClaim(Contract):
    """A claim found in a deliverable, in the same shape as a report assumption."""
    id: str                 # e.g. "CLM-DOC-005-2"
    document_id: str
    subject: str
    attribute: str
    value: str
    passage: str            # verbatim text of the claim in the deliverable
    confidence: float = Field(ge=0.0, le=1.0)

    def as_assumption(self):
        return Assumption(subject=self.subject, attribute=self.attribute, value=self.value)


class StaleClaim(Contract):
    """A claim contradicted by a decision in force or an open blocker (code)."""
    claim: DeliverableClaim
    expected_value: str
    contradicted_by: list[str] = Field(min_length=1)  # decision or ticket ids
    reason: str


# --- brick 7: escalations to the manager ----------------------------------------

Rule = Literal["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
Level = Literal["P1", "P2", "P3"]


class Gap(Contract):
    measured: float
    tolerance: float
    unit: Literal["days", "percent"] = "days"


class Escalation(Contract):
    """One escalation (architecture, brick 7, "Format d'une remontée")."""
    id: str                 # derived from (rule, subject), see escalation_id
    rule: Rule
    level: Level
    subject: str            # milestone, task, decision or deliverable id
    recipient: str          # authorised person on the subject (role table)
    finding: str            # factual sentence written by the code, not an LLM
    gap: Optional[Gap] = None
    expected_action: Literal["decide", "validate", "information"]
    evidence: list[str] = Field(min_length=1)  # decision, task, ticket, report ids
    status: Literal["open", "seen", "done"] = "open"
    created_at: datetime
    updated_at: datetime
    feedback: Optional[Literal["useful", "useless", "too_late"]] = None


def escalation_id(rule, subject):
    """Stable id for deduplication: one escalation per (rule, subject)."""
    digest = hashlib.sha1(f"{rule}|{subject}".encode("utf-8")).hexdigest()[:8]
    return f"ESC-{rule}-{digest}"
