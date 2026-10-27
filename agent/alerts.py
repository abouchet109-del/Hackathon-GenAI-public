"""Alert inboxes (brick 1, notification algorithm).

An MCP server cannot reach a member's AI on its own, so alerts are pulled:
each member has an inbox, returned when their AI calls the server.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_DIR = ROOT / ".state"  # git-ignored


class Alert(BaseModel):
    id: str
    member: str
    created_at: datetime
    decision_id: str
    message: str
    delivered: bool = False


def affected_members(decision, tasks, reports):
    """Members whose work touches the decision's subject.

    A member is affected when one of their tasks is about the same subject,
    or when one of their reports relies on the same subject and attribute.
    """
    members = {t.member for t in tasks if t.subject == decision.subject}
    for report in reports:
        for assumption in report.assumptions:
            if (assumption.subject, assumption.attribute) == decision.key:
                members.add(report.member)
    members.discard(decision.author)  # the author already knows
    return sorted(members)


class AlertInbox:
    """Inboxes stored as one JSON file per project."""

    def __init__(self, project, state_dir=None):
        base = Path(state_dir or os.environ.get("ATLAS_STATE_DIR") or DEFAULT_STATE_DIR)
        self.path = base / f"alerts-{project}.json"

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        return [Alert.model_validate(item) for item in data]

    def _save(self, alerts):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [a.model_dump(mode="json") for a in alerts]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def notify(self, decision, tasks, reports):
        """Drop an alert for each affected member; return the new alerts."""
        alerts = self._load()
        already = {(a.member, a.decision_id) for a in alerts}
        message = (f"Decision {decision.id}: {decision.subject} {decision.attribute} "
                   f"is now {decision.value} (by {decision.author}, {decision.date.isoformat()})")
        new = [Alert(id=uuid.uuid4().hex, member=member,
                     created_at=datetime.now(timezone.utc),
                     decision_id=decision.id, message=message)
               for member in affected_members(decision, tasks, reports)
               if (member, decision.id) not in already]
        self._save(alerts + new)
        return new

    def pending(self, member):
        """Undelivered alerts for a member, marked as delivered."""
        alerts = self._load()
        out = [a for a in alerts if a.member == member and not a.delivered]
        for alert in out:
            alert.delivered = True
        if out:
            self._save(alerts)
        return out
