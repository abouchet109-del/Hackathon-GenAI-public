"""Orchestrator (task 22): one run of the system, end to end, in code.

A run reads the sources through Zetaris, then brick 1 in order (structured
records, the decision register, the messages through extractor, update agent
and controller, the writer), then the manager agent. It carries the limits
(LLM calls, wall-clock timeout; one revision per proposal is in the
controller), the fallbacks (Zetaris cache, then local files; a message whose
LLM call fails is skipped and retried by the next run) and SAMPLE_MODE
(Zetaris and the LLM answered from their caches, H-MEM local). Every step
and every LLM call writes one JSONL line in logs/run-<run_id>.jsonl.

The project state lives in World Model (agent/world_model.py, JSON state as
fallback) and persists from one run to the next, so a second run only reads
what is new (S5). A scenario run (S2, S3) starts from a fresh JSON state of
its own, so a test decision never enters the project's state.

Command line:
    python -m agent.orchestrator [--scenario S3] [--today 2026-10-27] [--fresh]
"""
import argparse
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from agent.alerts import Alert, AlertInbox
from agent.controller import control
from agent.extractor import extract_message
from agent.hmem import HMem, load_org_lessons
from agent.manager import (DEFAULT_QUESTION, Escalated, InForce, ManagerReport, ProjectFacts,
                           project_facts, write_report)
from agent.sources import SOURCES, load_source, load_source_zetaris, parse_records
from agent.state import DEFAULT_STATE_DIR, JsonStateStore, apply_change
from agent.structured import (DEFAULT_MODEL, LLMClient, LLMOutputError, LLMUnavailable, Route,
                              Tracer, default_routes)
from agent.updater import UnknownCandidate, from_register, propose, revise
from agent.world_model import WorldModelStateStore
from agent.writer import StateWriter, change_for
from agent.zetaris import ROOT, ZetarisClient, ZetarisError, sample_mode

SCENARIO_DIR = ROOT / "data" / "scenarios"
LOG_DIR = ROOT / "logs"
RECORD_SOURCES = ("roles", "tasks", "milestones", "tickets", "reports")
DEFAULT_MAX_LLM_CALLS = 120
DEFAULT_TIMEOUT_S = 900
# Brick 1 needs judgment the 30B model lacks on this corpus (sources misread,
# kinds mixed up): the 550B model is the default of a run, and the 30B model
# a second Nightshift route if it does not answer (D16).
RUN_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"


class RunRequest(BaseModel):
    """Input of POST /run and of the command line."""
    model_config = ConfigDict(extra="forbid")
    project: str = "atlas"
    question: str = DEFAULT_QUESTION
    today: date                      # explicit: the rules never read the clock
    scenario: Optional[str] = Field(default=None, pattern=r"^S\d+$")
    # None: a fresh state for a scenario run, the persistent state otherwise.
    fresh_state: Optional[bool] = None
    max_llm_calls: int = Field(default=DEFAULT_MAX_LLM_CALLS, ge=1, le=500)
    timeout_s: int = Field(default=DEFAULT_TIMEOUT_S, ge=10, le=3600)


class Verdict(BaseModel):
    """One controller verdict, as the run reports it."""
    source: str
    proposal: str
    revision: int
    kind: str
    key: str
    value: str
    info_type: str
    author: str
    verdict: str
    reason: str
    escalate_to: Optional[str] = None


class Limits(BaseModel):
    llm_calls: int
    max_llm_calls: int
    elapsed_s: float
    timeout_s: int
    stopped: Optional[str] = None    # why the run stopped early, if it did


class RunResult(BaseModel):
    run_id: str
    project: str
    scenario: Optional[str]
    today: date
    sample_mode: bool
    state_store: str                 # "world-model", "json", "json-fallback", "json-fresh"
    state_version: int
    sources: dict[str, str]          # source -> where it was read from
    memory: str                      # H-MEM backend that answered
    in_force: list[InForce]
    conflicts: dict[str, list[str]]
    verdicts: list[Verdict]
    escalations: list[Escalated]
    alerts: list[Alert]
    facts: ProjectFacts
    report: Optional[ManagerReport]
    limits: Limits
    degraded: list[str]              # fallbacks taken and sources skipped
    trace_file: str


