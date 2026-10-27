"""DATA layer: the agent reads rules, senders and the owner's profile through Zetaris.

ZetarisClient sends one SQL statement at a time to the Zetaris REST API
(POST /sql-editor/sqls/run). SampleData runs the very same SQL on SQLite loaded
from domains/<domain>/data/*.csv, so SAMPLE_MODE exercises the same queries
without Zetaris. Both return rows as dicts keyed by the selected columns.
"""
from __future__ import annotations

import csv
import sqlite3
import time
import uuid
from pathlib import Path

import requests

from ..config import SETTINGS


class DataError(RuntimeError):
    pass


class ZetarisClient:
    name = "zetaris"

    def __init__(self, settings=SETTINGS):
        self.s = settings

    def run_sql(self, sql: str, columns: list[str]) -> list[dict]:
        url = self.s.zetaris_rest_url.rstrip("/") + "/sql-editor/sqls/run"
        last = None
        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    headers={
                        "Authorization": "Bearer " + self.s.zetaris_api_key,
                        "X-Org-ID": self.s.zetaris_org_id,
                        "X-Request-ID": str(uuid.uuid4()),
                    },
                    json={"queryId": str(uuid.uuid4()), "sql": sql, "source": "SqlEditor", "limit": 1000},
                    timeout=self.s.zetaris_timeout,
                )
                resp.raise_for_status()
                payload = resp.json()
                rows = payload.get("data") or []
                return [dict(zip(columns, row)) if isinstance(row, (list, tuple)) else row for row in rows]
            except (requests.RequestException, ValueError) as error:
                last = error
                time.sleep(1.5 * (attempt + 1))
        raise DataError(f"Zetaris did not answer after 3 attempts: {last}")


class SampleData:
    """Same SQL, run on SQLite. Tables live in an attached database named like the Zetaris schema."""
    name = "sample-sqlite"

    def __init__(self, data_dir: Path, schema: str):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.execute(f"ATTACH DATABASE ':memory:' AS {schema}")
        for csv_path in sorted(data_dir.glob("*.csv")):
            with csv_path.open(encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                cols = ", ".join(f'"{c}" TEXT' for c in header)
                table = f"{schema}.{csv_path.stem}"
                self.conn.execute(f"CREATE TABLE {table} ({cols})")
                marks = ", ".join("?" for _ in header)
                self.conn.executemany(f"INSERT INTO {table} VALUES ({marks})", list(reader))
        self.conn.commit()

    def run_sql(self, sql: str, columns: list[str]) -> list[dict]:
        cur = self.conn.execute(sql)
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def make_data_source(settings=SETTINGS):
    """Zetaris when configured, else SQLite sample data (logged by the caller)."""
    if settings.zetaris_ready:
        return ZetarisClient(settings)
    return SampleData(settings.domain_dir / "data", settings.data_schema)


def quote(value: str) -> str:
    """Minimal SQL string literal escaping for values that come from parsed emails."""
    return "'" + str(value).replace("'", "''") + "'"
