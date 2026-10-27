"""Per-member progress classification (brick 2, deterministic algorithm).

Each progress report is compared with the assigned task and the decisions in
force. The four cases of docs/architecture.md:
  1. ok        - on track
  2. late      - past the deadline and not done
  3. obsolete  - the work relies on a value a decision in force has changed
  4. meeting   - one decision makes the work of two or more members obsolete,
                 or a late task blocks another member's task
"""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from agent.decisions import in_force

Case = Literal["ok", "late", "obsolete"]


class Task(BaseModel):
    id: str
    member: str
    subject: str
    title: str
    start: Optional[date] = None  # needed for the R1 forecast (brick 7)
    due: date
    depends_on: list[str] = []  # ids of tasks that must finish first


class Milestone(BaseModel):
    """A project milestone. Its date is the decision in force on
    (subject, attribute), never a copy, so a new decision moves it (S2)."""
    id: str
    subject: str  # e.g. "atlas-launch"
    attribute: str  # e.g. "launch_date"
    title: str
    depends_on: list[str] = []  # ids of the tasks the milestone needs


class Assumption(BaseModel):
    """A value the member's work relies on, e.g. launch_date = 3 November."""
    subject: str
    attribute: str
    value: str


class Report(BaseModel):
    member: str
    task_id: str
    progress: float = Field(ge=0.0, le=1.0)
    reported_at: datetime
    assumptions: list[Assumption] = []
    blockers: list[str] = []  # ticket ids, or short text when there is no ticket
    note: str = ""


class Finding(BaseModel):
    member: str
    task_id: str
    case: Case
    reason: str
    decision_id: Optional[str] = None  # the decision that made the work obsolete


class Meeting(BaseModel):
    participants: list[str]
    reason: str
    evidence: list[str]  # ids of the tasks and decisions behind the recommendation


class Classification(BaseModel):
    findings: list[Finding]
    meetings: list[Meeting]


def _latest_reports(reports):
    latest = {}
    for report in reports:
        current = latest.get(report.task_id)
        if current is None or report.reported_at > current.reported_at:
            latest[report.task_id] = report
    return latest


def _is_late(task, report, today):
    progress = report.progress if report else 0.0
    return task.due < today and progress < 1.0


def classify(tasks, reports, decisions, today):
    """Classify each task's latest report and recommend the useful meetings."""
    rules = in_force(decisions)
    latest = _latest_reports(reports)
    findings = []
    late_tasks = set()
    obsolete_by_decision = {}

    for task in tasks:
        report = latest.get(task.id)
        task_findings = []
        if _is_late(task, report, today):
            late_tasks.add(task.id)
            done = round((report.progress if report else 0.0) * 100)
            task_findings.append(Finding(
                member=task.member, task_id=task.id, case="late",
                reason=f"due {task.due.isoformat()}, {done}% done"))
        for assumption in report.assumptions if report else []:
            decision = rules.get((assumption.subject, assumption.attribute))
            if decision and decision.value != assumption.value:
                obsolete_by_decision.setdefault(decision.id, set()).add(task.member)
                task_findings.append(Finding(
                    member=task.member, task_id=task.id, case="obsolete",
                    decision_id=decision.id,
                    reason=(f"relies on {assumption.attribute} = {assumption.value}, "
                            f"decision {decision.id} says {decision.value}")))
        if not task_findings:
            task_findings.append(Finding(
                member=task.member, task_id=task.id, case="ok",
                reason=f"on track for {task.due.isoformat()}"))
        findings.extend(task_findings)

    meetings = []
    for decision_id, members in sorted(obsolete_by_decision.items()):
        if len(members) >= 2:
            meetings.append(Meeting(
                participants=sorted(members),
                reason=f"decision {decision_id} makes the work of several members obsolete",
                evidence=[decision_id]))
    by_id = {task.id: task for task in tasks}
    for task in tasks:
        for blocker_id in task.depends_on:
            blocker = by_id.get(blocker_id)
            if blocker and blocker_id in late_tasks and blocker.member != task.member:
                meetings.append(Meeting(
                    participants=sorted({blocker.member, task.member}),
                    reason=f"late task {blocker_id} blocks task {task.id}",
                    evidence=[blocker_id, task.id]))
    return Classification(findings=findings, meetings=meetings)
