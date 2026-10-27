# Inventory, 27 October 2026, 18:15 (Paris)

What exists before the unification, where, whether it runs (commands actually run, real results), who wrote it, and how it maps to the v2 specification (`08-specifications-steward-v2.md`, the authoritative spec).

## Source A: Steward (Ryan Dalier-Dulys with Claude), `~/open-agent-hack` and this branch

Git: one commit on the Mac (`3cf8291`, 27/10 00:4x); six commits in Claude's working copy (`cf88874` to `a1fe471`, 27/10 13:50 to 15:00), authored "Ryan Dalier-Dulys", co-authored by Claude. Python 3 (FastAPI, openai client, pydantic, mcp), TypeScript for the H-MEM service.

| Module | What it does | Runs? (command, real result on 27/10 18:20) | Tests | Spec v2 |
| --- | --- | --- | --- | --- |
| `app/agents.py`, `app/pipeline.py`, `app/guard.py` | Harness: intake + guard, Researcher (SQL), MemoryKeeper (H-MEM), rule matching, Decider <-> Critic (hard checks + 9-point rubric, pass at 7, 2 revisions then escalate), Reporter; domain packs plug in through hooks | `python run.py steward-demo`: 8-step scenario completes offline | `tests/test_harness.py` (5, admin pack) | Sub-agents 2, 3, 4 |
| `app/llm.py` | All model calls through Nightshift (OpenAI-compatible, `meterless-app`/`meterless-scope` headers), three lanes, replay cache, served model recorded per call | Never called live from this code (no runtime token on the Mac yet) | covered by harness tests in replay mode | Nightshift, Nemotron lanes |
| `app/adapters/zetaris.py` | REST client (`POST /sql-editor/sqls/run`, 3 retries) or SQLite copy of the CSVs in `SAMPLE_MODE` | SAMPLE_MODE only; live Zetaris never reached from this code | via harness tests | Zetaris |
| `app/adapters/memory.py`, `hmem-service/server.ts` | H-MEM client; Node service around the Meterless reference with `supersedes`/`supersededBy`, `/list` by tag, per-space persistence; local fallback with the same semantics | `cd hmem-service && npm run conformance`: **13/13 checks passed** (18:20) | `tests/test_steward.py` (supersede history) | H-MEM |
| `domains/project_memory/` | Brikk pack: 12 members + intern, trust role x domain, 14 topics with keywords, rules S01-S12, procedures, finance, tasks; `logic.py` (verdicts, hard checks, apply, resolve, clarify); `context.py` (watchlist, extract, context composer, what's new, weak signals, onboarding) | yes, see demo | `tests/test_steward.py` (11) | Sub-agents 1, 5, 6, 7; data |
| `app/steward.py` | The Steward service: remember, observe, my_context, whats_new, clarifications, answer_clarification, escalations/resolve, signals, onboarding, progress, alerts; cross-process write lock (fcntl / msvcrt) | yes | idem | all tools |
| `app/mcp_server.py` | MCP server `steward` (stdio; named `osef-steward` at inventory time): 15 tools, resource `osef://watchlist`, prompt `role_procedures`; provenance from `clientInfo` + `OSEF_MEMBER`/`OSEF_AI_TOOL` env | `python scripts/mcp_smoke.py`: **PASS** (real stdio client, 18:20) | smoke | 12 of the 13 spec tools present; `clarifications` missing as a tool (it is folded into `whats_new`); 3 extra: `my_tasks`, `report_progress`, `my_alerts` |
| `app/server.py`, `app/console.py`, `app/static/` | FastAPI: `POST /run`, `/learn`, `/health`, `/finance/budgets` (REST source for Zetaris), console `/console` (shared truth, CEO queue, clarifications, context preview, onboarding, simulate an AI) with the Steward brand kit (`tokens.css`, `components.css`, fonts, icons) | `python run.py serve`: console renders (screenshots taken 27/10) | none automated | Console (topic history is inside the "why" dialog; traces not shown as a screen) |
| `app/coordination/` | Ported from Atlas on 27/10 14:3x: `decisions.py`, `progress.py`, `alerts.py` + `bridge.py` (decisions in force read from H-MEM, tasks from Zetaris, alerts on store/supersede) | yes | `tests/coordination/` (23, theirs) + `tests/test_coordination_bridge.py` (4) | beyond spec (progress and alerts) |
| `app/evaluation.py` | Ablation: profiles full / no_memory / rules_only / no_critic / model_only | `DOMAIN=project_memory python run.py ablation` (offline, 26/10): rules_only 56 %, 3 unsafe; full 100 %, 0 unsafe, escalation 9 % | — | evidence |
| `scripts/zetaris/register_steward.sql`, `run_steward_sql.py` | Postgres `brikk` datasource (JDBC), REST table + SchemaStore view for finance, FILESTORE on MinIO for procedures, USL `brikk_usl` (4 tables), cross-source query; 19 statements, one per request | `--dry-run` only. **Never run against a live Zetaris.** JDBC and MinIO are not in the official recipes | — | Zetaris 3 sources + USL |
| `scripts/install-zetaris.sh`, `after-zetaris.sh`, `setup-steward-mac.sh`, `configure_nightshift.py`, `set-secret.sh`, `windows/setup.ps1` | Install and wiring scripts (Mac and Windows); Nightshift lanes with Nemotron check | Mac: Zetaris images pulled and started on 27/10 00:5x, UI not reachable at 14:19; keys never entered. Windows script untested | — | ops |
| `scripts/video/*`, `docs/submission/*` | Terminal and console recorders, title cards, assembly; `steward-demo.mp4` draft 3:26 (offline run) | yes | — | video |
| `tests/` | 43 tests | `python -m pytest -q`: **43 passed** (18:20) | — | — |
| `docs/STEWARD.md`, `docs/TEAM-AND-MERGE.md`, `docs/mcp/*.json`, `metadata.json`, `LICENSE` (all rights reserved), `NOTICE` | docs and submission files | — | — | deliverables |

Not in the spec but present: the `admin` domain pack (second pack on the same harness, 30 cases, 5 tests).

## Source B: Atlas (Adam Semlali, Alexandre Bouchet), `github.com/abouchet109-del/Hackathon-GenAI-public`

Git: 27 commits on `main`, 26/10 23:21 to 27/10 18:09, authors `belufr` (22) and `abouchet109-del` (5). Which of Adam or Alexandre is `belufr`: UNKNOWN. Python 3 (pydantic, requests, unittest). Built with Claude sessions following `CLAUDE.md` and `docs/PLAN.md`; their own plan: code freeze 22:30, submission 00:15.

| Module | What it does | Runs? | Tests | Spec v2 |
| --- | --- | --- | --- | --- |
| `agent/decisions.py` | Decision register: applicable decisions, conflicts, decision in force per (subject, attribute) | yes | 6 | "what is in force" (the arbitration side is Steward's) |
| `agent/progress.py` | Per-member task classification (ok, late, obsolete), meetings when a decision obsoletes several people or a late task blocks another; Task gained a start date, Milestone reads its date from the decision in force | yes | 11 | beyond spec: progress per member (Steward reuses it) |
| `agent/alerts.py` | Alert inboxes per member, pulled once through MCP | yes | 6 | beyond spec (Steward reuses it) |
| `agent/llm.py` | Meterless Runtime provider: token from `.settings.json` / `METERLESS_STATE_DIR/proxy-token`, auto-detect on ports 8088/8090/8787/11434, connect links, `status/detect/models/chat` CLI | verified live on their PC (Nightshift online, `meterless/auto` answers) | 13 (fake runtime) | Nightshift |
| `agent/structured.py` | Common LLM call: JSON validated by a pydantic schema, one retry with the error, 90 s timeout, routes Nightshift then `MODEL_*` then cache (`data/cache/llm/`, the only route in SAMPLE_MODE), JSONL trace `logs/llm-trace.jsonl`; reads the served model from Nightshift's receipt `meterless.routed_model`; **default model `nvidia/nemotron-3.5-lightning-30b-a3b`, verified live on 27/10 17:58** (`nemotron-3-ultra-550b-a55b` also answers; `nemotron-3-super-120b` returns a 404 from NVIDIA) | live on their PC | 8 (fake runtime) | Nemotron pinned, model in trace |
| `agent/zetaris.py` | Zetaris client: SQL over REST, 60 s timeout, cache per query committed in `data/cache/zetaris/` for SAMPLE_MODE, fallback to cache on 5xx/timeout only | live on their PC (9 sources read back identical to the corpus) | 7 (fake server) | Zetaris |
| `scripts/register_zetaris.py` | Registers 9 REST tables in a Lightning database `ATLAS`, each on a jsDelivr URL pinned on a commit of the public repo; idempotent, `--verify-only`, `--repin` | **live, 27/10 17:49** | — | a proven way to register a file source without S3 |
| `agent/contracts.py`, `agent/sources.py`, `agent/state.py`, `agent/hmem.py` | Pydantic contracts between bricks; corpus loaders; versioned project state behind a `StateStore` interface; H-MEM client interface with a tested local fallback (no TypeScript service yet) | yes (offline) | contracts 5, corpus 9, state 7, hmem 9 | partial overlap with Steward's harness and H-MEM service |
| `data/sample/*.json`, `data/expected/`, `data/scenarios/`, `evaluation/expected.py` | Synthetic Atlas corpus (project "Atlas", 5 people, past project "Orion"), expected results S1-S9 | yes | corpus tests | a second demo company; Steward's is Brikk |
| `docs/architecture.md`, `docs/PLAN.md`, `docs/DECISIONS.md` (D1-D14), `docs/STATUS.md`, `docs/JOURNAL.md`, `docs/use-case-atlas.md`, `docs/architecture-notes/*.jpg` | Use case, bricks 1, 2, 4, 5, 7, three layers (Zetaris / World Model / H-MEM), decisions, plan with estimates | — | — | vision: prosecutor/judge, CEO/manager agent, weak signals, meetings |
| `docs/hackathon/`, `docs/strategie/` | Copies of the rules and the jury grid, internal strategy | — | — | not for the product |
| `smoke_test.py`, `scripts/hmem-conformance.ps1` | Stack check (Zetaris REST with key, Nightshift, Nemotron); H-MEM conformance on Windows: 13/13 | live on their PC | — | ops |
| `tests/` | 92 tests + 48 subtests | `SAMPLE_MODE=true python -m pytest -q`: **92 passed, 48 subtests passed** (run here, 18:20) | — | — |

Not built on their side (their STATUS/PLAN): the LLM bricks (analyst, controller), the orchestrator, `POST /run`, the MCP server, the manager page, the video.

## Overlaps and contradictions, with the resolution

| Topic | Steward | Atlas | Resolution (criterion: the v2 spec and the jury grid) |
| --- | --- | --- | --- |
| Product and demo company | Steward, Brikk (12 people + intern) | Atlas project, 5 people, past project Orion | **Steward and Brikk** (spec v2, decided 26/10). The Atlas corpus stays in the repo as the team's data set and test fixtures; it is not the demo. Noted in DECISIONS D15. |
| Pipeline | Complete: guard, research, recall, arbiter, judge, clarify, apply, context | Contracts and state written; LLM bricks and orchestrator not started | Steward's pipeline is the runtime. |
| What is in force | H-MEM records with `supersedes`, trust = role x domain | Decision register with (subject, attribute) keys and conflicts | Both: H-MEM is the source; `app/coordination/bridge.py` maps records to the register so Atlas' progress and alerts work on it. |
| Progress per member, alerts, meetings | none before 27/10 | `progress.py`, `alerts.py` | Taken from Atlas, intact and credited; wired through `report_progress`, `my_tasks`, `my_alerts`. |
| Zetaris sources | Postgres (JDBC), REST finance, FILESTORE on MinIO; USL; never run live | REST tables on jsDelivr (pinned commit); run live | Keep Postgres + REST finance + USL; **replace the MinIO filestore by a jsDelivr REST table** (their proven recipe) for the procedures catalogue once the repo is public (cut 2 in the prompt otherwise). |
| Nightshift / Nemotron | lanes `meterless/*`, served model read from the answer, never run live | exact ids `nvidia/nemotron-3.5-lightning-30b-a3b` (fast) and `nvidia/nemotron-3-ultra-550b-a55b` (deep/judge), receipt `meterless.routed_model`, run live | Pin those ids by default in `.env.example` and `configure_nightshift.py`; read the receipt field in `app/llm.py`. |
| H-MEM | TypeScript service around the reference, conformance 13/13, `supersedes` | Python client interface + local fallback, no service | Keep the service (their D11 option (a)); their client stays in `atlas/` as reference. |
| Language per component | Python app, TS H-MEM | Python only | Keep (ADR-3). |
| Package layout | `app/`, `domains/`, `hmem-service/` | `agent/`, `data/`, `evaluation/` | Their package is kept whole as `atlas/` (history preserved by a git merge), their tests kept; Steward imports `atlas.decisions/progress/alerts` instead of its copies. |
| Docs | `docs/STEWARD.md`, `docs/TEAM-AND-MERGE.md` | `docs/architecture.md` (draft), `PLAN.md`, `DECISIONS.md`, ... | Theirs move to `docs/atlas/` (case-insensitive file systems would otherwise collide `architecture.md` with `ARCHITECTURE.md`); `docs/DECISIONS.md` stays at the root and continues their numbering. |
| Repository | `rdalierdulys-arch` (spec) | `abouchet109-del/Hackathon-GenAI-public` (their D5, public since 26/10) | The shared repository, branch `unify`, then `main` with Ryan's go (prompt of 27/10 18:12, the most recent source). |
| License | All rights reserved, Ryan | none in the repo | Recommendation sent to Ryan: joint copyright, all rights reserved, Apache-2.0 for Meterless code. Pending. |
| Schedule | T2 21:30 main submittable, T3 23:15 freeze | freeze 22:30, submit 00:15 | Ryan's milestones; the team must be told (message sent to Ryan 18:20). |

## Environment facts

- Ryan's Mac: Docker running; Zetaris images pulled and containers started on 27/10 00:5x (`install-zetaris.sh`), UI not reachable at 14:19 and at 18:12 (Docker probably stopped); no Zetaris API key, no Nightshift token in `.env`; Nightshift app installed and running at 00:00 (port 8088 answered). The Mac link to this session drops regularly.
- Teammates' Windows PC: Zetaris with key, Nightshift with Nemotron, H-MEM conformance: all verified by them (their STATUS, 27/10).
- This container: no Zetaris, no Nightshift; everything runs in `SAMPLE_MODE`; H-MEM service and conformance run locally; pushes to the shared repository are refused for this session (GitHub App not installed on `abouchet109-del`).
