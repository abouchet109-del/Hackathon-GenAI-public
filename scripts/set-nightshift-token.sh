#!/bin/bash
# Put the Nightshift runtime token into .env straight from the clipboard, without showing it.
# Run in Terminal:  bash ~/open-agent-hack/scripts/set-nightshift-token.sh
# It waits while you click "Copy" next to AUTH TOKEN in Nightshift > Setup > Providers, then press Enter.
set -euo pipefail
ROOT="$HOME/open-agent-hack"
ENV="$ROOT/.env"
echo "In Nightshift > Setup > Providers > AUTH TOKEN, click Copy, then come back here and press Enter."
read -r _
TOKEN="$(pbpaste | tr -d '[:space:]')"
if [ "${#TOKEN}" -lt 16 ]; then
  echo "The clipboard does not hold a token: click Copy next to AUTH TOKEN in Nightshift, then run this again."
  exit 1
fi
[ -f "$ENV" ] && cp "$ENV" "$ENV.bak-$(date +%s)"
touch "$ENV"
grep -v -E '^(METERLESS_RUNTIME_TOKEN|METERLESS_BASE_URL)=' "$ENV" > "$ENV.tmp" || true
printf 'METERLESS_BASE_URL=http://127.0.0.1:8088/v1\nMETERLESS_RUNTIME_TOKEN=%s\n' "$TOKEN" >> "$ENV.tmp"
mv "$ENV.tmp" "$ENV"
chmod 600 "$ENV"
printf '' | pbcopy   # clear the clipboard
echo "Runtime token saved in .env (${TOKEN:0:4}…${TOKEN: -4}). Clipboard cleared."
if [ -x "$ROOT/.venv/bin/python" ]; then
  "$ROOT/.venv/bin/python" "$ROOT/scripts/configure_nightshift.py" --check || true
fi
