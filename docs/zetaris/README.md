# Zetaris in Steward: the use case, the three sources, the Unified Semantic Layer

This folder answers the Zetaris scoring methodology published on 26 October (build a USL over at least three sources, 2–3 queries per source, the USL's DDL and 2–3 queries proving it is active, one executed data-quality rule, three short reflection documents).

**Status at the time of writing (27 October, 20:50 Paris): honest labels on every item.** The DDL and every query below are the ones Steward's code runs. Each query was executed on the SQLite copy of the same tables (`SAMPLE_MODE`, same SQL, same column names) and its real output is shown. **None of them has been executed on a live Zetaris from this code yet** (`NOT RUN ON ZETARIS`): the registration script is written and verified for syntax (`--dry-run`), the team ran the same recipe live for the Atlas corpus (`scripts/register_zetaris.py`, 27/10), and the Brikk registration is the next step on a machine where Zetaris answers (`scripts/zetaris/run_steward_sql.py`, then `--verify-only`). When that run happens, this file is updated with the live outputs.

## 1a. The use case and the sources

Steward arbitrates what each person's AI proposes to the company's shared truth. Every arbitration needs governance data that no AI should carry in its prompt: who the author is and how much weight their role gives them on this topic, who owns the topic and its spending limit, which rules apply, how the department's budget stands, and which formal procedure the person's role follows. Those facts live in three systems of a real small company; Zetaris makes them one SQL door.

| Source | What it holds | System of record | Registered as |
| --- | --- | --- | --- |
| 1. `brikk` (Postgres) | `members` (org chart, AI tool, level), `trust` (weights role x domain), `topics` (owner, single-answer flag, limit, keywords), `rules` (S01–S12), `profiles` (onboarding answers), `project`, `tasks` | the HR/governance database | `CREATE DATASOURCE brikk ... jdbc:postgresql://host.docker.internal:5434/brikk` + `REGISTER DATASOURCE TABLES` |
| 2. Finance API (REST) | budgets and commitments per department, served live by `GET /finance/budgets` | the finance tool | `CREATE LIGHTNING REST TABLE BRIKK_FINANCE_REST.budgets_raw` + SchemaStore view `brikk_api.finance` (`LATERAL VIEW explode`) |
| 3. Company catalogue (REST, a JSON file on a public URL pinned on a commit) | the role procedures (P01–P05: when to use, steps) | the company drive | `CREATE LIGHTNING REST TABLE BRIKK_CATALOGUE.procedures_raw` + SchemaStore view `brikk_drive.procedures` |
| USL `brikk_usl` | `member`, `topic`, `procedure`, `department` (finance per department) | — | `COMPILE USL brikk_usl ... DDL`, `ACTIVATE USL TABLE ... AS SELECT` |

Who reads what, in the code: `domains/project_memory/logic.py::research` (sources 1 on every arbitration), `domains/project_memory/context.py` (profiles, watchlist, procedures, finance on every context and for the CEO's weak signals), `app/steward.py::escalations` (topic limits), `app/coordination/bridge.py` (tasks). `ZETARIS_USE_USL=true` switches the same reads to the USL tables (`domain.yaml: zetaris_usl_tables`).

## 1b, 1c. DDL, queries, quality rule

- DDL: [`../../scripts/zetaris/register_steward.sql`](../../scripts/zetaris/register_steward.sql) (21 statements, one per request; the runner is `scripts/zetaris/run_steward_sql.py`). An S3/MinIO variant of source 3: `register_steward_minio.sql`.
- Queries with their outputs: [`queries.md`](queries.md).
- Data-quality rule, executed: [`quality-rule.md`](quality-rule.md).

## 2. Reflections

[`reflections.md`](reflections.md): time saved versus hand-coding, where a USL would and would not help in our own work, how to make the USL stronger (written as a PM).
