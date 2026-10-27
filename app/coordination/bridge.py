"""Glue between Steward's company memory and the team's coordination modules.

- The decisions in force come from H-MEM (records tagged kind:decision on single-answer topics), mapped to
  the decision register of app.coordination.decisions, so "what is in force" has one source.
- Tasks come from Zetaris (table tasks), progress reports from each person's AI (MCP tool report_progress).
- app.coordination.progress classifies every task (ok, late, obsolete) and recommends meetings;
  app.coordination.alerts drops an alert for each person whose work a new decision touches.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path

from atlas.alerts import AlertInbox
from atlas.decisions import Decision, Source
from atlas.progress import Assumption, Report, Task, classify

SUBJECT = "brikk"
DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
AMOUNT = re.compile(r"(\d[\d ,.]*)\s*(?:EUR|€)", re.I)


def value_of(text: str) -> str:
    """The comparable value of a decision or an assumption: its first ISO date, else its first amount, else
    the text itself, lower-cased. '29 EUR per user per month' and '29 EUR' compare equal."""
    text = str(text or "")
    m = DATE.search(text)
    if m:
        return m.group(1)
    m = AMOUNT.search(text)
    if m:
        return f"{float(m.group(1).replace(' ', '').replace(',', '')):g} EUR"
    return text.strip().lower()


def _tags(mem: dict) -> dict:
    return {t.split(":", 1)[0]: t.split(":", 1)[1] for t in mem.get("tags", []) if ":" in t}


def decisions_from_memory(memory, singleton_topics: set[str], today: date) -> list[Decision]:
    out = []
    for m in memory.list(None):
        tags = _tags(m)
        if "kind:decision" not in m.get("tags", []) or tags.get("topic") not in singleton_topics:
            continue
        out.append(Decision(
            id=m["id"], subject=SUBJECT, attribute=tags["topic"], value=value_of(m["content"]),
            status="superseded" if m.get("superseded_by") else "approved",
            author=tags.get("author") or m.get("source") or "unknown",
            source=Source(type="register", ref=m["id"]), date=today,
            confidence=max(0.0, min(1.0, float(m.get("confidence") or 0.9))),
            supersedes=m.get("supersedes")))
    return out


def tasks_from_rows(rows: list[dict]) -> list[Task]:
    return [Task(id=r["task_id"], member=r["member"], subject=r["topic"], title=r["title"],
                 due=date.fromisoformat(r["due"]),
                 depends_on=[d.strip() for d in (r.get("depends_on") or "").split(";") if d.strip()])
            for r in rows]


class ProgressStore:
    """Progress reports, one JSON file per space (git-ignored), seeded from the domain pack."""

    def __init__(self, space: str, state_dir: Path):
        self.path = Path(state_dir) / f"progress-{space}.json"

    def load(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save(self, rows: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    def reset(self, seed_file: Path | None) -> int:
        rows = []
        if seed_file and seed_file.exists():
            rows = [json.loads(l) for l in seed_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.save(rows)
        return len(rows)

    def add(self, row: dict) -> None:
        rows = self.load()
        rows.append(row)
        self.save(rows)

    def reports(self) -> list[Report]:
        out = []
        for r in self.load():
            out.append(Report(member=r["member"], task_id=r["task_id"], progress=float(r["progress"]),
                              reported_at=datetime.fromisoformat(r["reported_at"]), note=r.get("note", ""),
                              assumptions=[Assumption(subject=SUBJECT, attribute=k, value=value_of(v))
                                           for k, v in (r.get("assumptions") or {}).items()]))
        return out


def inbox(space: str, state_dir: Path) -> AlertInbox:
    return AlertInbox(space, state_dir=state_dir)


def as_of(project_rows: list[dict]) -> date:
    """The date the synthetic project lives at (project.as_of), so the demo stays the same whenever it runs;
    STEWARD_TODAY overrides it, and real deployments drop the key to use today."""
    if os.getenv("STEWARD_TODAY"):
        return date.fromisoformat(os.environ["STEWARD_TODAY"])
    row = next((r for r in project_rows if r.get("key") == "as_of"), None)
    return date.fromisoformat(row["value"]) if row and row.get("value") else date.today()


def classification(tasks: list[Task], reports: list[Report], decisions: list[Decision], today: date) -> dict:
    c = classify(tasks, reports, decisions, today)
    titles = {t.id: t.title for t in tasks}
    return {"as_of": today.isoformat(),
            "findings": [{**f.model_dump(), "title": titles.get(f.task_id)} for f in c.findings],
            "meetings": [m.model_dump() for m in c.meetings]}
