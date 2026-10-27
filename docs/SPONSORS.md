# How each sponsor technology is used

The test of a load-bearing integration: remove it and Steward stops working (except in `SAMPLE_MODE`, which says so on every screen and trace).

## Zetaris (DATA)

One SQL door over three sources, read on every arbitration and every context:

| Source | Registered as | Read by |
| --- | --- | --- |
| Postgres `brikk` (org chart, trust weights role x domain, topics with owner and limits, rules, profiles, tasks) | `CREATE DATASOURCE brikk ... jdbc:postgresql://host.docker.internal:5434/brikk`, `REGISTER DATASOURCE TABLES` | `domains/project_memory/logic.py::research` (author, trust, topic owner, limit, rules), `context.py` (profiles, watchlist, tasks) |
| Finance REST API (`GET /finance/budgets`, served by Steward) | Lightning REST table + SchemaStore view `brikk_api.finance` (`LATERAL VIEW explode`) | `context.py::finance` (budget ratios in contexts and weak signals) |
| Company catalogue (role procedures), a JSON file on the public repository pinned on a commit | Lightning REST table + SchemaStore view `brikk_drive.procedures` | `context.py::procedures_for` (the `role_procedures` MCP prompt and every context) |
| Unified Semantic Layer `brikk_usl` (`department`, `member`, `topic`, `procedure`) | `COMPILE USL ... DDL`, `ACTIVATE USL TABLE ... AS SELECT` | the same reads when `ZETARIS_USE_USL=true` |

Scripts: `scripts/zetaris/register_steward.sql` (21 statements, one per request), `scripts/zetaris/run_steward_sql.py` (registers, then reads every table back and compares the counts with the CSVs: `app/adapters/verify_sources.py`, the quality rule), `scripts/zetaris/export_catalogue.py`; the team's `scripts/register_zetaris.py` registers the Atlas corpus the same way (REST tables pinned on a commit; the team ran it live on its own machine on 27/10, the only committed artefact of that run is the query cache in `data/cache/zetaris/`). Client: `app/adapters/zetaris.py` (REST, 3 retries, 45 s) and the SQLite copy for `SAMPLE_MODE`; `atlas/zetaris.py` (the team's client with a committed query cache).

Status on 27/10: the Atlas registration ran live on the team's machine; the Steward registration (`register_steward.sql`) is the same recipe for sources 2 and 3 plus a JDBC datasource for source 1 and the USL, and had not been run live at the time of writing (README, "Known limits").

## Meterless H-MEM (BUILD)

The company memory. `hmem-service/server.ts` wraps the reference engine (Apache-2.0, vendored unchanged by `setup.sh`; conformance suite 13/13 on `npm run conformance`, run of 27/10 committed as `logs/samples/hmem-conformance.txt`) and adds what Steward needs: `supersedes` chains (a replaced decision is kept, marked `supersededBy`, down-ranked), `/list` by tag, one persisted space per company. Every record carries `source` (who, via which AI), `confidence` (= the author's trust weight role x domain), tags (`topic:`, `kind:`, `author:`, `department:`, `ai:`, `trust:`, `policy`). CEO policies are corrections stored as tagged records and recalled on the next arbitration. The per-person "seen up to" cursor for `whats_new`, the CEO queue and the questionnaire answers are local state files next to it (`data/steward-*`, per company space), not H-MEM records. Client: `app/adapters/memory.py` (with a local fallback that has the same semantics, used only when no real stack is configured). The team's `atlas/hmem.py` is a second, tested client interface.

## Meterless Nightshift (POWER)

The only model provider. `app/llm.py` calls `http://127.0.0.1:8088/v1` with `meterless-app` and `meterless-scope: user`, on three lanes: fast (extractor), deep (arbiter), judge (critic). The model that actually answered is read from Nightshift's receipt (`meterless.routed_model`, `receipt_id`) and written on every trace line. `scripts/configure_nightshift.py` lists the lanes, writes them to `.env` and makes one test call; `atlas/llm.py` and `atlas/structured.py` are the team's provider and schema-validated call, tested against a fake runtime (21 tests); the team made live calls through them on 27/10 on its own machine (no transcript committed; the receipt format they return is the one `app/llm.py::served_model` reads).

## NVIDIA Nemotron

Pinned by exact id on the three lanes: `nvidia/nemotron-3.5-lightning-30b-a3b` (fast) and `nvidia/nemotron-3-ultra-550b-a55b` (deep, judge), the ids the team verified through Nightshift on 27/10 on its own machine (`nvidia/nemotron-3-super-120b` returned a 404 from NVIDIA in that session; no transcript committed, see `.env.example`). The NVIDIA key lives only in Nightshift.

## Cursor

The development environment of the team, and one of the two MCP clients in the demo (`docs/mcp/cursor-mcp.json`, Sami Haddad, CTO). Claude Desktop is the other (`docs/mcp/claude_desktop_config.json`, Claire Morel, CEO).
