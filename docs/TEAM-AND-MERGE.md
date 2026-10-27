# Team OSEF: who built what, and how the two codebases merged

Two codebases grew in parallel during the event and were merged on 27 October 2026 into this repository.

| | Steward (Ryan Dalier-Dulys, with Claude) | Atlas (Adam Semlali, Alexandre Bouchet) |
| --- | --- | --- |
| Repository | this one | [abouchet109-del/Hackathon-GenAI-public](https://github.com/abouchet109-del/Hackathon-GenAI-public) |
| Focus | What becomes the company's shared truth, and what each person's AI receives | Keeping a project coordinated: progress per member, conflicts, meetings, manager updates |
| Built | Harness (guard, Zetaris research, H-MEM recall, decider/critic), 7 verdicts with role x domain trust and clarification before escalation, role-and-task context, MCP server, CEO console, H-MEM service with supersedes, Zetaris registration over 3 sources + USL, evaluation on 34 cases, video kit | Use case and architecture (bricks 1, 2, 4, 5; decisions D1 to D13), decision register, per-member progress classification, alert inboxes, Meterless Runtime provider tested against a fake runtime, live checks of Zetaris, Nightshift and Nemotron on their machine, H-MEM conformance |

## What the merged version takes from each side

- **From Steward (the base):** the arbitration pipeline, the company memory in H-MEM, the role-aware context, the 16 MCP tools, the console, the Zetaris sources, the evaluation.
- **From Atlas, ported as is and credited** (`app/coordination/`, from commit `961f320`, with 23 of their tests in `tests/coordination/`):
  - `decisions.py`: which decision is in force, and conflicts between applicable decisions;
  - `progress.py`: each task classified as ok, late or obsolete, and meetings recommended when a decision makes several people's work obsolete or a late task blocks someone else;
  - `alerts.py`: one inbox per person, each alert returned once (an MCP server cannot push to an AI, so alerts are pulled).
- **New glue** (`app/coordination/bridge.py`): the decisions in force are read from H-MEM, so there is one source of truth; Brikk's tasks come from Zetaris (table `tasks`); progress reports come from each person's AI (`report_progress`). A stored or replaced decision alerts the people whose tasks or reports depend on it; late work, obsolete work and coordination meetings appear in the CEO's weak signals.
- **New MCP tools:** `my_tasks`, `report_progress`, `my_alerts`.
- **Everything else of Atlas, kept whole in `atlas/`** (their `agent/` package with the imports rewritten, history preserved, their tests in `tests/`): the common model call with the Nemotron receipt (`structured.py`, `llm.py`), the versioned project state (`state.py`) and its World Model store (`world_model.py`, `services/world_model/`), their H-MEM client and service (`hmem.py`, `services/hmem/`, `ATLAS_HMEM_URL`), the Atlas corpus loaders (`sources.py`, `zetaris.py` with its committed cache), and the agents of the evening of 27 October: `extractor.py`, `updater.py`, `controller.py`, `writer.py`, `manager.py`, the `orchestrator.py` with `POST /run` on port 8080 (`python -m atlas.api`), versioned prompts in `atlas/prompts/`, and the replay cache of their real Nemotron runs (`data/cache/llm/`). Their documents are in `docs/atlas/` (README, PLAN, STATUS, JOURNAL, architecture); `docs/DECISIONS.md` keeps their numbering (D1-D17) and continues it (D24-D36). Two wrappers of the same Meterless reference (`hmem-service/` for Steward, `services/hmem/` for Atlas) coexist on different ports and are a post-event unification item.
- **Their lesson on Nightshift**, applied: the runtime exposes routing modes (`meterless/fast`, `meterless/deep`, ...), not model ids. The lanes point at those modes and the model actually served is read back from every answer and checked against Nemotron (`scripts/configure_nightshift.py`).

## Running it live

The sponsor stack (Zetaris with its API key, Nightshift, Nemotron) was verified on Adam and Alexandre's Windows machine with the Atlas code (live Zetaris registration of the Atlas corpus, real Nemotron runs cached in `data/cache/llm/`). Steward's own registration and demo on the real stack had not run at the time of writing (README, Known limits). From a checkout of this repository there:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\setup.ps1 -AtlasDir D:\path\to\Hackathon-GenAI-public
.venv\Scripts\python scripts\zetaris\run_steward_sql.py
.venv\Scripts\python run.py steward-demo
$env:DOMAIN="project_memory"; .venv\Scripts\python run.py ablation --repeats 3
.venv\Scripts\python run.py serve      # console: http://localhost:8000/console
```

On a Mac: `bash scripts/install-zetaris.sh`, then `bash scripts/after-zetaris.sh`.
