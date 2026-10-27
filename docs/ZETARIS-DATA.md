# Getting our data into Zetaris

Zetaris cannot read a file sitting on the laptop: file tables need S3-compatible, Azure, GCS or HDFS storage. Three ways to serve our synthetic data, best first.

| Route | How | Status |
| --- | --- | --- |
| 1. Postgres datasource (chosen) | `docker compose up osef-db` loads the CSVs into Postgres; `CREATE DATASOURCE ... jdbcurl "jdbc:postgresql://host.docker.internal:5433/osef"` then `REGISTER DATASOURCE TABLES` | Syntax from the Zetaris SQL command reference (section 4); not yet run live |
| 2. MinIO (S3-compatible) | Run a MinIO container, upload the CSVs, `CREATE LIGHTNING FILESTORE TABLE ... FORMAT CSV OPTIONS (path "s3a://...", s3Endpoint "...", useS3PathStyleAccess "true", ...)` | Pattern proven by Zetaris' Parquet/CSV recipes on public S3; see kbase "How to connect to MinIO S3" |
| 3. REST table on a local API | Serve the CSVs as JSON from a tiny HTTP server; `CREATE LIGHTNING REST TABLE` + `CREATE SCHEMASTORE VIEW` | Pattern proven by the PokéAPI recipe |

## Route 1, step by step

1. `docker compose up -d osef-db` (Postgres on host port 5433, data from `domains/admin/data/*.csv`).
2. In the Zetaris SQL Editor, run `scripts/zetaris/register_sources.sql` one statement at a time.
3. Check: `SELECT rule_id, decision FROM osef.rules;` returns 13 rows.
4. In `.env`: `DATA_SCHEMA=osef`, Zetaris API key set, `SAMPLE_MODE=false`.
5. `python run.py run --input input_examples/example_1.json`: the trace shows `queried_zetaris` with `source=zetaris`.

If `osef.rules` is not the right qualified name after registration, run `SHOW TABLES` style commands from the SQL reference and set `DATA_SCHEMA` accordingly; the agents prefix every table with it.

## Why this is a real role for Zetaris

The Researcher never sees a CSV. It asks Zetaris three questions per item (is the sender verified, what rules apply to this item type, what is the owner's auto-pay limit) and gets governed answers. Adding a second source (a bank export, the school's calendar API) is one more registration in Zetaris and one more query, with no new connector in the app.
