"""BUILD layer, engine 1: Meterless H-MEM.

HMemClient talks to hmem-service/ (a small Node server that runs the Meterless H-MEM
reference implementation, which passes the official 13-check conformance suite).
If the service is down, LocalMemory keeps the run going with a plain keyword store,
and the trace says so: the demo and the judges always know which one answered.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from ..config import ROOT, SETTINGS


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9.\-]+", text.lower()) if len(t) > 2}


class HMemClient:
    name = "meterless-hmem"

    def __init__(self, settings=SETTINGS, space: str | None = None):
        self.base = settings.hmem_url.rstrip("/")
        self.space = space or settings.hmem_space

    def _post(self, path: str, body: dict) -> dict:
        resp = requests.post(f"{self.base}{path}", json={"space": self.space, **body}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> bool:
        try:
            return requests.get(f"{self.base}/health", timeout=2).ok
        except requests.RequestException:
            return False

    def add(self, content: str, tags: list[str], source: str, confidence: float = 0.9,
            event: str = "user_correction", supersedes: str | None = None) -> dict:
        body = {"content": content, "tags": tags, "source": source,
                "confidence": confidence, "layer": "long_term", "event": event}
        if supersedes:
            body["supersedes"] = supersedes
        return self._post("/add", body)

    def list(self, tag: str | None = None) -> list[dict]:
        """Every record (superseded ones included), oldest first; optionally only those carrying `tag`."""
        return self._post("/list", {"tag": tag} if tag else {}).get("memories", [])

    def query(self, text: str, top_n: int = 3, threshold: float = 0.25) -> list[dict]:
        return self._post("/query", {"query": text, "topN": top_n, "threshold": threshold}).get("memories", [])

    def feedback(self, memory_id: str, kind: str) -> None:
        self._post("/feedback", {"id": memory_id, "kind": kind})

    def reset(self) -> None:
        self._post("/reset", {})


class LocalMemory:
    """Fallback only: JSON file, keyword overlap. Not the Meterless engine."""
    name = "local-fallback"

    def __init__(self, space: str = "default"):
        self.space = space
        self.path = ROOT / "data" / f"memory-fallback-{space}.json"
        self._mtime = None
        self.records: list[dict] = []
        self._refresh()

    def _refresh(self) -> None:
        """Several processes (one MCP server per AI client) share the file: reload it when it changed."""
        if not self.path.exists():
            self.records, self._mtime = [], None
            return
        mtime = self.path.stat().st_mtime_ns
        if mtime != self._mtime:
            self.records = json.loads(self.path.read_text() or "[]")
            self._mtime = mtime

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.records, indent=1, ensure_ascii=False))
        self._mtime = self.path.stat().st_mtime_ns

    def health(self) -> bool:
        return True

    def add(self, content, tags, source, confidence=0.9, event="user_correction", supersedes=None) -> dict:
        self._refresh()
        rec = {"id": f"lm-{len(self.records) + 1}", "content": content, "tags": tags, "source": source,
               "confidence": confidence, "timestamp": time.time(), "supersedes": supersedes, "superseded_by": None}
        for old in self.records:
            if supersedes and old["id"] == supersedes:
                old["superseded_by"] = rec["id"]
        self.records.append(rec)
        self._save()
        return rec

    def list(self, tag=None) -> list[dict]:
        self._refresh()
        return [dict(r) for r in self.records if not tag or tag in r["tags"]]

    def query(self, text, top_n=3, threshold=0.25) -> list[dict]:
        self._refresh()
        q = _tokens(text)
        scored = []
        for rec in self.records:
            tokens = _tokens(rec["content"] + " " + " ".join(rec["tags"]))
            score = len(q & tokens) / max(1, len(q)) * rec["confidence"]  # share of the query covered
            if rec.get("superseded_by"):
                score -= 0.2  # same rule as H-MEM: superseded records are penalized, never deleted
            if score >= threshold:
                scored.append({**rec, "score": round(score, 3)})
        return sorted(scored, key=lambda r: -r["score"])[:top_n]

    def feedback(self, memory_id, kind) -> None:
        return None

    def reset(self) -> None:
        self.records = []
        self._save()


def make_memory(settings=SETTINGS, space: str | None = None):
    client = HMemClient(settings, space)
    if client.health():
        return client
    return LocalMemory(space or settings.hmem_space)


def load_seed(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
