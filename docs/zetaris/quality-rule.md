# Data-quality rule: every table Steward reads is read back and compared with its source file

**Rule.** After the registration, for every table Steward reads (`domain.yaml: zetaris_tables`, and the USL tables when `ZETARIS_USE_USL=true`), `SELECT COUNT(*)` through the same SQL door must equal the number of rows of the CSV the table was loaded from (sources 1 and 3) or be greater than zero for a live view (source 2, the finance API; the USL `department` view). A gap is a failed registration, printed table by table, exit code 1: never a silent default.

**Where it lives.** `app/adapters/verify_sources.py` (the rule), `scripts/zetaris/run_steward_sql.py` (runs it after the statements; `--verify-only` repeats it alone), `tests/test_verify_sources.py` (the rule itself is tested offline: a short table and a missing table are findings, not crashes).

**Executed on 27 October 20:50 Paris on the SQLite copy of the tables** (`SampleData`, the same `run_sql` door Steward uses in `SAMPLE_MODE`):

```
ok   brikk.members    rows    13 expected    13
ok   brikk.trust      rows     4 expected     4
ok   brikk.topics     rows    14 expected    14
ok   brikk.rules      rows    12 expected    12
ok   brikk.project    rows     6 expected     6
ok   brikk.profiles   rows    13 expected    13
ok   brikk.finance    rows     7 expected     7
ok   brikk.procedures rows     5 expected     5
ok   brikk.tasks      rows     7 expected     7
9/9 tables match their CSV
```

**On Zetaris: `NOT RUN` yet** (`python scripts/zetaris/run_steward_sql.py --verify-only` once the registration has run on a live instance). The second half of the rule is already enforced at read time: every Zetaris read has a 45 s timeout and three retries (`app/adapters/zetaris.py`), a failed read is an error on the trace, and the USL activation uses `COALESCE` on NOT NULL columns so that a null key never breaks a join (`register_steward.sql`).

A third guard belongs to the data itself: `topics.budget_limit_eur` and `finance.budget_eur` are the two figures a wrong value would turn into a wrong verdict (S05 escalation, budget signals). The read-back check does not validate values; today only the `warnings` field that contexts carry when the finance source is unavailable stands in for it. A `CHECK (budget_eur > 0)` on the Postgres table and a count of topics whose `budget_limit_eur` is empty would be the next two rules (not implemented).
