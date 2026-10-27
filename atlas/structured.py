"""The common LLM call: JSON output validated by a pydantic schema.

Every agent goes through call_json():
- routes, in order: Nightshift (Meterless Runtime) with a Nemotron model
  imposed by its id, then the MODEL_* route (NVIDIA API) if configured, then
  the cache of earlier replies (data/cache/llm/); SAMPLE_MODE=true reads the
  cache only; LLM_CACHE_FIRST=true reads the cache first and calls a route only
  for a prompt never answered (to record a cache that replays consistently:
  the model is not deterministic, even at temperature 0);
- a timeout on each request;
- an invalid output (not JSON, or not matching the schema) is sent back once
  with the validation error; a second invalid output raises LLMOutputError;
- one JSONL trace line per call, with the model actually used, read in the
  reply (Nightshift's receipt `meterless.routed_model`), not the one requested.
"""
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
from pydantic import ValidationError

from atlas import llm
from atlas.zetaris import sample_mode

ROOT = llm.ROOT
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"  # verified via Nightshift, 27/10
DEFAULT_TIMEOUT = 90  # seconds per request
MAX_TOKENS = 4000  # Nemotron may reason before answering: leave room for it
DEFAULT_CACHE_DIR = ROOT / "data" / "cache" / "llm"
DEFAULT_TRACE_FILE = ROOT / "logs" / "llm-trace.jsonl"
SUMMARY_CHARS = 200


class LLMUnavailable(Exception):
    """No route answered and no cached reply exists."""


class LLMOutputError(Exception):
    """The model's output stayed invalid after one retry."""


@dataclass
class Route:
    name: str          # "nightshift" or "model_api"
    base_url: str      # ends with /v1
    headers: dict
    model: str


@dataclass
class Reply:
    text: str
    model: str         # the model actually used, read in the reply
    route: str         # route name, or "cache"
    receipt_id: str | None = None


def default_routes(model=None):
    routes = [Route("nightshift", llm.get_base_url(), llm._headers(llm.get_token(), chat=True),
                    model or os.environ.get("NIGHTSHIFT_MODEL") or DEFAULT_MODEL)]
    if os.environ.get("MODEL_BASE_URL") and os.environ.get("NEMOTRON_MODEL"):
        routes.append(Route("model_api", os.environ["MODEL_BASE_URL"].rstrip("/"),
                            {"Authorization": f"Bearer {os.environ.get('MODEL_API_KEY', '')}"},
                            os.environ["NEMOTRON_MODEL"]))
    return routes


