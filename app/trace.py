"""Run traces: one JSONL file per run in logs/, plus readable lines on stdout.

Every event says which agent acted, what it did, for whom, with which model,
and how confident it was. Secrets are never written.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SECRET = re.compile(r"(?i)(bearer\s+[a-z0-9._\-]+|nvapi-[a-z0-9_\-]+|sk-[a-z0-9_\-]{8,})")


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _SECRET.sub("[redacted]", value)
    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


class Tracer:
    def __init__(self, run_id: str, log_dir: Path, quiet: bool = False):
        self.run_id = run_id
        self.quiet = quiet
        log_dir.mkdir(parents=True, exist_ok=True)
        self.path = log_dir / f"trace-{run_id}.jsonl"
        self.started = time.monotonic()
        self.events: list[dict[str, Any]] = []

    def event(self, agent: str, action: str, *, input_summary: str = "", output_summary: str = "",
              target: str | None = None, model: str | None = None, confidence: float | None = None,
              retry: int = 0, status: str = "success", **extra: Any) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": self.run_id,
            "agent_name": agent,
            "action": action,
            "input_summary": input_summary[:400],
            "output_summary": output_summary[:400],
            "target_agent": target,
            "model": model,
            "confidence": None if confidence is None else round(float(confidence), 3),
            "retry_count": retry,
            "status": status,
        }
        record.update(extra)
        record = _redact(record)
        self.events.append(record)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        if not self.quiet:
            arrow = f" -> {target}" if target else ""
            model_part = f" (model: {model})" if model else ""
            print(f"[{status.upper():>8}] run_id={self.run_id} {agent}{arrow}: {action} | {output_summary[:140]}{model_part}",
                  file=sys.stderr)
        return record

    @property
    def elapsed(self) -> float:
        return round(time.monotonic() - self.started, 2)
