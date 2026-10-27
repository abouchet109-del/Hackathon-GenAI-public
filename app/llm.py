"""POWER layer: every model call goes through Meterless Nightshift (OpenAI-compatible).

- Three lanes: fast (structuring), deep (deciding), judge (critique). Map them to
  Nemotron lanes in Nightshift with METERLESS_MODEL_FAST/DEEP/JUDGE.
- Every real response is recorded in data/llm_cache.jsonl (RECORD_LLM=true).
- In SAMPLE_MODE, or when Nightshift is unreachable, recorded responses are replayed
  when the exact same prompt was seen before; otherwise the caller gets None and
  falls back to its deterministic path. Nothing is ever invented here.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ROOT, SETTINGS

CACHE = ROOT / "data" / "llm_cache.jsonl"
_lock = threading.Lock()


@dataclass
class LLMResult:
    text: str
    model: str
    source: str  # "nightshift" | "replay"
    receipt_id: str | None = None  # Nightshift's receipt, when the runtime returns one


def served_model(resp, requested: str) -> tuple[str, str | None]:
    """The model that actually answered, and the receipt id. Nightshift puts both in a `meterless` block
    (`routed_model`, `receipt_id`); without it, the OpenAI `model` field; without that, the lane requested.
    The team verified the receipt shape against Nightshift on 27/10 (atlas/structured.py)."""
    try:
        data = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)
    except Exception:  # noqa: BLE001 - an unexpected response shape must not lose the answer
        data = {}
    receipt = data.get("meterless") if isinstance(data.get("meterless"), dict) else {}
    model = receipt.get("routed_model") or data.get("model") or getattr(resp, "model", None) or requested
    return str(model), (str(receipt["receipt_id"]) if receipt.get("receipt_id") else None)


def _key(lane_model: str, messages: list[dict[str, str]]) -> str:
    blob = json.dumps({"m": lane_model, "msgs": messages}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def _load_cache() -> dict[str, dict[str, Any]]:
    if not CACHE.exists():
        return {}
    out = {}
    for line in CACHE.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            out[row["key"]] = row
        except (json.JSONDecodeError, KeyError):
            continue
    return out


class LLM:
    def __init__(self, settings=SETTINGS):
        self.s = settings
        self._client = None
        self._cache = _load_cache()
        if self.s.llm_ready:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.s.meterless_token,
                base_url=self.s.meterless_base_url,
                timeout=self.s.llm_timeout,
                max_retries=2,
                default_headers={"meterless-app": self.s.meterless_app, "meterless-scope": "user"},
            )

    @property
    def online(self) -> bool:
        return self._client is not None

    def lane(self, name: str) -> str:
        return {"fast": self.s.model_fast, "deep": self.s.model_deep, "judge": self.s.model_judge}[name]

    def chat(self, lane: str, system: str, user: str) -> LLMResult | None:
        model = self.lane(lane)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        key = _key(model, messages)
        if self._client is not None:
            try:
                resp = self._client.chat.completions.create(model=model, messages=messages, temperature=0.2)
                text = resp.choices[0].message.content or ""
                served_by, receipt_id = served_model(resp, model)
                if self.s.record_llm:
                    self._record(key, model, served_by, text)
                return LLMResult(text=text, model=served_by, source="nightshift", receipt_id=receipt_id)
            except Exception as error:  # noqa: BLE001 - network/provider failures fall back
                self.last_error = f"{type(error).__name__}: {error}"[:200]
        hit = self._cache.get(key)
        if hit:
            return LLMResult(text=hit["text"], model=hit["served_by"], source="replay")
        return None

    def _record(self, key: str, model: str, served_by: str, text: str) -> None:
        row = {"key": key, "lane_model": model, "served_by": served_by, "text": text}
        with _lock:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            with CACHE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            self._cache[key] = row


def parse_json(text: str) -> dict[str, Any] | None:
    """Extract the answer's JSON object. Tolerates ```json fences and reasoning models that think aloud
    (<think>...</think>, prose with braces): the first decodable object carrying an expected key wins."""
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for block in fenced:
        try:
            obj = json.loads(block)
            if isinstance(obj, dict):
                candidates.append(obj)
        except json.JSONDecodeError:
            pass
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            candidates.append(obj)
    expected = {"decision", "scores", "items", "total"}
    for obj in candidates:
        if expected & obj.keys():
            return obj
    return candidates[0] if candidates else None
