"""Zetaris client against a fake server: timeout, cache, SAMPLE_MODE."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import requests

from atlas.sources import load_source, load_source_zetaris
from atlas.zetaris import ZetarisClient, ZetarisError

ROOT = Path(__file__).resolve().parent.parent


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class FakeSession:
    """Answers like /sql-editor/sqls/run, or fails the way it is told to."""

    def __init__(self, reply=None, error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def post(self, url, headers, json, timeout):
        self.calls.append({"url": url, "headers": headers, "body": json, "timeout": timeout})
        if self.error:
            raise self.error
        return self.reply


OK = FakeResponse(200, {"headers": ["id", "value"], "data": [["DEC-004", "2026-11-10"]],
                        "total": 1, "timeUsed": 12})


class ZetarisClientTest(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".test-tmp"  # git-ignored, stays on the project's disk
        base.mkdir(exist_ok=True)
        self.cache = tempfile.mkdtemp(dir=base)
        self.addCleanup(shutil.rmtree, self.cache, ignore_errors=True)

    def client(self, session, sample=False):
        return ZetarisClient(base_url="http://zetaris.test/api/", org_id="1", api_key="k",
                             timeout=7, cache_dir=self.cache, sample=sample, session=session)

    def test_query_sends_sql_with_timeout_and_returns_records(self):
        session = FakeSession(reply=OK)
        result = self.client(session).query("SELECT id,  value\nFROM atlas.decisions")
        call = session.calls[0]
        self.assertEqual(call["url"], "http://zetaris.test/api/sql-editor/sqls/run")
        self.assertEqual(call["timeout"], 7)
        self.assertEqual(call["body"]["sql"], "SELECT id, value FROM atlas.decisions")
        self.assertEqual(result.origin, "zetaris")
        self.assertEqual(result.records(), [{"id": "DEC-004", "value": "2026-11-10"}])

    def test_result_is_cached_then_read_back_in_sample_mode(self):
        self.client(FakeSession(reply=OK)).query("SELECT 1")
        offline = FakeSession(error=AssertionError("SAMPLE_MODE must not call Zetaris"))
        result = self.client(offline, sample=True).query("SELECT 1")
        self.assertEqual(result.origin, "cache")
        self.assertEqual(result.rows, [["DEC-004", "2026-11-10"]])
        self.assertEqual(offline.calls, [])

    def test_sample_mode_without_cache_fails_clearly(self):
        with self.assertRaisesRegex(ZetarisError, "SAMPLE_MODE"):
            self.client(FakeSession(reply=OK), sample=True).query("SELECT 2")

    def test_timeout_falls_back_to_the_cache(self):
        self.client(FakeSession(reply=OK)).query("SELECT 1")
        result = self.client(FakeSession(error=requests.Timeout())).query("SELECT 1")
        self.assertEqual(result.origin, "cache-fallback")

    def test_timeout_without_cache_raises(self):
        with self.assertRaises(ZetarisError) as caught:
            self.client(FakeSession(error=requests.ConnectionError())).query("SELECT 1")
        self.assertTrue(caught.exception.unavailable)

    def test_sql_error_is_never_hidden_by_the_cache(self):
        self.client(FakeSession(reply=OK)).query("SELECT 1")
        refused = FakeSession(reply=FakeResponse(400, {"msg": "TABLE_OR_VIEW_NOT_FOUND"}))
        with self.assertRaisesRegex(ZetarisError, "HTTP 400"):
            self.client(refused).query("SELECT 1")

    def test_statements_that_change_the_instance_are_not_cached(self):
        self.client(FakeSession(reply=OK)).query("CREATE LIGHTNING DATABASE X", use_cache=False)
        self.assertEqual(os.listdir(self.cache), [])


class CommittedCacheTest(unittest.TestCase):
    """The committed cache lets a clean clone run SAMPLE_MODE without Zetaris."""

    def test_every_source_is_cached_and_matches_the_sample(self):
        client = ZetarisClient(sample=True, session=FakeSession(error=AssertionError()))
        for name in ("decisions", "tasks", "messages", "tickets", "reports", "roles",
                     "documents", "milestones", "past_projects"):
            with self.subTest(source=name):
                records, origin = load_source_zetaris(name, client)
                self.assertEqual(origin, "cache")
                self.assertEqual(records, load_source(name))


if __name__ == "__main__":
    unittest.main()