class Tracer:
    """Appends one JSON line per LLM call."""

    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("LLM_TRACE_FILE") or DEFAULT_TRACE_FILE)

    def write(self, record):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as trace:
            trace.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_json(text):
    """The JSON object in a reply, tolerating code fences or text around it."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def unwrap_schema_echo(text, schema):
    """The object inside {"properties": {...}, ...}, a shape Nemotron sometimes
    answers with when shown a schema (with "type" or "required" around it);
    any other text is returned unchanged."""
    if "properties" in schema.model_fields:
        return text
    try:
        data = json.loads(text)
    except ValueError:
        return text
    if (isinstance(data, dict) and isinstance(data.get("properties"), dict)
            and not set(data) & set(schema.model_fields)):
        return json.dumps(data["properties"])
    return text


def schema_instructions(schema):
    # "an instance", because Nemotron otherwise tends to answer with the
    # schema's own shape ({"properties": {...}}).
    return ("Answer with one JSON object only, no text before or after it: an instance "
            "of this JSON schema (the values themselves, not the schema):\n"
            + json.dumps(schema.model_json_schema()))


class LLMClient:
    def __init__(self, routes=None, timeout=DEFAULT_TIMEOUT, cache_dir=None, sample=None,
                 tracer=None, cache_first=None):
        self.routes = routes if routes is not None else default_routes()
        self.timeout = timeout
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self.sample = sample_mode() if sample is None else sample
        self.tracer = tracer or Tracer()
        self.cache_first = (os.environ.get("LLM_CACHE_FIRST", "").strip().lower()
                            in ("1", "true", "yes")) if cache_first is None else cache_first

    # --- cache --------------------------------------------------------------

    def _cache_path(self, messages):
        key = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        return self.cache_dir / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}.json"

    def _read_cache(self, messages):
        try:
            entry = json.loads(self._cache_path(messages).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        return Reply(entry["text"], entry["model"], "cache", entry.get("receipt_id"))

    def _write_cache(self, messages, reply):
        path = self._cache_path(messages)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"messages": messages, "text": reply.text, "model": reply.model,
                                    "route": reply.route, "receipt_id": reply.receipt_id},
                                   ensure_ascii=False, indent=1), encoding="utf-8")

    # --- one completion -----------------------------------------------------

    def _post(self, route, messages):
        response = requests.post(
            f"{route.base_url}/chat/completions", headers=route.headers, timeout=self.timeout,
            json={"model": route.model, "messages": messages, "max_tokens": MAX_TOKENS,
                  "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}})
        if response.status_code != 200:
            raise LLMUnavailable(f"{route.name}: HTTP {response.status_code} "
                                 f"{' '.join(response.text.split())[:200]}")
        body = response.json()
        receipt = body.get("meterless") or {}
        text = body["choices"][0]["message"].get("content") or ""
        model = receipt.get("routed_model") or body.get("model") or "unknown"
        return Reply(text, model, route.name, receipt.get("receipt_id"))

    def complete(self, messages):
        """One reply, from the first route that answers, else from the cache."""
        failures = []
        if self.cache_first and not self.sample:
            cached = self._read_cache(messages)
            if cached is not None:
                return cached, failures
        if not self.sample:
            for route in self.routes:
                try:
                    reply = self._post(route, messages)
                except (requests.RequestException, LLMUnavailable, KeyError, ValueError) as error:
                    failures.append(f"{route.name}: {str(error)[:200] or type(error).__name__}")
                    continue
                self._write_cache(messages, reply)
                return reply, failures
        cached = self._read_cache(messages)
        if cached is None:
            reason = "SAMPLE_MODE and no cached reply" if self.sample else "; ".join(failures)
            raise LLMUnavailable(f"no LLM reply ({reason})")
        return cached, failures

    # --- the structured call ------------------------------------------------

    def call_json(self, agent, action, system, user, schema):
        """Return (validated output, Reply). One retry on an invalid output."""
        messages = [{"role": "system", "content": f"{system}\n\n{schema_instructions(schema)}"},
                    {"role": "user", "content": user}]
        started = time.monotonic()
        record = {"agent": agent, "action": action, "input_summary": user[:SUMMARY_CHARS],
                  "requested_model": self.routes[0].model if self.routes else None}
        reply, error, failures = None, None, []
        for attempt in (1, 2):
            try:
                reply, route_failures = self.complete(messages)
            except LLMUnavailable as unavailable:
                self._trace(record, started, attempt, "unavailable", error=str(unavailable))
                raise
            failures += route_failures
            try:
                output = schema.model_validate_json(
                    unwrap_schema_echo(extract_json(reply.text), schema))
            except ValidationError as invalid:
                error = invalid
                messages = messages + [
                    {"role": "assistant", "content": reply.text},
                    {"role": "user", "content": "Your answer is not valid against the schema: "
                                                f"{_short_errors(invalid)}. Answer again with the "
                                                "corrected JSON object only."}]
                continue
            self._trace(record, started, attempt, "ok", reply=reply, failures=failures)
            return output, reply
        self._trace(record, started, 2, "invalid_output", reply=reply, failures=failures,
                    error=_short_errors(error))
        raise LLMOutputError(f"{agent}/{action}: invalid output after one retry: "
                             f"{_short_errors(error)}")

    def _trace(self, record, started, attempts, status, reply=None, failures=(), error=None):
        self.tracer.write({
            "ts": datetime.now(timezone.utc).isoformat(), **record,
            "output_summary": reply.text[:SUMMARY_CHARS] if reply else None,
            "model": reply.model if reply else None,
            "route": reply.route if reply else None,
            "receipt_id": reply.receipt_id if reply else None,
            "attempts": attempts, "retries": attempts - 1, "status": status,
            "fallbacks": list(failures), "error": error,
            "latency_ms": round((time.monotonic() - started) * 1000)})


def _short_errors(error):
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'output'}: {e['msg']}"
                     for e in error.errors()[:5])
