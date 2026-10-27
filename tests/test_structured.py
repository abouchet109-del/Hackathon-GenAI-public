"""The common LLM call against a fake runtime: schema, one retry, timeout, trace."""
import json
import shutil
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import BaseModel

from agent.structured import (LLMClient, LLMOutputError, LLMUnavailable, Route, Tracer,
                              extract_json)

ROOT = Path(__file__).resolve().parent.parent


class LaunchDate(BaseModel):
    launch_date: str
    decision_id: str


class ScriptedRuntime(BaseHTTPRequestHandler):
    """Answers each chat request with the next scripted content, like Nightshift:
    the receipt names the model it actually routed to."""
    script = []
    seen = []
    delay = 0.0

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).seen.append(body)
        time.sleep(type(self).delay)
        content = type(self).script.pop(0)
        payload = {"model": body["model"],
                   "choices": [{"message": {"role": "assistant", "content": content}}],
                   "meterless": {"receipt_id": "rcpt_test", "requested_model": body["model"],
                                 "routed_model": "nvidia/nemotron-routed"}}
        data = json.dumps(payload).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except ConnectionError:
            pass  # the client gave up (timeout test)


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/v1"


VALID = '{"launch_date": "2026-11-10", "decision_id": "DEC-004"}'
CLOSED_PORT_URL = "http://127.0.0.1:9/v1"


class StructuredCallTest(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".test-tmp"  # git-ignored, stays on the project's disk
        base.mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=base))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        ScriptedRuntime.script, ScriptedRuntime.seen, ScriptedRuntime.delay = [], [], 0.0
        self.server, self.url = serve(ScriptedRuntime)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def client(self, urls=None, timeout=5, sample=False):
        routes = [Route(f"route{i}", url, {}, "nvidia/nemotron-requested")
                  for i, url in enumerate(urls or [self.url])]
        return LLMClient(routes=routes, timeout=timeout, cache_dir=self.tmp / "cache",
                         sample=sample, tracer=Tracer(self.tmp / "trace.jsonl"))

    def trace(self):
        lines = (self.tmp / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def call(self, client):
        return client.call_json("controller", "check", "You check decisions.",
                                "Which launch date is in force?", LaunchDate)

    def test_valid_output_is_validated_and_traced_with_the_model_used(self):
        ScriptedRuntime.script = [VALID]
        output, reply = self.call(self.client())
        self.assertEqual(output, LaunchDate(launch_date="2026-11-10", decision_id="DEC-004"))
        self.assertEqual(reply.model, "nvidia/nemotron-routed")
        request = ScriptedRuntime.seen[0]
        self.assertEqual(request["model"], "nvidia/nemotron-requested")
        self.assertIn('"launch_date"', request["messages"][0]["content"])  # schema sent
        [line] = self.trace()
        self.assertEqual((line["agent"], line["status"], line["attempts"]), ("controller", "ok", 1))
        self.assertEqual(line["model"], "nvidia/nemotron-routed")
        self.assertEqual(line["requested_model"], "nvidia/nemotron-requested")
        self.assertEqual(line["receipt_id"], "rcpt_test")

    def test_one_invalid_output_triggers_one_retry_with_the_error(self):
        ScriptedRuntime.script = ['{"launch_date": "2026-11-10"}', VALID]
        output, _ = self.call(self.client())
        self.assertEqual(output.decision_id, "DEC-004")
        self.assertEqual(len(ScriptedRuntime.seen), 2)
        retry = ScriptedRuntime.seen[1]["messages"][-1]["content"]
        self.assertIn("decision_id", retry)
        self.assertEqual(self.trace()[0]["attempts"], 2)

    def test_two_invalid_outputs_raise_a_clear_error(self):
        ScriptedRuntime.script = ["not json at all", '{"launch_date": 10}', VALID]
        with self.assertRaisesRegex(LLMOutputError, "controller/check"):
            self.call(self.client())
        self.assertEqual(len(ScriptedRuntime.seen), 2)  # no third attempt
        self.assertEqual(self.trace()[0]["status"], "invalid_output")

    def test_json_in_code_fences_is_accepted(self):
        self.assertEqual(extract_json(f"Here it is:\n```json\n{VALID}\n```"), VALID)

    def test_unreachable_route_falls_back_to_the_next_one(self):
        ScriptedRuntime.script = [VALID]
        _, reply = self.call(self.client([CLOSED_PORT_URL, self.url]))
        self.assertEqual(reply.route, "route1")
        self.assertEqual(len(self.trace()[0]["fallbacks"]), 1)

    def test_timeout_without_cache_raises_unavailable(self):
        ScriptedRuntime.script, ScriptedRuntime.delay = [VALID], 1.0
        with self.assertRaises(LLMUnavailable):
            self.call(self.client(timeout=0.2))
        self.assertEqual(self.trace()[0]["status"], "unavailable")

    def test_cached_reply_serves_sample_mode_and_outages(self):
        ScriptedRuntime.script = [VALID]
        self.call(self.client())
        output, reply = self.call(self.client(sample=True))
        self.assertEqual((output.decision_id, reply.route), ("DEC-004", "cache"))
        self.assertEqual(reply.model, "nvidia/nemotron-routed")  # the model that answered
        _, reply = self.call(self.client([CLOSED_PORT_URL]))
        self.assertEqual(reply.route, "cache")
        self.assertEqual(len(ScriptedRuntime.seen), 1)

    def test_sample_mode_without_cache_fails_clearly(self):
        with self.assertRaisesRegex(LLMUnavailable, "SAMPLE_MODE"):
            self.call(self.client(sample=True))


if __name__ == "__main__":
    unittest.main()
