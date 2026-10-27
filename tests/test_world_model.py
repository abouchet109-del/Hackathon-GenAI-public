"""World Model adapter: same state as the JSON store, kept by the engine.

The first tests need no service (diff, rebuild, fallback). The integration
tests run against the World Model service and are skipped when it is not
running; each run writes its own project, so earlier runs never interfere.
"""
import os
import shutil
import tempfile
import unittest
import uuid
from datetime import date
from pathlib import Path

import requests

from agent.sources import load_all
from agent.state import Change, JsonStateStore, ProjectState, apply_change
from agent.world_model import (DEFAULT_URL, WorldModelError, WorldModelStateStore,
                               _meta, state_diff, state_from_engine)
from tests.fixtures import task
from tests.test_state import fact

ROOT = Path(__file__).resolve().parent.parent
URL = os.environ.get("WORLD_MODEL_URL", DEFAULT_URL)


def corpus_change():
    sources = load_all()
    return Change(refs=[f"decisions/{d.id}" for d in sources["decisions"]],
                  records={"tasks": sources["tasks"], "roles": sources["roles"],
                           "milestones": sources["milestones"], "tickets": sources["tickets"],
                           "reports": sources["reports"]},
                  decisions=sources["decisions"], facts=[fact("F2"), fact("F1")],
                  summary="corpus")


def without_times(state):
    dump = state.model_dump(mode="json")
    for entry in dump["history"]:
        entry.pop("at")
    return dump


def temp_dir(test):
    base = ROOT / ".test-tmp"  # git-ignored, stays on the project's disk
    base.mkdir(exist_ok=True)
    path = Path(tempfile.mkdtemp(dir=base))
    test.addCleanup(shutil.rmtree, path, ignore_errors=True)
    return path


class DiffTest(unittest.TestCase):
    def test_diff_sends_only_new_or_changed_records_with_their_edges(self):
        old = apply_change(ProjectState(project="atlas"),
                           Change(records={"tasks": [task("T1", "hugo", date(2026, 10, 23))]}))
        new = apply_change(old, Change(records={"tasks": [task("T1", "sarah", date(2026, 10, 23)),
                                                          task("T2", "ines", date(2026, 10, 24))]}))
        upserts, links = state_diff(old, new)
        self.assertEqual([(u["table"], u["key"]) for u in upserts], [("tasks", "T1"), ("tasks", "T2")])
        self.assertIn({"from": {"table": "tasks", "key": "T1"}, "type": "owned_by",
                       "to": {"table": "roles", "key": "sarah"}}, links)
        self.assertEqual(state_diff(new, new), ([], []))

    def test_state_rebuilt_from_engine_records_equals_the_state(self):
        state = apply_change(ProjectState(project="atlas"), corpus_change())
        upserts, _ = state_diff(ProjectState(project="atlas"), state)
        records = {}
        for upsert in reversed(upserts):  # the engine returns entities in its own order
            records.setdefault(upsert["table"], []).append(upsert["record"])
        rebuilt = state_from_engine("atlas", {"meta": _meta(state), "records": records})
        self.assertEqual(rebuilt, state)
        self.assertEqual([f.id for f in rebuilt.facts], ["F2", "F1"])


class FailingSession:
    def __init__(self, error=None, status=None):
        self.error = error
        self.status = status
        self.calls = 0

    def request(self, method, url, json=None, timeout=None):
        self.calls += 1
        if self.error:
            raise self.error
        return type("Response", (), {"status_code": self.status, "text": "bad request"})()


class FallbackTest(unittest.TestCase):
    def test_sample_mode_uses_the_json_state(self):
        fallback = JsonStateStore("atlas", state_dir=temp_dir(self))
        store = WorldModelStateStore("atlas", sample=True, fallback=fallback,
                                     session=FailingSession(status=500))
        self.assertEqual(store.commit(Change(facts=[fact("F1")])), 1)
        self.assertEqual(store.origin, "json")
        self.assertEqual(store.session.calls, 0)

    def test_unreachable_service_switches_to_the_json_state_for_good(self):
        fallback = JsonStateStore("atlas", state_dir=temp_dir(self))
        session = FailingSession(error=requests.ConnectTimeout("timed out"))
        store = WorldModelStateStore("atlas", base_url="http://wm.test", sample=False,
                                     fallback=fallback, session=session)
        self.assertEqual(store.commit(Change(facts=[fact("F1")])), 1)
        self.assertEqual(store.origin, "json-fallback")
        self.assertIn("ConnectTimeout", store.fallback_reason)
        self.assertEqual([f.id for f in store.load().facts], ["F1"])
        self.assertEqual(session.calls, 1)

    def test_a_refused_request_is_not_hidden_by_the_fallback(self):
        store = WorldModelStateStore("atlas", base_url="http://wm.test", sample=False,
                                     fallback=JsonStateStore("atlas", state_dir=temp_dir(self)),
                                     session=FailingSession(status=400))
        with self.assertRaises(WorldModelError):
            store.load()
        self.assertEqual(store.origin, "world-model")


def service_running():
    try:
        return requests.get(URL + "/health", timeout=2).json().get("engine") == "world-model-reference"
    except (requests.RequestException, ValueError):
        return False


@unittest.skipUnless(service_running(),
                     f"World Model service not running at {URL}: start it with "
                     f"python scripts/engine_service.py world_model (README, section Engines)")
class WorldModelServiceTest(unittest.TestCase):
    def setUp(self):
        self.project = f"atlas-test-{uuid.uuid4().hex[:8]}"
        self.store = WorldModelStateStore(self.project, base_url=URL, sample=False,
                                          fallback=JsonStateStore(self.project,
                                                                  state_dir=temp_dir(self)))
        self.json = JsonStateStore(self.project, state_dir=temp_dir(self))

    def test_state_read_from_world_model_equals_the_json_state(self):
        change = corpus_change()
        self.assertEqual(self.store.commit(change), 1)
        self.json.commit(change)
        state = self.store.load()
        self.assertEqual(self.store.origin, "world-model")
        self.assertEqual(without_times(state), without_times(self.json.load()))
        self.assertEqual(state.in_force()[("atlas-launch", "launch_date")].id, "DEC-004")

    def test_reingesting_the_same_sources_writes_no_event(self):
        self.store.commit(corpus_change())
        events = requests.get(f"{URL}/projects/{self.project}/state", timeout=5).json()["events"]
        self.assertIsNone(self.store.commit(corpus_change()))
        after = requests.get(f"{URL}/projects/{self.project}/state", timeout=5).json()["events"]
        self.assertEqual(after, events)

    def test_a_new_owner_closes_the_old_edge(self):
        self.store.commit(Change(records={"tasks": [task("T1", "hugo", date(2026, 10, 23))]}))
        self.assertEqual(self.store.commit(Change(records={"tasks": [
            task("T1", "sarah", date(2026, 10, 23))]})), 2)
        edges = {e["to"]: e["validTo"] for e in self.store.edges("owned_by")}
        self.assertIsNotNone(edges["roles:atlas:hugo"])
        self.assertIsNone(edges["roles:atlas:sarah"])
        self.assertEqual(self.store.load().tasks[0].member, "sarah")

    def test_supersedes_is_an_edge_of_the_project_graph(self):
        self.store.commit(corpus_change())
        pairs = {(e["from"], e["to"]) for e in self.store.edges("supersedes")}
        self.assertIn(("decisions:atlas:DEC-004", "decisions:atlas:DEC-001"), pairs)


if __name__ == "__main__":
    unittest.main()
