"""State writer: one write per source, alerts for decisions in force, H-MEM."""
import shutil
import tempfile
import unittest
from pathlib import Path

from agent.alerts import AlertInbox
from agent.contracts import ControllerResult
from agent.controller import control
from agent.hmem import HMem, LocalBackend
from agent.sources import load_all
from agent.state import JsonStateStore
from agent.updater import from_register
from agent.writer import StateWriter
from tests.scripted import ScriptedLLM
from tests.test_controller import proposal

ROOT = Path(__file__).resolve().parent.parent
SOURCES = load_all()


class WriterTest(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".test-tmp"
        base.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=base))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.store = JsonStateStore("atlas", state_dir=self.tmp)
        self.inbox = AlertInbox("atlas", state_dir=self.tmp)
        self.memory = HMem(backend=LocalBackend())
        self.writer = StateWriter(self.store, self.inbox, self.memory)
        self.writer.ingest_records(
            {name: SOURCES[name] for name in ("roles", "tasks", "milestones", "tickets",
                                              "reports")}, refs=[])

    def write_register(self, records):
        results = []
        for record in records:
            state = self.store.load()
            p = from_register(record, "atlas")
            results.append((control(ScriptedLLM([]), p, state, f"decisions/{record.id}",
                                    record=record), p))
            self.writer.write([f"decisions/{record.id}"], results[-1:])
        return results

    def test_validated_decision_alerts_the_affected_members_and_goes_to_hmem(self):
        dec1, dec2, dec3, dec4, dec5 = SOURCES["decisions"]
        self.write_register([dec1, dec2, dec3])
        p = from_register(dec4, "atlas")
        result = control(ScriptedLLM([]), p, self.store.load(), "decisions/DEC-004",
                         record=dec4)
        outcome = self.writer.write(["decisions/DEC-004"], [(result, p)])
        self.assertTrue(outcome.changed)
        self.assertEqual(sorted(a.member for a in outcome.alerts), ["hugo", "ines", "sarah"])
        self.assertEqual(len(outcome.memories), 1)
        self.assertIn("2026-11-10", self.memory.explain("atlas-launch", "launch_date").text())

    def test_rewriting_the_same_source_changes_nothing(self):
        dec1 = SOURCES["decisions"][0]
        self.write_register([dec1])
        version = self.store.load().version
        p = from_register(dec1, "atlas")
        result = ControllerResult(proposal_id=p.id, verdict="accepted", checks=[],
                                  decision=dec1, reason="again")
        outcome = self.writer.write(["decisions/DEC-001"], [(result, p)])
        self.assertFalse(outcome.changed)
        self.assertEqual((outcome.version, outcome.alerts), (version, []))

    def test_accepted_fact_and_ignored_proposal(self):
        fact = proposal(kind="observation", info_type="observation", subject="csv-export",
                        attribute="qa_status", value="failing", supersedes=None, author="ines")
        accepted = ControllerResult(proposal_id=fact.id, verdict="accepted", checks=[],
                                    reason="ok")
        ignored = ControllerResult(proposal_id="PROP-X", verdict="ignored", checks=[],
                                   reason="helios")
        outcome = self.writer.write(["messages/MSG-099"], [(accepted, fact), (ignored, fact)])
        state = self.store.load()
        self.assertEqual(outcome.facts, [fact.id])
        self.assertEqual([f.value for f in state.facts], ["failing"])
        self.assertTrue(state.is_ingested("messages/MSG-099"))

    def test_conflicting_register_entry_is_recorded_without_alert_or_memory(self):
        self.write_register(SOURCES["decisions"])
        dec7 = SOURCES["decisions"][3].model_copy(update={
            "id": "DEC-007", "value": "2026-11-17", "author": "marc", "supersedes": None})
        p = from_register(dec7, "atlas")
        result = control(ScriptedLLM([]), p, self.store.load(), "decisions/DEC-007",
                         record=dec7)
        outcome = self.writer.write(["decisions/DEC-007"], [(result, p)])
        self.assertEqual((result.verdict, outcome.alerts, outcome.memories),
                         ("escalated", [], []))
        state = self.store.load()
        self.assertNotIn(("atlas-launch", "launch_date"), state.in_force())
        self.assertEqual([c.key for c in state.conflicts()], [("atlas-launch", "launch_date")])


if __name__ == "__main__":
    unittest.main()
