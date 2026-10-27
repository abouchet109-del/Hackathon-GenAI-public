"""A complete run in SAMPLE_MODE, on the caches of the real runs.

Zetaris answers from data/cache/zetaris/, the LLM from data/cache/llm/ (the
replies Nemotron gave in the real runs of S1 and S3), H-MEM from its local
backend: the real logic runs offline. The results are compared with
data/expected/. A prompt change invalidates the LLM cache: rerun S1 and S3
for real (README) to refresh it.
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from atlas.orchestrator import RunRequest, run
from tests.test_orchestrator import EXPECTED, TODAY

ROOT = Path(__file__).resolve().parent.parent


class SampleRunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / ".test-tmp"
        base.mkdir(exist_ok=True)
        cls.tmp = Path(tempfile.mkdtemp(dir=base))
        with mock.patch.dict(os.environ, {"SAMPLE_MODE": "true"}):
            cls.s1 = run(RunRequest(today=TODAY), state_dir=cls.tmp, log_dir=cls.tmp)
            cls.s3 = run(RunRequest(today=TODAY, scenario="S3"), state_dir=cls.tmp,
                         log_dir=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def verdicts(self, result, source):
        return [v for v in result.verdicts if v.source == source]

    def test_runs_offline_from_the_caches(self):
        for result in (self.s1, self.s3):
            self.assertTrue(result.sample_mode)
            self.assertEqual(result.degraded, [])
            self.assertTrue(all(o.startswith("cache") for o in result.sources.values()))
            self.assertEqual(result.memory, "local")
            self.assertIsNone(result.limits.stopped)
            self.assertIsNotNone(result.report)

    def test_s1_expected_decisions_are_in_force(self):
        # data/expected lists three decisions; the run also holds a decision of
        # MSG-001 on csv-export/export_formats (docs/STATUS.md, open point).
        in_force = {(i.key, i.value, i.decision) for i in self.s1.in_force}
        for expected in EXPECTED["S1"]["in_force"]:
            self.assertIn((expected["key"], expected["value"], expected["decision"]), in_force)
        self.assertEqual(self.s1.conflicts, {})

    def test_s1_records_not_applied(self):
        decided = {v.source for v in self.s1.verdicts
                   if v.verdict == "accepted" and v.info_type == "decision"}
        for record in EXPECTED["S1"]["not_applied"]:
            self.assertNotIn(f"messages/{record['record']}", decided, record["reason"])
        self.assertEqual(self.verdicts(self.s1, "messages/MSG-009")[0].verdict, "ignored")

    def test_s1_unauthorised_claim_goes_through_one_revision(self):
        first, *rest = self.verdicts(self.s1, "messages/MSG-008")
        self.assertEqual((first.verdict, first.author), ("revision", "sarah"))
        self.assertTrue(rest and rest[0].revision == 1)

    def test_s3_conflict_escalated_to_marc_and_no_date_applied(self):
        [conflict] = EXPECTED["S3"]["decision_conflicts"]
        self.assertEqual(self.s3.conflicts, {conflict["key"]: conflict["decisions"]})
        self.assertIn(("decisions/DEC-007", "marc"),
                      [(e.source, e.to) for e in self.s3.escalations])
        self.assertNotIn(conflict["key"], {i.key for i in self.s3.in_force})
        self.assertFalse(self.s3.facts.milestones[0].on_track)

    def test_the_trace_names_the_model_that_answered(self):
        lines = (ROOT / self.s1.trace_file).read_text(encoding="utf-8").splitlines()
        models = {json.loads(line).get("model") for line in lines} - {None}
        self.assertTrue(models and all(m.startswith("nvidia/nemotron") for m in models), models)


if __name__ == "__main__":
    unittest.main()
