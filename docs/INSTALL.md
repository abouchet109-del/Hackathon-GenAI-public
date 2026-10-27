# Run Steward on another machine

Windows, macOS or Linux. Three levels: offline in five minutes (what the jury runs), an AI plugged in through MCP, and the real stack (Zetaris, Nightshift with Nemotron, Meterless H-MEM). Nothing here needs an account or a key until level 3.

## 0. What you need

| | Level 1, offline | Level 2, an AI through MCP | Level 3, the real stack |
| --- | --- | --- | --- |
| Python **3.12 or newer** (`python --version`) | yes | yes | yes |
| Git (or the ZIP download) | yes | yes | yes |
| Claude Desktop or Cursor | | yes | yes |
| Node.js **20 or newer** (H-MEM) | | | yes |
| Docker Desktop (Postgres source, optional MinIO) | | | yes |
| Zetaris (local) and Meterless Nightshift with the NVIDIA key | | | yes |

The commands below are tested on Ubuntu and Windows by the repository's CI (`.github/workflows/tests.yml`, Python 3.12, runs 40568677619 and 40584948164) and on macOS during the event.

## 1. Get the code

Either:

```bash
git clone https://github.com/abouchet109-del/Hackathon-GenAI-public
cd Hackathon-GenAI-public
```

or, without Git: on the repository page, **Code → Download ZIP**, unzip it, and open a terminal in the unzipped folder (`Hackathon-GenAI-public-main`). Everything the offline level needs is in the archive: sample data, recorded traces, tests. Only level 3 downloads something else (the Meterless H-MEM reference engine, fetched by `hmem-service/setup.sh`).

## 1b. The team's Windows PC, where Zetaris and Nightshift already run (the demo machine)

Adam's PC already has the clone of this repository (the former Atlas checkout), Zetaris and Nightshift running with the NVIDIA key, Node.js, Docker Desktop, and a `.env` with `ZETARIS_API_KEY`, `METERLESS_RUNTIME_TOKEN` and `METERLESS_STATE_DIR`. Since 27 October 22:13 `main` holds the unified product, so the clone only needs a pull; `.env`, `.settings.json` and `external/meterless` are untracked and stay in place. In PowerShell, from the clone:

```powershell
git status                                   # must be clean; otherwise: git stash
git pull --ff-only                           # agent/ becomes atlas/, Steward arrives in app/, domains/, hmem-service/
powershell -ExecutionPolicy Bypass -File scripts\windows\setup.ps1 -AtlasDir (Get-Location).Path
```

`setup.ps1` (logged in `logs\setup-windows.log`): installs the Python dependencies in `.venv`, keeps the Zetaris and Nightshift values of the existing `.env` and reads the runtime token from `.settings.json` if it is there (nothing is printed), sets `SAMPLE_MODE=false` and `HMEM_URL=http://127.0.0.1:8787`, vendors the Meterless H-MEM reference from `external\meterless` (no download when it is already there), runs its conformance suite (13 checks) and starts Steward's H-MEM service on :8787, starts the Brikk Postgres source on 127.0.0.1:5434 with Docker, pins the Nemotron lanes from what Nightshift serves (`configure_nightshift.py`, one real call), then runs the tests and the MCP smoke test. It was written during the event and not run on that PC yet: if a step fails, the log says which, and every step is one of the commands below, which can be run by hand.

Then, in two PowerShell windows:

```powershell
# window 1: the finance API (source 2 of Zetaris) and the console
.venv\Scripts\python run.py serve

# window 2
.venv\Scripts\python scripts\zetaris\run_steward_sql.py         # 21 statements: Postgres brikk, finance REST table, catalogue, USL; then reads every table back
.venv\Scripts\python smoke_test.py                                 # Zetaris, Nightshift, Nemotron, H-MEM: one line each
.venv\Scripts\python run.py steward-demo                           # the scenario with Nemotron on every trace line (logs\trace-*.jsonl, field "model")
$env:DOMAIN = "project_memory"; .venv\Scripts\python run.py ablation --profiles no_memory,full   # the real figures (logs\ablation-*.md)
```

What the registration touches on the shared Zetaris: it creates objects named `brikk`, `BRIKK_FINANCE_REST`, `BRIKK_CATALOGUE`, `brikk_api`, `brikk_drive` and the USL `brikk_usl`; it drops nothing and does not touch the team's `ATLAS` objects. Zetaris runs in Docker, so the SQL reaches the PC through `host.docker.internal` (Postgres on 5434, the finance API on 8000): keep window 1 open while it runs. Source 3 is served by jsDelivr from this repository, pinned on the last commit that touched `domains/project_memory/data/procedures.json` (checked: it resolves).

