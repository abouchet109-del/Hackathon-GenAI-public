"""H-MEM client on its local fallback: provenance, trust ledger, feedback, recall."""
import unittest
from datetime import datetime, timezone

import requests

from agent.hmem import HMem, HMemError, HttpBackend, LocalBackend, load_org_lessons
from agent.sources import load_source

AT = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def corpus_memory():
    memory = HMem(backend=LocalBackend())
    for decision in load_source("decisions"):
        memory.record_decision(decision, "atlas")
    return memory


class DecisionMemoryTest(unittest.TestCase):
    def test_decision_is_written_with_its_provenance_and_confidence(self):
        memory = corpus_memory()
        current = memory.explain("atlas-launch", "launch_date").current
        self.assertEqual(current.external_id, "DEC-004")
        self.assertEqual(current.tag("value"), "2026-11-10")
        self.assertEqual(current.source, "register REG-2026-021")
        self.assertEqual(current.provenance.origin, "document")
        self.assertIn("REG-2026-021", current.provenance.refs)
        self.assertEqual(current.confidence, 1.0)
        self.assertEqual(current.recorded_at.date().isoformat(), "2026-10-20")

    def test_why_10_november_gives_history_and_trust_log(self):
        explanation = corpus_memory().explain("atlas-launch", "launch_date")
        self.assertEqual([m.external_id for m in explanation.history], ["DEC-001", "DEC-004"])
        old = explanation.history[0]
        self.assertEqual(old.superseded_by, explanation.current.id)
        actions = [(e.action, e.memory_id) for e in explanation.trust_log]
        self.assertEqual(actions, [("create", old.id), ("create", explanation.current.id),
                                   ("update", old.id)])
        text = explanation.text()
        self.assertIn("2026-11-10", text)
        self.assertIn("REG-2026-021", text)
        self.assertIn("replaces DEC-001 (2026-11-03", text)

    def test_writing_the_same_decision_twice_creates_nothing(self):
        memory = corpus_memory()
        decision = load_source("decisions")[3]
        _, created = memory.record_decision(decision, "atlas")
        self.assertFalse(created)
        self.assertEqual(len(memory.explain("atlas-launch", "launch_date").history), 2)

    def test_two_approved_values_in_force_are_not_resolved_by_memory(self):
        memory = HMem(backend=LocalBackend())
        first, second = load_source("decisions")[0], load_source("decisions")[3]
        memory.record_decision(first, "atlas")
        memory.record_decision(second.model_copy(update={"supersedes": None}), "atlas")
        explanation = memory.explain("atlas-launch", "launch_date")
        self.assertIsNone(explanation.current)
        self.assertEqual(len(explanation.history), 2)

    def test_unknown_subject_has_no_current_value(self):
        explanation = corpus_memory().explain("atlas-launch", "budget")
        self.assertIsNone(explanation.current)
        self.assertIn("No decision", explanation.text())

    def test_memory_without_source_is_rejected(self):
        with self.assertRaises(HMemError):
            HMem(backend=LocalBackend()).remember("X-1", "text", "working", [], " ",
                                                  "manual", "", [], 0.5, AT)


class FeedbackTest(unittest.TestCase):
    def test_feedback_moves_confidence_by_the_reference_deltas_and_is_logged(self):
        memory = corpus_memory()
        current = memory.explain("atlas-launch", "sso_release").current
        self.assertAlmostEqual(memory.feedback(current.id, "wrong", AT).confidence, 0.8)
        after = memory.feedback(current.id, "helpful", AT)
        self.assertAlmostEqual(after.confidence, 0.85)
        self.assertIn("review", after.tags)
        entry = memory.explain("atlas-launch", "sso_release").trust_log[-1]
        self.assertEqual((entry.action, entry.confidence_before), ("feedback", 0.8))
        self.assertAlmostEqual(entry.confidence_after, 0.85)

    def test_feedback_on_unknown_memory_fails_clearly(self):
        with self.assertRaises(HMemError):
            corpus_memory().feedback("mem-99", "helpful", AT)


class OrganisationMemoryTest(unittest.TestCase):
    def test_orion_lesson_is_recalled_for_a_brief_sent_before_acceptance(self):
        memory = HMem(backend=LocalBackend())
        self.assertEqual(load_org_lessons(memory, load_source("past_projects")), 3)
        recalled = memory.recall("commercial-brief acceptance-testing launch: "
                                 "brief envoyé avant la fin de la recette", top_n=1)
        self.assertEqual(recalled[0].memory.external_id, "LES-ORION-1")
        self.assertEqual(recalled[0].memory.layer, "long_term")

    def test_loading_lessons_twice_writes_nothing_new(self):
        memory = HMem(backend=LocalBackend())
        load_org_lessons(memory, load_source("past_projects"))
        self.assertEqual(load_org_lessons(memory, load_source("past_projects")), 0)

    def test_recall_stays_in_the_organisation_layer(self):
        memory = corpus_memory()
        load_org_lessons(memory, load_source("past_projects"))
        layers = {r.memory.layer for r in memory.recall("atlas launch date decision")}
        self.assertLessEqual(layers, {"long_term"})


class FailingSession:
    def __init__(self, error=None, status=None):
        self.error = error
        self.status = status
        self.calls = 0

    def request(self, method, url, json=None, params=None, timeout=None):
        self.calls += 1
        if self.error:
            raise self.error
        return type("Response", (), {"status_code": self.status, "text": "bad request",
                                     "json": lambda self: {}})()


class FallbackTest(unittest.TestCase):
    def test_sample_mode_uses_the_local_fallback(self):
        self.assertEqual(HMem(sample=True).origin, "local")

    def test_unreachable_service_switches_to_the_fallback_for_good(self):
        session = FailingSession(error=requests.ConnectTimeout("timed out"))
        memory = HMem(backend=HttpBackend("http://hmem.test", 1, session))
        memory.record_decision(load_source("decisions")[0], "atlas")
        self.assertEqual(memory.origin, "local-fallback")
        self.assertIn("ConnectTimeout", memory.fallback_reason)
        self.assertEqual(memory.explain("atlas-launch", "launch_date").current.external_id,
                         "DEC-001")
        self.assertEqual(session.calls, 1)

    def test_a_refused_request_is_not_hidden_by_the_fallback(self):
        memory = HMem(backend=HttpBackend("http://hmem.test", 1, FailingSession(status=400)))
        with self.assertRaises(HMemError):
            memory.health()
        self.assertEqual(memory.origin, "hmem-service")


if __name__ == "__main__":
    unittest.main()
