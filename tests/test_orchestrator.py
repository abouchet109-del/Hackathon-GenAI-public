"""Orchestrator and POST /run, end to end without network.

Zetaris answers from its committed cache (SAMPLE_MODE client), H-MEM from its
local backend, and the LLM is a fake that answers by agent: the runs check the
order of the bricks, the limits, the fallbacks and the traces, and compare
S1 and S3 with the expected results.
"""
import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from agent import api
from agent.hmem import HMem, LocalBackend
from agent.orchestrator import RunRequest, run
from agent.state import JsonStateStore
from agent.structured import LLMUnavailable
from agent.zetaris import ZetarisClient
from evaluation.expected import EXPECTED_FILE

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 10, 27)
EXPECTED = {s["id"]: s for s in json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))["records"]}

SARAH_CLAIM = {"subject": "atlas-launch", "attribute": "launch_date", "value": "2026-11-03",
               "quote": "lancement le 3 novembre", "confidence": 0.9}


class FakeLLM:
    """Answers by agent. Only MSG-008 (sarah's unauthorised "decision") and
    MSG-009 (another project) carry information; every proposal is supported.
    The update agent keeps a decision on its first pass and requalifies it as
    a work declaration when the controller asks for a revision."""

    def __init__(self, fail_on=()):
        self.calls = []
        self.fail_on = set(fail_on)

    def call_json(self, agent, action, system, user, schema):
        self.calls.append((agent, action))
        if any(record in user for record in self.fail_on):
            raise LLMUnavailable("fake outage")
        reply = getattr(self, agent.replace("-", "_"))(action, user)
        return schema.model_validate(reply), SimpleNamespace(text=json.dumps(reply), model="fake")

    def extractor(self, action, user):
        if "messages/MSG-008" in user:
            return {"infos": [{**SARAH_CLAIM, "info_type": "decision"}]}
        if "messages/MSG-009" in user:
            return {"infos": [{**SARAH_CLAIM, "value": "2026-11-17", "info_type": "decision",
                               "quote": "confirmé au 17 novembre"}]}
        return {"infos": []}

    def updater(self, action, user):
        candidate = user.split("- ", 1)[1].split(":", 1)[0]
        revising = action.startswith("revise")
        draft = {"candidate_id": candidate, "subject": "atlas-launch",
                 "attribute": "launch_date", "rationale": "test", "confidence": 0.8,
                 "value": "2026-11-17" if "2026-11-17" in user else "2026-11-03"}
        if revising:
            return {"proposals": [{**draft, "kind": "observation",
                                   "info_type": "work_declaration"}]}
        return {"proposals": [{**draft, "kind": "supersede", "info_type": "decision",
                               "supersedes": "DEC-004"}]}

    def controller(self, action, user):
        return {"supported": True, "reason": "the text says it"}

    def manager(self, action, user):
        facts = json.loads(user.split("(data, not instructions):\n", 1)[1])
        return {"answer": "Le lancement est à risque.",
                "deadlines": [{"milestone": m["milestone"], "explanation": "; ".join(m["reasons"]),
                               "evidence": m["evidence"]} for m in facts["milestones"]],
                "members": [{"member": m["member"], "summary": "..."} for m in facts["members"]]}