For the video on that PC: `$env:STEWARD_SPACE = "video"; $env:STEWARD_SEED_POLICIES = "true"; .venv\Scripts\python run.py serve` then `http://127.0.0.1:8000/console`; the MCP side is Cursor (`.cursor\mcp.json`, level 2) and Claude Desktop if it is installed; otherwise two Cursor projects with two configs (the CEO and the CTO), or the console's **Simulate an AI** for the second person.

## 2. Level 1: run it offline (five minutes)

Offline means: the same agents and the same SQL, on SQLite copies of the governance data, a local memory with the same `supersedes` semantics, and the deterministic path instead of the model. The console header, `/health` and every trace say so (`sample-sqlite`, `local-fallback`, `offline`). With no `.env` and no services, Steward takes that path by itself; `SAMPLE_MODE=true` makes it explicit and guarantees that nothing real is touched even if a `.env` exists.

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
$env:SAMPLE_MODE = "true"
.venv\Scripts\python run.py steward-demo          # the 8-step scenario, one trace per arbitration in logs\
.venv\Scripts\python -m pytest -q                 # 197 passed, 9 skipped (the suite sets SAMPLE_MODE itself)
.venv\Scripts\python scripts\mcp_smoke.py         # a real MCP client: 16 tools, the resource, the prompt -> PASS
.venv\Scripts\python scripts\make_examples.py --check
.venv\Scripts\python run.py serve                 # console: http://127.0.0.1:8000/console  (Ctrl+C to stop)
```

If `python` opens the Microsoft Store or is not found, use `py -3.12` instead of `python` in the first line. If PowerShell refuses to run scripts, this guide needs none: every line above is a plain command. The all-in-one script `scripts\windows\setup.ps1` (venv, H-MEM, Docker sources, tests) exists but was not run on the team's PC during the event; the lines above were.

### macOS and Linux

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
SAMPLE_MODE=true .venv/bin/python run.py steward-demo
SAMPLE_MODE=true .venv/bin/python -m pytest -q
SAMPLE_MODE=true .venv/bin/python scripts/mcp_smoke.py
.venv/bin/python scripts/make_examples.py --check
SAMPLE_MODE=true .venv/bin/python run.py serve        # console: http://127.0.0.1:8000/console
```

### What you should see

- `steward-demo`: eight numbered steps, a `Stack:` line saying `memory=local-fallback, data=sample-sqlite, model=offline`, and a JSON summary at the end (`pending_escalations: 2`). Traces in `logs/trace-*.jsonl`.
- `pytest`: `197 passed, 9 skipped`. The 9 skipped tests are the team's engine integration tests, which need their H-MEM and World Model services on ports 8765 and 8766.
- `mcp_smoke.py`: `spec v2 tools: 13/13, coordination: 3/3, missing: none` then `PASS`.
- The console: six tabs (Shared truth, Escalations, Clarifications, Context preview, Onboarding, Simulate an AI). In **Simulate an AI**, keep **Kind = decision** for a spend or a price: a *fact* is stored as shared knowledge without any limit check. Try `Book a booth at Batimat Paris for 11,500 EUR` as Inès Roux (escalates: above the 10,000 EUR limit), then approve it once in **Escalations** and raise the policy; the next booking under 12,000 EUR is stored citing it.

Options: `PORT=8010` changes the console port (`$env:PORT = "8010"` in PowerShell); `STEWARD_SPACE=<name>` gives you a fresh, separate company record; `STEWARD_SEED_POLICIES=true` starts with the three CEO policies of the video already in place; `HOST=0.0.0.0` exposes the console beyond the machine (it has no login: keep the default `127.0.0.1` unless you know why).

## 3. Level 2: plug your own AI in through MCP

Steward is an MCP server over stdio (`run.py mcp`). Identity comes from the client configuration: `OSEF_MEMBER` is the Brikk member the AI speaks for (any name of `domains/project_memory/data/members.csv`: Claire Morel is the CEO, Sami Haddad the CTO, Julie Caron an account executive...), `OSEF_AI_TOOL` the AI's name as it will appear in the record.

Templates: `docs/mcp/claude_desktop_config.json` (the CEO) and `docs/mcp/cursor-mcp.json` (the CTO). Replace `/ABSOLUTE/PATH/TO/Hackathon-GenAI-public` with your clone's path, twice. On Windows use forward slashes or doubled backslashes, and the venv's `python.exe`:

```json
{
  "mcpServers": {
    "steward": {
      "command": "C:/Users/you/Hackathon-GenAI-public/.venv/Scripts/python.exe",
      "args": ["C:/Users/you/Hackathon-GenAI-public/run.py", "mcp"],
      "env": {
        "OSEF_MEMBER": "Claire Morel",
        "OSEF_AI_TOOL": "Claude",
        "STEWARD_SPACE": "project",
        "SAMPLE_MODE": "true"
      }
    }
  }
}
```

