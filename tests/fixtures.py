"""Small Atlas-like fixtures shared by the foundation tests."""
from datetime import date, datetime

from agent.decisions import Decision, Source
from agent.progress import Assumption, Report, Task

TODAY = date(2026, 10, 27)


def decision(id, attribute, value, status="approved", supersedes=None,
             author="lea", subject="atlas-launch", day=20):
    return Decision(id=id, subject=subject, attribute=attribute, value=value,
                    status=status, author=author,
                    source=Source(type="register", ref=f"reg-{id}"),
                    date=date(2026, 10, day), confidence=0.9,
                    supersedes=supersedes)


def task(id, member, due, subject="atlas-launch", depends_on=()):
    return Task(id=id, member=member, subject=subject, title=id,
                due=due, depends_on=list(depends_on))


def report(member, task_id, progress, assumptions=(), hour=9):
    return Report(member=member, task_id=task_id, progress=progress,
                  reported_at=datetime(2026, 10, 27, hour, 0),
                  assumptions=[Assumption(subject="atlas-launch", attribute=a, value=v)
                               for a, v in assumptions])
