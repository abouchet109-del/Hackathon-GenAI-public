#!/bin/bash
# One-shot setup of the Steward demo on the Mac. Run in Terminal:  bash ~/open-agent-hack/scripts/setup-steward-mac.sh
# - installs the Python dependencies (incl. the MCP SDK) in .venv
# - vendors and starts the Meterless H-MEM engine (port 8787)
# - starts the Brikk sources for Zetaris: Postgres (5434) and the S3 drive (9000), if Docker is running
# - starts the Steward app: console http://localhost:8000/console and the finance API /finance/budgets
# - connects Claude Desktop (as the CEO, Claire Morel) and Cursor (as the CTO, Sami Haddad) to the Steward MCP server
# Idempotent: run it again any time; it only starts what is not running. Logs in logs/.
set -uo pipefail
ROOT="$HOME/open-agent-hack"
cd "$ROOT" || exit 1
mkdir -p logs data
say() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
PY="$ROOT/.venv/bin/python"

say "1/6 Python dependencies"
[ -x "$PY" ] || python3 -m venv .venv
"$PY" -m pip install -q --upgrade pip >/dev/null 2>&1
"$PY" -m pip install -q -r requirements.txt && echo "ok"

say "2/6 Meterless H-MEM engine"
if curl -s -m 2 http://127.0.0.1:8787/health >/dev/null; then
  echo "already running"
else
  if [ ! -d hmem-service/vendor/hmem-reference ]; then
    METERLESS_REPO="$ROOT/vendor/meterless" bash hmem-service/setup.sh
  fi
  (cd hmem-service && [ -d node_modules ] || npm install --silent)
  (cd hmem-service && HMEM_DIR="$ROOT/data/hmem" nohup npm start > "$ROOT/logs/hmem.log" 2>&1 &)
  for i in $(seq 1 20); do curl -s -m 1 http://127.0.0.1:8787/health >/dev/null && break; sleep 1; done
  curl -s -m 2 http://127.0.0.1:8787/health && echo
fi
(cd hmem-service && npm run -s conformance 2>/dev/null | tail -1)

say "3/6 Brikk sources for Zetaris (Postgres + S3 drive)"
if docker info >/dev/null 2>&1; then
  docker compose up -d brikk-db drive drive-init && echo "brikk-db on :5434, drive on :9000"
else
  echo "Docker is not running: skipped (start Docker Desktop and rerun)"
fi

say "4/6 Steward app (console + finance API) on :8000"
if curl -s -m 2 http://127.0.0.1:8000/health >/dev/null; then
  echo "already running"
else
  STEWARD_SPACE=project nohup "$PY" run.py serve > logs/serve.log 2>&1 &
  for i in $(seq 1 20); do curl -s -m 1 http://127.0.0.1:8000/health >/dev/null && break; sleep 1; done
fi
curl -s -m 3 http://127.0.0.1:8000/finance/budgets | head -c 120; echo
echo "Console: http://localhost:8000/console"

say "5/6 Connect Claude Desktop (CEO) and Cursor (CTO) over MCP"
"$PY" - <<'PYEOF'
import json, os, shutil, time
root = os.path.expanduser("~/open-agent-hack")
py = os.path.join(root, ".venv/bin/python")
def entry(member, tool):
    return {"command": py, "args": [os.path.join(root, "run.py"), "mcp"],
            "env": {"OSEF_MEMBER": member, "OSEF_AI_TOOL": tool, "STEWARD_SPACE": "project",
                    "HMEM_URL": "http://127.0.0.1:8787"}}
targets = [
    (os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json"), entry("Claire Morel", "Claude")),
    (os.path.join(root, ".cursor/mcp.json"), entry("Sami Haddad", "Cursor")),
]
for path, value in targets:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cfg = {}
    if os.path.exists(path):
        shutil.copy(path, f"{path}.bak-{int(time.time())}")   # keep a backup of the user's config
        try:
            cfg = json.load(open(path))
        except json.JSONDecodeError:
            print(f"!! {path} is not valid JSON: left untouched"); continue
    cfg.setdefault("mcpServers", {})["osef-steward"] = value
    json.dump(cfg, open(path, "w"), indent=2)
    print("connected:", path)
PYEOF

say "6/6 Nightshift lanes (Nemotron)"
if "$PY" scripts/configure_nightshift.py; then
  pkill -f "run.py serve" 2>/dev/null; sleep 1   # restart the app so it reads the new lanes
  STEWARD_SPACE=project nohup "$PY" run.py serve > logs/serve.log 2>&1 &
  echo "App restarted on the Nemotron lanes."
else
  echo "Nightshift not ready yet: rerun this script once the NVIDIA key and lanes are set."
fi

echo
echo "Done. Restart Claude Desktop (Cmd+Q, reopen) and open ~/open-agent-hack in Cursor to see the 'osef-steward' tools."