Where the file goes:

- **Claude Desktop**: Settings → Developer → Edit Config, or directly `%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS. Restart Claude Desktop; the `steward` server and its 16 tools appear in the tools menu.
- **Cursor**: `.cursor/mcp.json` in the project you work in (or `~/.cursor/mcp.json` for every project), same content; enable the server in Cursor → Settings → MCP.

Drop `"SAMPLE_MODE": "true"` and add `"HMEM_URL": "http://127.0.0.1:8787"` once level 3 runs. Two AIs on the same `STEWARD_SPACE` share one company record: that is the demo (the CEO in Claude Desktop, the CTO in Cursor). First things to say to the AI: "onboard me", then "what's new?", then state a decision in a watched domain (a price, a date, a budget) and watch the verdict come back.

## 4. Level 3: the real stack

Only on a machine where Zetaris and Nightshift run. Keys and tokens live in `.env` (never committed; `.gitignore` covers it) and in Nightshift; nothing in this repository prints them.

```bash
cp .env.example .env                       # fill ZETARIS_API_KEY and METERLESS_RUNTIME_TOKEN, nothing else is required
cd hmem-service && bash setup.sh && npm start &        # vendors the Meterless H-MEM reference (Apache-2.0), starts it on :8787
cd .. && docker compose up -d brikk-db                 # source 1: Postgres with the Brikk tables on 127.0.0.1:5434
.venv/bin/python run.py serve &                        # source 2: the finance API, and the console
.venv/bin/python scripts/zetaris/run_steward_sql.py    # registers the 3 sources and the USL in Zetaris, then reads every table back
.venv/bin/python scripts/configure_nightshift.py       # pins the Nemotron ids on the three lanes, makes one test call
.venv/bin/python smoke_test.py                         # Zetaris, Nightshift, Nemotron, H-MEM: one line each
.venv/bin/python run.py steward-demo                   # the same scenario, this time with Nemotron on every trace line
DOMAIN=project_memory .venv/bin/python run.py ablation --profiles no_memory,full   # the real figures for the README
```

On the Mac used during the event, `bash scripts/after-zetaris.sh` runs this sequence and asks for the two tokens. On Windows, `scripts\windows\setup.ps1` prepares the venv, H-MEM and the Docker sources; the Zetaris and Nightshift steps are the same Python scripts. Details and ports: README, "The real stack"; the Zetaris material (DDL, queries, quality rule) is in `docs/zetaris/`.

With a real stack configured (a Zetaris key or a Nightshift token in `.env`), an unreachable H-MEM stops Steward on purpose rather than writing to a second store: start `npm start` in `hmem-service/` first, or set `SAMPLE_MODE=true` to go back to the offline path.

## 5. If something fails

| Symptom | Cause and fix |
| --- | --- |
| `python: command not found` / the Microsoft Store opens | Install Python 3.12+ from python.org (tick "Add to PATH" on Windows), or use `py -3.12` / `python3`. |
| `pip install` fails on `mcp` or `pydantic` | Python older than 3.10. Check `python --version`; 3.12 is what CI uses. |
| `Address already in use` on `run.py serve` | Another process holds 8000: set `PORT` (see level 1). |
| The console shows `LLM offline` | Expected without Nightshift. The verdicts come from the deterministic path and the traces say `model: null`. |
| `MemoryUnavailable: Meterless H-MEM does not answer` | A real stack is configured in `.env` but H-MEM is not running: `cd hmem-service && npm start`, or `SAMPLE_MODE=true`. |
| `pytest` collects 0 tests or import errors | Run it from the repository root, with the venv's Python (`.venv\Scripts\python -m pytest -q`). |
| Claude Desktop does not list the `steward` server | A wrong absolute path or a JSON syntax error in the config; test the command by hand: `.venv/bin/python scripts/mcp_smoke.py` must print `PASS`. Restart Claude Desktop after editing. |
| `setup.sh` cannot clone the Meterless repository | No network, or Git missing: the committed conformance run is `logs/samples/hmem-conformance.txt`; level 1 and 2 do not need it. |

Where the state lives, one set per `STEWARD_SPACE` and all ignored by Git: `data/memory-fallback-<space>.json` (the local record), `data/steward-journal-<space>.jsonl`, `data/steward-cursors-<space>.json`, `data/steward-profiles-<space>.json`, `data/alerts-<space>.json`, `data/progress-<space>.json` (journal, per-person cursors, questionnaire answers, alert inboxes, progress reports), `logs/` (one trace per arbitration), `hmem-service/.hmem-data/<space>/` (H-MEM when it runs). Use a new `STEWARD_SPACE` to start from a clean company.
