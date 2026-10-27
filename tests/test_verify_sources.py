"""The read-back check of the Brikk sources (ARCHITECTURE.md §4, quality rule) runs on the SQLite copy exactly
as it runs on Zetaris: every table Steward reads is counted and compared with its CSV."""
from pathlib import Path

from app.adapters.verify_sources import report, verify
from app.adapters.zetaris import SampleData
from app.config import SETTINGS

DATA = Path(SETTINGS.domain_dir) / "data"
TABLES = {"members": "brikk.members", "trust": "brikk.trust", "topics": "brikk.topics", "rules": "brikk.rules",
          "project": "brikk.project", "profiles": "brikk.profiles", "finance": "brikk.finance",
          "procedures": "brikk.procedures", "tasks": "brikk.tasks"}


def test_every_table_matches_its_csv():
    data = SampleData(DATA, "brikk")
    lines = verify(data, DATA, TABLES)
    assert [l["table"] for l in lines] == list(TABLES.values())
    assert all(l["ok"] for l in lines), report(lines)
    assert next(l for l in lines if l["table"] == "brikk.members")["found"] == 13  # 12 people + the intern


def test_a_short_table_is_a_finding():
    data = SampleData(DATA, "brikk")
    data.conn.execute("DELETE FROM brikk.tasks WHERE task_id = 't07'")
    lines = verify(data, DATA, {"tasks": "brikk.tasks", "members": "brikk.members"})
    tasks = next(l for l in lines if l["table"] == "brikk.tasks")
    assert tasks["ok"] is False and tasks["found"] == tasks["expected"] - 1
    assert "1 table(s) differ" in report(lines)


def test_a_missing_table_is_a_finding_not_a_crash():
    data = SampleData(DATA, "brikk")
    lines = verify(data, DATA, {"members": "brikk.members"}, {"member": "lightning.metastore.osef.brikk_usl.member"})
    usl = next(l for l in lines if l["table"].endswith("brikk_usl.member"))
    assert usl["ok"] is False and usl["found"] is None and usl["error"]
