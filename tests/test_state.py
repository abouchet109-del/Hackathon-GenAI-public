"""Project state: one new version per write, re-ingestion changes nothing (S5)."""
import shutil
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from agent.contracts import Evidence
from agent.sources import load_all
from agent.state import Change, Fact, JsonStateStore, ProjectState, apply_change
from tests.fixtures import decision, task

ROOT = Path(__file__).resolve().parent.parent


def fact(id, value="failing"):
    return Fact(id=id, subject="csv-export", attribute="qa_status", value=value,
                info_type="observation", author="ines",
                stated_at=datetime(2026, 10, 27, 9, 15),
                evidence=[Evidence(table="messages", record_id="MSG-013")])


class StateStoreTest(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".test-tmp"  # git-ignored, stays on the project's disk
        base.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=base))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.store = JsonStateStore("atlas", state_dir=self.tmp)

    def test_empty_state_has_version_zero(self):
        self.assertEqual(self.store.load(), ProjectState(project="atlas"))

    def test_each_write_creates_a_new_version(self):
        v1 = self.store.commit(Change(refs=["decisions/D1"],
                                      decisions=[decision("D1", "launch_date", "2026-11-03")]))
        v2 = self.store.commit(Change(refs=["messages/MSG-013"], facts=[fact("F1")]))
        self.assertEqual((v1, v2), (1, 2))
        state = self.store.load()
        self.assertEqual([h.version for h in state.history], [1, 2])
        self.assertEqual(state.history[1].refs, ["messages/MSG-013"])

    def test_reingesting_the_same_sources_changes_nothing(self):
        sources = load_all()
        change = Change(refs=[f"decisions/{d.id}" for d in sources["decisions"]],
                        records={"tasks": sources["tasks"], "roles": sources["roles"]},
                        decisions=sources["decisions"])
        self.assertEqual(self.store.commit(change), 1)
        before = self.store.path.read_text(encoding="utf-8")
        self.assertIsNone(self.store.commit(change))
        self.assertEqual(self.store.path.read_text(encoding="utf-8"), before)
        state = self.store.load()
        self.assertEqual(len(state.decisions), len(sources["decisions"]))
        self.assertEqual(state.in_force()[("atlas-launch", "launch_date")].id, "DEC-004")

    def test_a_ref_alone_is_recorded_once(self):
        # A message that yields nothing is still ingested, so it is not re-read.
        self.assertEqual(self.store.commit(Change(refs=["messages/MSG-009"])), 1)
        self.assertTrue(self.store.load().is_ingested("messages/MSG-009"))
        self.assertIsNone(self.store.commit(Change(refs=["messages/MSG-009"])))

    def test_a_changed_record_replaces_the_stored_one(self):
        self.store.commit(Change(records={"tasks": [task("T1", "hugo", date(2026, 10, 23))]}))
        version = self.store.commit(Change(records={"tasks": [task("T1", "hugo",
                                                                   date(2026, 10, 30))]}))
        self.assertEqual(version, 2)
        [stored] = self.store.load().tasks
        self.assertEqual(stored.due, date(2026, 10, 30))

    def test_same_fact_id_is_not_duplicated(self):
        self.store.commit(Change(facts=[fact("F1")]))
        self.assertIsNone(self.store.commit(Change(facts=[fact("F1")])))
        self.assertEqual(len(self.store.load().facts), 1)

    def test_apply_change_is_pure(self):
        state = ProjectState(project="atlas")
        new = apply_change(state, Change(facts=[fact("F1")]))
        self.assertEqual((state.version, state.facts), (0, []))
        self.assertEqual(new.version, 1)


class StateReadsTest(unittest.TestCase):
    def setUp(self):
        sources = load_all()
        self.state = apply_change(ProjectState(project="atlas"), Change(
            records={name: sources[name] for name in ("roles", "tasks", "milestones",
                                                      "tickets", "reports")},
            decisions=sources["decisions"]))

    def test_authorised_members_come_from_the_role_table(self):
        members = [r.member for r in self.state.authorised("atlas-launch", "launch_date")]
        self.assertEqual(members, ["lea", "marc"])  # nora approves helios only

    def test_open_blockers(self):
        self.assertEqual([t.id for t in self.state.open_blockers()], ["TCK-QA-012"])

    def test_known_keys_include_decisions_reports_and_roles(self):
        keys = self.state.known_keys()
        for key in [("atlas-launch", "launch_date"), ("csv-export", "export_formats"),
                    ("csv-export", "qa_status")]:
            self.assertIn(key, keys)


if __name__ == "__main__":
    unittest.main()
