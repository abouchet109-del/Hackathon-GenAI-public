"""Integration: the Python client against the running H-MEM service.

Start the service first (README, "H-MEM"); without it these tests are skipped.
Each run writes under its own subject and ids (project "atlas-test"), so a
persisted store from an earlier run never changes the result, and the
project's own decisions are never touched.
"""
import os
import unittest
import uuid
from datetime import datetime, timezone

import requests

from atlas.hmem import DEFAULT_URL, HMem, HMemError, load_org_lessons
from atlas.sources import load_source

URL = os.environ.get("ATLAS_HMEM_URL", DEFAULT_URL)
AT = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def service_running():
    try:
        return requests.get(URL + "/health", timeout=2).json().get("engine") == "hmem-reference"
    except (requests.RequestException, ValueError):
        return False


@unittest.skipUnless(service_running(),
                     f"H-MEM service not running at {URL}: start it with "
                     f"python scripts/engine_service.py hmem (README, section Engines)")
class HMemServiceTest(unittest.TestCase):
    def setUp(self):
        self.memory = HMem(base_url=URL, sample=False)
        self.run = uuid.uuid4().hex[:8]
        self.subject = f"atlas-launch-{self.run}"
        self.decisions = {}
        for decision in load_source("decisions"):
            if decision.subject == "atlas-launch":
                renamed = decision.model_copy(update={
                    "id": f"{decision.id}-{self.run}", "subject": self.subject,
                    "supersedes": f"{decision.supersedes}-{self.run}" if decision.supersedes else None})
                self.decisions[decision.id] = renamed
                self.memory.record_decision(renamed, "atlas-test")

    def test_why_10_november_from_the_engine(self):
        explanation = self.memory.explain(self.subject, "launch_date")
        self.assertEqual(self.memory.origin, "hmem-service")
        current = explanation.current
        self.assertEqual(current.external_id, f"DEC-004-{self.run}")
        self.assertEqual(current.tag("value"), "2026-11-10")
        self.assertEqual(current.source, "register REG-2026-021")
        self.assertEqual(current.provenance.refs, ["REG-2026-021"])
        self.assertEqual(current.confidence, 1.0)
        old = explanation.history[0]
        self.assertEqual(old.superseded_by, current.id)
        self.assertEqual([(e.action, e.memory_id) for e in explanation.trust_log],
                         [("create", old.id), ("create", current.id), ("update", old.id)])
        self.assertIn(f"replaces DEC-001-{self.run} (2026-11-03", explanation.text())

    def test_writing_the_same_decision_twice_creates_nothing(self):
        _, created = self.memory.record_decision(self.decisions["DEC-004"], "atlas-test")
        self.assertFalse(created)
        self.assertEqual(len(self.memory.explain(self.subject, "launch_date").history), 2)

    def test_feedback_is_applied_by_the_engine_and_logged(self):
        current = self.memory.explain(self.subject, "sso_release").current
        after = self.memory.feedback(current.id, "wrong", AT)
        self.assertAlmostEqual(after.confidence, 0.8)
        self.assertIn("review", after.tags)
        entry = self.memory.explain(self.subject, "sso_release").trust_log[-1]
        self.assertEqual(entry.action, "feedback")
        self.assertEqual(entry.details["kind"], "wrong")

    def test_record_without_source_is_refused_not_hidden_by_the_fallback(self):
        with self.assertRaises(HMemError):
            self.memory.remember(f"X-{self.run}", "text", "working", [], "", "manual", "",
                                 [], 0.5, AT)
        self.assertEqual(self.memory.origin, "hmem-service")

    def test_orion_lesson_is_recalled_from_the_organisation_memory(self):
        load_org_lessons(self.memory, load_source("past_projects"))
        self.assertEqual(load_org_lessons(self.memory, load_source("past_projects")), 0)
        recalled = self.memory.recall("commercial-brief acceptance-testing launch: "
                                      "brief envoyé avant la fin de la recette", top_n=1)
        self.assertEqual(recalled[0].memory.external_id, "LES-ORION-1")
        self.assertEqual(recalled[0].memory.layer, "long_term")


if __name__ == "__main__":
    unittest.main()
