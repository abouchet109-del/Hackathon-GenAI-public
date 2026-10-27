"""Read-back check of the Brikk sources after a Zetaris registration (the quality rule of ARCHITECTURE.md §4).

For every table Steward reads (`domain.yaml: zetaris_tables`, and `zetaris_usl_tables` when the USL is active),
run `SELECT COUNT(*)` through the same `run_sql` door and compare with the CSV the table was loaded from:
a count that differs is a failed registration, never a silent default. The check runs on any data source that
answers `run_sql(sql, columns)`: Zetaris (scripts/zetaris/run_steward_sql.py --verify) or the SQLite sample copy
(the tests), so the comparison itself is tested offline.
"""
from __future__ import annotations

import csv
from pathlib import Path

# the Postgres tables of source 1 and the two views (sources 2 and 3) are loaded from these CSVs
CSV_OF = {"members": "members.csv", "trust": "trust.csv", "topics": "topics.csv", "rules": "rules.csv",
          "project": "project.csv", "profiles": "profiles.csv", "tasks": "tasks.csv", "finance": "finance.csv",
          "procedures": "procedures.csv"}
# USL tables that are one-to-one with a CSV; `department` joins finance and members and is checked for non-emptiness
USL_CSV_OF = {"member": "members.csv", "topic": "topics.csv", "procedure": "procedures.csv"}


def csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def count(data, table: str) -> int:
    rows = data.run_sql(f"SELECT COUNT(*) AS n FROM {table}", ["n"])
    return int(rows[0]["n"]) if rows else 0


def verify(data, data_dir: Path, tables: dict[str, str], usl_tables: dict[str, str] | None = None) -> list[dict]:
    """One line per table: {table, expected, found, ok}. `expected` is None when the table has no CSV of its own."""
    out = []
    for key, table in tables.items():
        expected = csv_rows(data_dir / CSV_OF[key]) if key in CSV_OF else None
        try:
            found = count(data, table)
        except Exception as error:  # noqa: BLE001 - the error is the finding
            out.append({"table": table, "expected": expected, "found": None, "ok": False, "error": str(error)[:200]})
            continue
        out.append({"table": table, "expected": expected, "found": found,
                    "ok": (found == expected) if expected is not None else found > 0})
    for key, table in (usl_tables or {}).items():
        name = table.rsplit(".", 1)[-1]
        expected = csv_rows(data_dir / USL_CSV_OF[name]) if name in USL_CSV_OF else None
        try:
            found = count(data, table)
        except Exception as error:  # noqa: BLE001
            out.append({"table": table, "expected": expected, "found": None, "ok": False, "error": str(error)[:200]})
            continue
        out.append({"table": table, "expected": expected, "found": found,
                    "ok": (found == expected) if expected is not None else found > 0})
    return out


def report(lines: list[dict]) -> str:
    width = max(len(l["table"]) for l in lines) if lines else 10
    rows = []
    for l in lines:
        exp = "any" if l["expected"] is None else str(l["expected"])
        found = "error" if l["found"] is None else str(l["found"])
        rows.append(f"{'ok  ' if l['ok'] else 'FAIL'} {l['table']:<{width}} rows {found:>5} expected {exp:>5}"
                    + (f"  {l['error']}" if l.get("error") else ""))
    bad = sum(1 for l in lines if not l["ok"])
    rows.append(f"{len(lines) - bad}/{len(lines)} tables match their CSV" if not bad else f"{bad} table(s) differ from their CSV")
    return "\n".join(rows)