def run_routes():
    """Nightshift with the run's model, then Nightshift with the default model,
    then the MODEL_* route if configured. NIGHTSHIFT_MODEL overrides the first."""
    first, *others = default_routes(os.environ.get("NIGHTSHIFT_MODEL") or RUN_MODEL)
    routes = [first]
    if first.model != DEFAULT_MODEL:
        routes.append(Route("nightshift-30b", first.base_url, first.headers, DEFAULT_MODEL))
    return routes + others


def store_origin(store):
    return getattr(store, "origin", "json-fresh")


class LimitReached(Exception):
    """The run's LLM budget or timeout is used up."""


class RunTracer(Tracer):
    """The LLM trace and the orchestration events of one run, in one file."""

    def __init__(self, path, run_id):
        super().__init__(path)
        self.run_id = run_id

    def write(self, record):
        super().write({"run_id": self.run_id, **record})

    def event(self, agent, action, status, input_summary="", output_summary="", **extra):
        self.write({"ts": datetime.now(timezone.utc).isoformat(), "agent": agent,
                    "action": action, "input_summary": input_summary,
                    "output_summary": output_summary, "status": status, **extra})


class BudgetedLLM:
    """The LLM client with the run's limits: a number of calls and a deadline."""

    def __init__(self, client, max_calls, deadline):
        self.client = client
        self.max_calls = max_calls
        self.deadline = deadline
        self.calls = 0

    def check(self):
        if time.monotonic() > self.deadline:
            raise LimitReached("run timeout reached")
        if self.calls >= self.max_calls:
            raise LimitReached(f"LLM budget of {self.max_calls} calls used up")

    def call_json(self, *args, **kwargs):
        self.check()
        self.calls += 1
        return self.client.call_json(*args, **kwargs)


# --- reading the sources ------------------------------------------------------------

