"""World Model adapter: the project state kept by the World Model engine (task 7).

WorldModelStateStore implements the StateStore interface of agent/state.py
(load() and commit()) on top of the World Model service (services/world_model/,
the Meterless reference implementation served over local HTTP). The state's
semantics stay those of agent/state.py: commit() computes the new state with
apply_change(), then sends only what changed. World Model adds what the JSON
file does not have: an append-only event log with an audit entry per write,
stable ids so a record written again is an upsert (S5), and bitemporal edges
(a task's owner, a report's task and author, the decision a decision
replaces) that keep their history when they change.

The JSON state stays the fallback (decision D12): with SAMPLE_MODE=true, or
once the service cannot be reached, the store uses JsonStateStore for the rest
of its life; `origin` says which one answered.

Command line:
    python -m agent.world_model health
    python -m agent.world_model state <project>
"""
import json
import os
import sys
from typing import Optional

import requests

from agent.state import (RECORD_TABLES, Change, JsonStateStore, ProjectState, StateStore,
                         apply_change, record_key)
from agent.zetaris import sample_mode

DEFAULT_URL = "http://127.0.0.1:8766"
DEFAULT_TIMEOUT = 5  # seconds: a local service either answers fast or is down
# Tables kept in append order by the state; World Model returns entities
# sorted by id, so their order is stored in the project context.
ORDERED_TABLES = ("decisions", "facts")


class WorldModelError(Exception):
    """The World Model service refused a request, or could not be reached.

    unavailable is True for a timeout, a network error or a 5xx: only those
    switch the store to the JSON fallback, so a bad request is never hidden.
    """

    def __init__(self, message, unavailable=False):
        super().__init__(message)
        self.unavailable = unavailable


def _key(table, record):
    return str(record.id if table in ORDERED_TABLES else record_key(table, record))


def _records(state, table):
    return {_key(table, r): r for r in getattr(state, table)}


def _links(table, record):
    """Single-target edges of a record: a new target closes the old edge."""
    if table == "tasks":
        return [("owned_by", ("roles", record.member))]
    if table == "reports":
        return [("about_task", ("tasks", record.task_id)), ("reported_by", ("roles", record.member))]
    if table == "decisions" and record.supersedes:
        return [("supersedes", ("decisions", record.supersedes))]
    return []


def state_diff(old: ProjectState, new: ProjectState):
    """Records of `new` that are absent or different in `old`, and their edges."""
    upserts, links = [], []
    for table in (*sorted(RECORD_TABLES), *ORDERED_TABLES):
        before = _records(old, table)
        for key, record in _records(new, table).items():
            if before.get(key) == record:
                continue
            upserts.append({"table": table, "key": key, "record": record.model_dump(mode="json")})
            links += [{"from": {"table": table, "key": key}, "type": kind,
                       "to": {"table": target, "key": target_key}}
                      for kind, (target, target_key) in _links(table, record)]
    return upserts, links


def _meta(state: ProjectState):
    return {"version": state.version, "ingested": state.ingested,
            "history": [h.model_dump(mode="json") for h in state.history],
            "order": {t: [r.id for r in getattr(state, t)] for t in ORDERED_TABLES}}


def state_from_engine(project, reply):
    """Rebuild the ProjectState from what World Model holds."""
    meta = reply.get("meta") or {}
    records = reply.get("records") or {}
    fields = {"project": project, "version": meta.get("version", 0),
              "ingested": meta.get("ingested", []), "history": meta.get("history", [])}
    for table in RECORD_TABLES:
        fields[table] = sorted(records.get(table, []),
                               key=lambda r: str(r.get("member") if table == "roles" else r.get("id")))
    for table in ORDERED_TABLES:
        by_id = {r["id"]: r for r in records.get(table, [])}
        fields[table] = [by_id[i] for i in meta.get("order", {}).get(table, []) if i in by_id]
    return ProjectState.model_validate(fields)


class WorldModelStateStore(StateStore):
    """The project state in World Model, with the JSON state as fallback."""

    def __init__(self, project, base_url=None, timeout=DEFAULT_TIMEOUT, sample=None,
                 fallback=None, session=None):
        self.project = project
        self.base_url = (base_url or os.environ.get("WORLD_MODEL_URL", DEFAULT_URL)).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.fallback = fallback or JsonStateStore(project)
        self.fallback_reason = "SAMPLE_MODE" if (sample_mode() if sample is None else sample) \
            else None

    @property
    def origin(self):
        """"world-model", "json" (SAMPLE_MODE) or "json-fallback"."""
        if self.fallback_reason is None:
            return "world-model"
        return "json" if self.fallback_reason == "SAMPLE_MODE" else "json-fallback"

    def _request(self, method, path, body=None):
        try:
            response = self.session.request(method, f"{self.base_url}{path}", json=body,
                                            timeout=self.timeout)
        except requests.RequestException as error:
            raise WorldModelError(f"cannot reach the World Model service at {self.base_url}: "
                                  f"{type(error).__name__}", unavailable=True) from error
        if response.status_code != 200:
            raise WorldModelError(f"World Model service: HTTP {response.status_code}: "
                                  f"{' '.join(response.text.split())[:300]}",
                                  unavailable=response.status_code >= 500)
        return response.json()

    def _engine(self, operation):
        """Run `operation` on World Model; fall back to the JSON state for good
        when the service is unavailable. Returns (result, used_engine)."""
        if self.fallback_reason is not None:
            return None, False
        try:
            return operation(), True
        except WorldModelError as error:
            if not error.unavailable:
                raise
            self.fallback_reason = str(error)
            return None, False

    def _load_engine(self):
        return state_from_engine(self.project,
                                 self._request("GET", f"/projects/{self.project}/state"))

    def load(self) -> ProjectState:
        state, used = self._engine(self._load_engine)
        return state if used else self.fallback.load()

    def commit(self, change: Change) -> Optional[int]:
        def write():
            old = self._load_engine()
            new = apply_change(old, change)
            if new is None:
                return None
            upserts, links = state_diff(old, new)
            self._request("POST", f"/projects/{self.project}/commit",
                          {"at": new.history[-1].at.isoformat(), "upserts": upserts,
                           "links": links, "meta": _meta(new)})
            return new.version

        version, used = self._engine(write)
        return version if used else self.fallback.commit(change)

    def edges(self, kind=None):
        """Current and closed edges of the project graph, from World Model."""
        suffix = f"?type={kind}" if kind else ""
        return self._request("GET", f"/projects/{self.project}/edges{suffix}")["edges"]


def main(argv):
    if argv[1:2] == ["health"]:
        store = WorldModelStateStore("atlas")
        print(json.dumps(store._request("GET", "/health"), indent=1))
        return 0
    if len(argv) == 3 and argv[1] == "state":
        store = WorldModelStateStore(argv[2])
        state = store.load()
        print(json.dumps({"origin": store.origin, "version": state.version,
                          **{t: len(getattr(state, t)) for t in (*RECORD_TABLES, *ORDERED_TABLES)}},
                         indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
