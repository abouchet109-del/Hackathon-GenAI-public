"""The project's sources: one record model per Zetaris table.

Each source is a JSON file shaped as Zetaris expects, an object holding an
array: {"synthetic": true, "description": "...", "records": [...]}.
The Atlas corpus in data/sample/ is synthetic and says so in every file.
"""
import json
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from agent.decisions import Decision
from agent.progress import Milestone, Report, Task

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "data" / "sample"


class Message(BaseModel):
    id: str
    project: str  # a message may come from another project (S4)
    channel: str
    author: str
    sent_at: datetime
    text: str
    reply_to: Optional[str] = None


class Document(BaseModel):
    id: str
    project: str
    title: str
    kind: Literal["brief", "spec", "test_plan", "note"]
    author: str
    status: Literal["draft", "published", "archived"]
    updated_at: datetime
    text: str


class Ticket(BaseModel):
    id: str
    project: str
    title: str
    description: str
    status: Literal["open", "closed"]
    severity: Literal["blocker", "major", "minor"]
    blocking: bool
    blocks: list[str] = []  # ids of the tasks the ticket blocks while open
    related_task: Optional[str] = None
    reporter: str
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RoleEntry(BaseModel):
    """The role table: authority is checked here, never in a message's text."""
    member: str
    name: str
    project: str
    role: Literal["manager", "product_owner", "developer", "sales", "qa"]
    can_approve: list[str] = []  # "subject/attribute", "subject/*" or "*"

    def may_approve(self, subject, attribute):
        return any(rule in ("*", f"{subject}/*", f"{subject}/{attribute}")
                   for rule in self.can_approve)


class Lesson(BaseModel):
    id: str
    text: str
    situation: list[str]  # tags describing when the lesson applies


class PastProject(BaseModel):
    id: str
    name: str
    ended: date
    summary: str
    outcome: str
    lessons: list[Lesson]


SOURCES = {
    "documents": Document,
    "messages": Message,
    "tickets": Ticket,
    "decisions": Decision,
    "tasks": Task,
    "milestones": Milestone,
    "reports": Report,
    "roles": RoleEntry,
    "past_projects": PastProject,
}


def parse_records(name, payload):
    """Validate the records of one source against its model."""
    model = SOURCES[name]
    return [model.model_validate(record) for record in payload["records"]]


def load_source(name, directory=None):
    path = Path(directory or SAMPLE_DIR) / f"{name}.json"
    return parse_records(name, json.loads(path.read_text(encoding="utf-8")))


def load_all(directory=None):
    return {name: load_source(name, directory) for name in SOURCES}


# --- the same sources, read through Zetaris -----------------------------------

ZETARIS_DATABASE = "atlas"


def source_sql(name):
    """One row per record, as JSON, so nested fields keep their shape."""
    return (f"SELECT to_json(r) AS record FROM {ZETARIS_DATABASE}.{name} "
            f"LATERAL VIEW explode(records) AS r")


def load_source_zetaris(name, client):
    """Records of one source, queried in SQL through Zetaris (or its cache)."""
    result = client.query(source_sql(name))
    payload = {"records": [json.loads(row[0]) for row in result.rows]}
    return parse_records(name, payload), result.origin
