"""Zetaris client: SQL over the REST API, with a timeout and a cache.

Zetaris is the read-only data layer: the agents send SQL, Zetaris reads the
sources (REST tables registered by scripts/register_zetaris.py).

Every successful query is written to the cache (data/cache/zetaris/, one JSON
file per query). With SAMPLE_MODE=true the client reads the cache only and
never calls Zetaris; otherwise, when Zetaris fails, it falls back to the cache
and says so in the result.

Command line:
    python -m atlas.zetaris "<sql>"
"""
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_DIR = ROOT / "data" / "cache" / "zetaris"
DEFAULT_TIMEOUT = 60  # seconds: a REST table calls its source on each query
DEFAULT_LIMIT = 1000
load_dotenv(ROOT / ".env")


class ZetarisError(Exception):
    """Zetaris refused the query, or could not be reached and nothing is cached.

    unavailable is True for a timeout, a network error or a 5xx: only those
    fall back to the cache, so a wrong query is never hidden by an old result.
    """

    def __init__(self, message, unavailable=False):
        super().__init__(message)
        self.unavailable = unavailable


def sample_mode():
    return os.environ.get("SAMPLE_MODE", "").strip().lower() in ("1", "true", "yes")


def _normalise(sql):
    return " ".join(sql.split())


class QueryResult:
    def __init__(self, sql, columns, rows, origin, fetched_at):
        self.sql = sql
        self.columns = columns
        self.rows = rows
        self.origin = origin  # "zetaris", "cache" (SAMPLE_MODE) or "cache-fallback"
        self.fetched_at = fetched_at

    def records(self):
        return [dict(zip(self.columns, row)) for row in self.rows]


class ZetarisClient:
    def __init__(self, base_url=None, org_id=None, api_key=None, timeout=DEFAULT_TIMEOUT,
                 cache_dir=None, sample=None, session=None):
        self.base_url = (base_url or os.environ.get("ZETARIS_REST_URL", "")).rstrip("/")
        self.org_id = org_id or os.environ.get("ZETARIS_ORG_ID", "")
        self._key = api_key or os.environ.get("ZETARIS_API_KEY", "")
        self.timeout = timeout
        self.cache_dir = Path(cache_dir or os.environ.get("ZETARIS_CACHE_DIR") or DEFAULT_CACHE_DIR)
        self.sample = sample_mode() if sample is None else sample
        self.session = session or requests.Session()

    # --- cache ------------------------------------------------------------

    def _cache_path(self, sql, limit):
        digest = hashlib.sha256(f"{_normalise(sql)}|{limit}".encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, sql, limit, origin):
        try:
            entry = json.loads(self._cache_path(sql, limit).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        return QueryResult(entry["sql"], entry["columns"], entry["rows"], origin,
                           entry["fetched_at"])

    def _write_cache(self, result, limit):
        path = self._cache_path(result.sql, limit)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"sql": result.sql, "limit": limit, "fetched_at": result.fetched_at,
                 "columns": result.columns, "rows": result.rows}
        path.write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- queries ----------------------------------------------------------

    def _call(self, sql, limit):
        if not (self.base_url and self.org_id and self._key):
            raise ZetarisError("ZETARIS_REST_URL, ZETARIS_ORG_ID or ZETARIS_API_KEY is missing")
        try:
            response = self.session.post(
                self.base_url + "/sql-editor/sqls/run",
                headers={"Authorization": "Bearer " + self._key, "X-Org-ID": self.org_id,
                         "X-Request-ID": str(uuid.uuid4())},
                json={"queryId": str(uuid.uuid4()), "sql": sql, "source": "SqlEditor",
                      "limit": limit},
                timeout=self.timeout)
        except requests.RequestException as error:
            raise ZetarisError(f"cannot reach Zetaris: {type(error).__name__}",
                               unavailable=True) from error
        if response.status_code != 200:
            raise ZetarisError(f"HTTP {response.status_code}: {' '.join(response.text.split())[:300]}",
                               unavailable=response.status_code >= 500)
        body = response.json()
        if not isinstance(body, dict) or "headers" not in body:
            raise ZetarisError(f"unexpected reply: {response.text[:200]}")
        return QueryResult(sql, body["headers"], body.get("data") or [], "zetaris",
                           datetime.now(timezone.utc).isoformat())

    def query(self, sql, limit=DEFAULT_LIMIT, use_cache=True):
        """Run one SQL statement; return a QueryResult.

        use_cache=False is for statements that change the instance (CREATE...):
        they are never cached and never answered from the cache.
        """
        sql = _normalise(sql)
        if self.sample and use_cache:
            cached = self._read_cache(sql, limit, "cache")
            if cached is None:
                raise ZetarisError(f"SAMPLE_MODE: no cached result for: {sql[:120]}")
            return cached
        try:
            result = self._call(sql, limit)
        except ZetarisError as error:
            cached = (self._read_cache(sql, limit, "cache-fallback")
                      if use_cache and error.unavailable else None)
            if cached is None:
                raise
            return cached
        if use_cache:
            self._write_cache(result, limit)
        return result


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    result = ZetarisClient().query(argv[1])
    print(json.dumps({"origin": result.origin, "columns": result.columns,
                      "rows": result.rows[:20], "total": len(result.rows)},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
