#!/bin/bash
# Everything after "Zetaris is up", in one go:  bash ~/open-agent-hack/scripts/after-zetaris.sh
#  1. saves your Zetaris API key in .env (from the clipboard, never shown)
#  2. starts H-MEM, the Brikk sources (Postgres + S3 drive), the Steward app and the MCP configs
#  3. registers the 3 Brikk sources and the semantic layer in Zetaris, then reads every table back
#  4. runs the smoke test, the demo scenario and one ablation pass on the real stack (Nemotron through Nightshift)
# Everything is logged in logs/after-zetaris.log so Claude can read it and fix what breaks.
set -uo pipefail
ROOT="$HOME/open-agent-hack"
cd "$ROOT" || exit 1
mkdir -p logs
LOG="$ROOT/logs/after-zetaris.log"
exec > >(tee -a "$LOG") 2>&1
echo "===== $(date '+%F %T') after-zetaris ====="
say() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
setvar() { touch .env; { grep -v "^$1=" .env || true; printf '%s=%s\n' "$1" "$2"; } > .env.tmp && mv .env.tmp .env; }

say "1/4 Zetaris is answering?"
for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 3 http://localhost:3000 || true)
  [ "$code" = "200" ] && break
  sleep 6
done
echo "Zetaris UI: HTTP ${code:-none}"

say "2/4 Zetaris API key"
if grep -qE '^ZETARIS_API_KEY=.{20,}' .env && ! grep -q '^ZETARIS_API_KEY=your-' .env; then
  echo "Already in .env: keeping it (rerun with --new-key to replace it)."
fi
if [ "${1:-}" = "--new-key" ] || ! grep -qE '^ZETARIS_API_KEY=.{20,}' .env || grep -q '^ZETARIS_API_KEY=your-' .env; then
  open "http://localhost:3000" 2>/dev/null || true
  echo "In the Zetaris window: sign in with the admin email/password you just chose,"
  echo "then Management > API Tokens > create a key named "steward", and click Copy (shown once)."
  bash "$ROOT/scripts/set-secret.sh" ZETARIS_API_KEY
fi
setvar ZETARIS_REST_URL "http://localhost:8888/api/v1.0"
setvar ZETARIS_ORG_ID "1"
setvar SAMPLE_MODE "false"
chmod 600 .env

if ! grep -qE '^METERLESS_RUNTIME_TOKEN=.{16,}' .env || grep -q '^METERLESS_RUNTIME_TOKEN=your-' .env; then
  echo
  echo "Nightshift runtime token: in Nightshift > SETUP > PROVIDERS > Runtime endpoint, click Copy next to AUTH TOKEN."
  bash "$ROOT/scripts/set-secret.sh" METERLESS_RUNTIME_TOKEN || echo "Skipped: rerun later with  bash scripts/set-secret.sh METERLESS_RUNTIME_TOKEN"
fi
setvar METERLESS_BASE_URL "http://127.0.0.1:8088/v1"

say "3/4 H-MEM, Brikk sources, Steward app, MCP configs, Nightshift lanes"
bash "$ROOT/scripts/setup-steward-mac.sh"

say "4/5 Register the Brikk sources and the semantic layer in Zetaris"
sleep 5
"$ROOT/.venv/bin/python" "$ROOT/scripts/zetaris/run_steward_sql.py" || echo "Registration stopped: Claude reads logs/after-zetaris.log and fixes it."

say "5/5 The real stack: smoke test, the demo scenario, one ablation pass (Nemotron through Nightshift)"
set -a; . "$ROOT/.env"; set +a
export SAMPLE_MODE=false STEWARD_SPACE=real-$(date +%H%M)
"$ROOT/.venv/bin/python" "$ROOT/smoke_test.py" 2>&1 | tail -20 || echo "smoke test failed: see above"
"$ROOT/.venv/bin/python" "$ROOT/run.py" steward-demo > "$ROOT/logs/steward-demo-real.json" 2> "$ROOT/logs/steward-demo-real.txt" \
  && echo "demo ok: logs/steward-demo-real.txt" || echo "demo failed: logs/steward-demo-real.txt"
tail -5 "$ROOT/logs/steward-demo-real.txt"
DOMAIN=project_memory "$ROOT/.venv/bin/python" "$ROOT/run.py" ablation --profiles no_memory,full > "$ROOT/logs/ablation-real.txt" 2>&1 \
  && echo "ablation ok: logs/ablation-real.txt" || echo "ablation failed: logs/ablation-real.txt"
tail -12 "$ROOT/logs/ablation-real.txt"
grep -h '"model": "nvidia' "$ROOT"/logs/trace-*.jsonl 2>/dev/null | head -1 | cut -c1-160 || true
echo "Traces with the served model are in logs/trace-*.jsonl (model field)."

echo
echo "Done. Tell Claude 'after-zetaris fini' (the log is in logs/after-zetaris.log)."