def scenario_records(scenario):
    """Records a scenario adds to one source (data/scenarios/<s>-*.json)."""
    added = {}
    for path in sorted(SCENARIO_DIR.glob(f"{scenario.lower()}-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        added.setdefault(payload["source"], []).extend(parse_records(payload["source"], payload))
    if not added:
        raise ValueError(f"unknown scenario {scenario}: no file data/scenarios/"
                         f"{scenario.lower()}-*.json")
    return added


def read_sources(zetaris, degraded):
    """Every source through Zetaris (or its cache); local files as last resort."""
    def read(name):
        try:
            return name, *load_source_zetaris(name, zetaris)
        except ZetarisError as error:
            degraded.append(f"{name}: Zetaris failed ({error}); read from data/sample/")
            return name, load_source(name), "files"

    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        results = list(pool.map(read, SOURCES))
    return ({name: records for name, records, _ in results},
            {name: origin for name, _, origin in results})


# --- brick 1 ----------------------------------------------------------------------------

def _verdict(ref, proposal, result):
    return Verdict(source=ref, proposal=proposal.id, revision=proposal.revision,
                   kind=proposal.kind, key=f"{proposal.subject}/{proposal.attribute}",
                   value=proposal.value, info_type=proposal.info_type, author=proposal.author,
                   verdict=result.verdict, reason=result.reason,
                   escalate_to=result.escalate_to)


class Run:
    """The state of one run: what brick 1 decided, wrote and gave up on."""

    def __init__(self, llm, tracer, writer, store):
        self.llm = llm
        self.tracer = tracer
        self.writer = writer
        self.store = store
        self.verdicts = []
        self.escalations = []
        self.alerts = []
        self.degraded = []

    def record(self, ref, proposal, result):
        verdict = _verdict(ref, proposal, result)
        self.verdicts.append(verdict)
        self.tracer.event("controller", "verdict", result.verdict,
                          input_summary=f"{proposal.id} rev {proposal.revision}: {verdict.key} = "
                                        f"{proposal.value} ({proposal.info_type}, {proposal.kind}, "
                                        f"by {proposal.author})",
                          output_summary=result.reason[:300], escalate_to=result.escalate_to,
                          revision_request=result.revision_request)
        if result.verdict == "escalated":
            self.escalations.append(Escalated(proposal=proposal.id, source=ref,
                                              to=result.escalate_to, reason=result.reason))

    def ingest_records(self, sources):
        outcome = self.writer.ingest_records({name: sources[name] for name in RECORD_SOURCES},
                                             refs=[], summary="structured sources")
        self.tracer.event("writer", "ingest records", "changed" if outcome.changed else "same",
                          output_summary=f"state version {outcome.version}")

    def ingest_register(self, decisions):
        """The register in one write: each entry checked by the code against the
        state as the previous entries leave it, so a replaced decision is
        recorded in the memory but alerts only go out for what is in force."""
        state = self.store.load()
        results, refs = [], []
        for record in sorted(decisions, key=lambda d: (d.date, d.id)):
            ref = f"decisions/{record.id}"
            if state.is_ingested(ref):
                continue
            proposal = from_register(record, state.project)
            result = control(self.llm, proposal, state, ref, record=record)
            self.record(ref, proposal, result)
            results.append((result, proposal))
            refs.append(ref)
            state = apply_change(state, change_for([ref], [(result, proposal)])) or state
        if refs:
            self.write(refs, results, "decision register")

    def write(self, refs, results, summary):
        outcome = self.writer.write(refs, results, summary)
        self.alerts += outcome.alerts
        self.tracer.event("writer", "write", "changed" if outcome.changed else "same",
                          input_summary=", ".join(refs)[:200],
                          output_summary=f"version {outcome.version}; decisions "
                                         f"{outcome.decisions}; facts {len(outcome.facts)}; "
                                         f"alerts {len(outcome.alerts)}; memories "
                                         f"{len(outcome.memories)}")

    def ingest_message(self, message):
        ref = f"messages/{message.id}"
        state = self.store.load()
        if state.is_ingested(ref):
            return
        candidates = extract_message(self.llm, message, state)
        proposals = propose(self.llm, candidates, state)
        by_id = {c.id: c for c in candidates}
        results = []
        for proposal in proposals:
            result = control(self.llm, proposal, state, ref, message.text)
            self.record(ref, proposal, result)
            if result.verdict == "revision":
                proposal = revise(self.llm, proposal, by_id[proposal.candidate_ids[0]],
                                  result.revision_request, state)
                result = control(self.llm, proposal, state, ref, message.text)
                self.record(ref, proposal, result)
            results.append((result, proposal))
        self.write([ref], results, f"message {message.id}")

    def ingest_messages(self, messages):
        for message in sorted(messages, key=lambda m: (m.sent_at, m.id)):
            try:
                self.ingest_message(message)
            except (LLMUnavailable, LLMOutputError, UnknownCandidate) as error:
                # Not marked as ingested: the next run reads this message again.
                self.degraded.append(f"messages/{message.id} skipped: {error}")
                self.tracer.event("orchestrator", "skip message", "error",
                                  input_summary=message.id, output_summary=str(error)[:300])


# --- one run -----------------------------------------------------------------------------

def open_store(request, base, run_id):
    """(store, directory of the alert inboxes) for this run."""
    fresh = request.fresh_state if request.fresh_state is not None else bool(request.scenario)
    if fresh:
        base = base / "runs" / run_id
        return JsonStateStore(request.project, state_dir=base), base
    fallback = JsonStateStore(request.project, state_dir=base)
    return WorldModelStateStore(request.project, fallback=fallback), base


def run(request, state_dir=None, llm_client=None, zetaris=None, memory=None, log_dir=None,
        store=None):
    """Run the system once; return the structured result.

    The keyword arguments replace the real services, for tests."""
    started = time.monotonic()
    added = scenario_records(request.scenario) if request.scenario else {}
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    trace_file = Path(log_dir or LOG_DIR) / f"run-{run_id}.jsonl"
    tracer = RunTracer(trace_file, run_id)
    base = Path(state_dir or DEFAULT_STATE_DIR)
    if store is None:
        store, base = open_store(request, base, run_id)
    memory = memory or HMem()
    writer = StateWriter(store, AlertInbox(request.project, state_dir=base), memory)
    client = llm_client or LLMClient(routes=run_routes(), tracer=tracer)
    llm = BudgetedLLM(client, request.max_llm_calls, started + request.timeout_s)
    current = Run(llm, tracer, writer, store)
    tracer.event("orchestrator", "start", "ok", input_summary=request.model_dump_json(),
                 output_summary=f"state in {base}; SAMPLE_MODE={sample_mode()}")

    sources, origins = read_sources(zetaris or ZetarisClient(), current.degraded)
    for name, records in added.items():
        sources[name] = sources[name] + records
        origins[name] += f" + data/scenarios ({request.scenario})"
    tracer.event("orchestrator", "read sources", "ok",
                 output_summary=json.dumps({n: [origins[n], len(sources[n])] for n in sources}))

    lessons = load_org_lessons(memory, sources["past_projects"])
    tracer.event("orchestrator", "load organisation memory", "ok",
                 output_summary=f"{lessons} new lessons in H-MEM ({memory.origin})")
    stopped, report = None, None
    current.ingest_records(sources)
    current.ingest_register(sources["decisions"])
    try:
        current.ingest_messages(sources["messages"])
    except LimitReached as limit:
        stopped = str(limit)
    state = store.load()
    facts = project_facts(state, current.escalations, request.today)
    if stopped is None:
        try:
            report = write_report(llm, request.question, facts)
        except (LLMUnavailable, LLMOutputError, LimitReached) as error:
            current.degraded.append(f"manager report not written: {error}; facts only")
    else:
        current.degraded.append(f"stopped before the end: {stopped}")
    if store_origin(store) == "json-fallback":
        current.degraded.append(f"World Model unavailable, JSON state used: "
                                f"{store.fallback_reason}")
    if memory.fallback_reason:
        current.degraded.append(f"H-MEM unavailable, local memory used: {memory.fallback_reason}")

    result = RunResult(
        run_id=run_id, project=request.project, scenario=request.scenario,
        today=request.today, sample_mode=sample_mode(), state_store=store_origin(store),
        state_version=state.version,
        sources=origins, memory=memory.origin, in_force=facts.in_force,
        conflicts=facts.conflicts, verdicts=current.verdicts,
        escalations=current.escalations, alerts=current.alerts, facts=facts, report=report,
        limits=Limits(llm_calls=llm.calls, max_llm_calls=request.max_llm_calls,
                      elapsed_s=round(time.monotonic() - started, 1),
                      timeout_s=request.timeout_s, stopped=stopped),
        degraded=current.degraded, trace_file=str(trace_file.relative_to(ROOT))
        if trace_file.is_relative_to(ROOT) else str(trace_file))
    tracer.event("orchestrator", "end", "stopped" if stopped else "ok",
                 output_summary=f"version {state.version}; {len(current.verdicts)} verdicts; "
                                f"{len(current.escalations)} escalations; "
                                f"{llm.calls} LLM calls; degraded {len(current.degraded)}")
    return result


def main(argv):
    parser = argparse.ArgumentParser(description="Run the Atlas project memory once.")
    parser.add_argument("--project", default="atlas")
    parser.add_argument("--scenario", help="S2 or S3: add data/scenarios/<s>-*.json")
    parser.add_argument("--today", default=date.today().isoformat(),
                        help="reference date of the rules (default: today)")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--fresh", action="store_true", default=None,
                        help="start from an empty state (the default for a scenario)")
    parser.add_argument("--max-llm-calls", type=int, default=DEFAULT_MAX_LLM_CALLS)
    parser.add_argument("--out", help="write the full JSON result to this file")
    args = parser.parse_args(argv)
    request = RunRequest(project=args.project, question=args.question,
                         today=date.fromisoformat(args.today), scenario=args.scenario,
                         fresh_state=args.fresh, max_llm_calls=args.max_llm_calls)
    result = run(request)
    payload = result.model_dump_json(indent=1)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main(sys.argv[1:])