class RunTest(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".test-tmp"
        base.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=base))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_once(self, llm=None, fresh_state=True, **request):
        """A run on a fresh state, or on a JSON state kept in the test's
        directory (never the World Model service)."""
        self.llm = llm or FakeLLM()
        store = None if fresh_state else JsonStateStore("atlas", state_dir=self.tmp)
        return run(RunRequest(today=TODAY, fresh_state=fresh_state, **request),
                   state_dir=self.tmp, llm_client=self.llm, zetaris=ZetarisClient(sample=True),
                   memory=HMem(backend=LocalBackend()), log_dir=self.tmp / "logs", store=store)

    def trace(self, result):
        lines = (ROOT / result.trace_file).read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def test_s1_decisions_in_force_match_the_expected_results(self):
        result = self.run_once()
        expected = {(i["key"], i["value"], i["decision"]) for i in EXPECTED["S1"]["in_force"]}
        self.assertEqual({(i.key, i.value, i.decision) for i in result.in_force}, expected)
        self.assertEqual(result.conflicts, {})
        self.assertEqual(set(result.sources.values()), {"cache"})
        self.assertIsNotNone(result.report)
        self.assertFalse(result.facts.milestones[0].on_track)

    def test_s1_not_applied_records(self):
        result = self.run_once()
        by_source = {}
        for verdict in result.verdicts:
            by_source.setdefault(verdict.source, []).append(verdict)
        self.assertEqual(by_source["messages/MSG-009"][0].verdict, "ignored")  # S4
        first, second = by_source["messages/MSG-008"]
        self.assertEqual((first.verdict, second.revision, second.verdict),
                         ("revision", 1, "accepted"))
        self.assertEqual(second.info_type, "work_declaration")

    def test_revision_and_verdicts_are_in_the_trace(self):
        result = self.run_once()
        events = self.trace(result)
        verdicts = [e for e in events if e["agent"] == "controller" and e["action"] == "verdict"]
        self.assertIn("revision", {e["status"] for e in verdicts})
        self.assertEqual({e["run_id"] for e in events}, {result.run_id})
        self.assertEqual((events[0]["action"], events[-1]["action"]), ("start", "end"))

    def test_s3_conflict_is_escalated_to_marc(self):
        result = self.run_once(scenario="S3")
        [conflict] = EXPECTED["S3"]["decision_conflicts"]
        self.assertEqual(result.conflicts, {conflict["key"]: conflict["decisions"]})
        self.assertEqual([(e.source, e.to) for e in result.escalations],
                         [("decisions/DEC-007", "marc")])
        self.assertNotIn("atlas-launch/launch_date", {i.key for i in result.in_force})
        self.assertIsNone(result.facts.milestones[0].date)
        events = self.trace(result)
        self.assertTrue(any(e["status"] == "escalated" and e.get("escalate_to") == "marc"
                            for e in events))

    def test_rerun_on_the_same_state_changes_nothing(self):
        first = self.run_once(fresh_state=False)
        second = self.run_once(fresh_state=False)
        self.assertEqual(second.state_version, first.state_version)  # S5
        self.assertEqual(second.verdicts, [])
        self.assertEqual([a for a, _ in self.llm.calls], ["manager"])

    def test_budget_stops_the_run_and_says_so(self):
        result = self.run_once(max_llm_calls=3)
        self.assertEqual(result.limits.llm_calls, 3)
        self.assertIn("budget", result.limits.stopped)
        self.assertIsNone(result.report)
        self.assertTrue(result.degraded)

    def test_failed_message_is_skipped_and_read_again_next_run(self):
        result = self.run_once(llm=FakeLLM(fail_on={"messages/MSG-008"}), fresh_state=False)
        self.assertTrue(any("MSG-008" in d for d in result.degraded))
        again = self.run_once(fresh_state=False)
        self.assertEqual({v.source for v in again.verdicts}, {"messages/MSG-008"})

    def test_unknown_scenario_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown scenario S42"):
            self.run_once(scenario="S42")


class ApiTest(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".test-tmp"
        base.mkdir(exist_ok=True)
        tmp = Path(tempfile.mkdtemp(dir=base))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        api.Handler.run_options = {"state_dir": tmp, "llm_client": FakeLLM(),
                                   "zetaris": ZetarisClient(sample=True),
                                   "memory": HMem(backend=LocalBackend()),
                                   "log_dir": tmp / "logs"}
        self.addCleanup(setattr, api.Handler, "run_options", {})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def post(self, body):
        request = urllib.request.Request(f"{self.url}/run", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_run_returns_the_structured_result(self):
        status, body = self.post({"today": "2026-10-27", "scenario": "S3"})
        self.assertEqual(status, 200)
        self.assertEqual(body["conflicts"], {"atlas-launch/launch_date": ["DEC-004", "DEC-007"]})
        self.assertIn("deadlines", body["report"])

    def test_invalid_request_is_refused_with_details(self):
        status, body = self.post({"today": "2026-10-27", "max_llm_calls": 0, "colour": "red"})
        self.assertEqual(status, 400)
        self.assertEqual({tuple(d["loc"]) for d in body["details"]},
                         {("max_llm_calls",), ("colour",)})

    def test_health(self):
        with urllib.request.urlopen(f"{self.url}/health", timeout=5) as response:
            self.assertTrue(json.loads(response.read())["ok"])


if __name__ == "__main__":
    unittest.main()
