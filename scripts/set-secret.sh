#!/bin/bash
# Save a secret from the clipboard into ~/open-agent-hack/.env, without showing it.
#   bash ~/open-agent-hack/scripts/set-secret.sh ZETARIS_API_KEY
#   bash ~/open-agent-hack/scripts/set-secret.sh METERLESS_RUNTIME_TOKEN
# It waits while you click "Copy" next to the key in the other app, then you press Enter here.
set -euo pipefail
KEY="${1:?usage: set-secret.sh ENV_VAR_NAME}"
ROOT="$HOME/open-agent-hack"
ENV="$ROOT/.env"
echo "Copy the value for $KEY (its Copy button), then come back here and press Enter."
read -r _
VAL="$(pbpaste | tr -d '[:space:]')"
if [ "${#VAL}" -lt 12 ]; then echo "The clipboard does not hold a key: copy it, then run this again."; exit 1; fi
touch "$ENV"; cp "$ENV" "$ENV.bak-$(date +%s)"
{ grep -v "^$KEY=" "$ENV" || true; printf '%s=%s\n' "$KEY" "$VAL"; } > "$ENV.tmp" && mv "$ENV.tmp" "$ENV"
chmod 600 "$ENV"
printf '' | pbcopy
echo "$KEY saved in .env (${VAL:0:4}…${VAL: -4}). Clipboard cleared."
