#!/bin/bash
# Local Zetaris install for OSEF, following docs/install/updated_zetaris_installation_guide.md
# of the Zetaris getting-started repository. Run it in Terminal:  bash ~/open-agent-hack/scripts/install-zetaris.sh
# It asks for two things only you can give: the registry credentials (docker login) and the admin
# email + password of YOUR local Zetaris. Nothing secret is printed or written anywhere but zetaris-platform/.env.
set -euo pipefail

ROOT="$HOME/open-agent-hack"
DEST="$ROOT/zetaris-platform"
say() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

say "1/7 Docker"
docker info >/dev/null 2>&1 || { echo "Docker Desktop is not running: open it, wait for 'Engine running', rerun."; exit 1; }
echo "Docker memory: $(docker info --format '{{.MemTotal}}' | awk '{printf "%.1f GB", $1/1024/1024/1024}') · CPUs: $(docker info --format '{{.NCPU}}')"

say "2/7 The platform archive"
if [ ! -f "$DEST/docker-compose.yml" ]; then
  ZIP="$(ls -t "$HOME"/Downloads/zetaris-platform*.zip 2>/dev/null | head -1 || true)"
  [ -n "$ZIP" ] || { echo "zetaris-platform.zip not found in Downloads (page Run locally)."; exit 1; }
  echo "Using $ZIP"
  cp "$ZIP" "$ROOT/zetaris-platform.zip"
  (cd "$ROOT" && unzip -q -o zetaris-platform.zip)
fi
cd "$DEST"
[ -f docker-compose.yml ] || { echo "No docker-compose.yml in $DEST: the archive layout is unexpected."; exit 1; }
[ -f .env ] || { echo "No .env in the bundle: ask Zetaris for the matching .env (see the install guide)."; exit 1; }

say "3/7 Registry sign-in (credentials from the Run locally page)"
# If you already pasted the page's "docker login ... --password-stdin" command, this reuses the stored login.
docker login zetarishackathon.azurecr.io

say "4/7 Preflight"
./preflight.sh || { echo "Fix the preflight failures above, then rerun this script."; exit 1; }

say "5/7 Local settings in zetaris-platform/.env"
setvar() {  # key value: drop the old line, append the new one (no sed: a password may hold & or |)
  { grep -v "^$1=" .env || true; printf '%s=%s\n' "$1" "$2"; } > .env.new && mv .env.new .env
}
KEEP=n
if [ -f .osef-configured ]; then read -r -p "Admin email/password already set by this script. Keep them? [Y/n] " KEEP; KEEP=${KEEP:-y}
elif grep -q '^ZETARIS_ADMIN_PASSWORD=..*' .env && grep -q '^ZETARIS_ADMIN_EMAIL=..*' .env; then
  echo "The bundle already sets an admin account (see its README); keeping it. Change the password later in the web UI."
  KEEP=y
fi
if [[ "$KEEP" =~ ^[Yy] ]]; then
  echo "Keeping the admin account already in .env."
else
  read -r -p "Admin email for your local Zetaris: " ADMIN_EMAIL
  while true; do
    read -r -s -p "Admin password (8+ chars, upper, lower, digit, one of @!%*?& ; no \$): " ADMIN_PASS; echo
    if [[ ${#ADMIN_PASS} -ge 8 && "$ADMIN_PASS" =~ [a-z] && "$ADMIN_PASS" =~ [A-Z] && "$ADMIN_PASS" =~ [0-9] \
          && "$ADMIN_PASS" =~ [@!%*?\&] && ! "$ADMIN_PASS" =~ [^A-Za-z0-9@!%*?\&] ]]; then break; fi
    echo "Not accepted (Zetaris' policy, and no \$ so that .env stays literal), try again."
  done
  setvar ZETARIS_ADMIN_EMAIL "$ADMIN_EMAIL"
  setvar ZETARIS_ADMIN_PASSWORD "$ADMIN_PASS"
  unset ADMIN_PASS
  touch .osef-configured
fi
setvar ZETARIS_ADMIN_ORG "OSEF"
setvar ZSPARK_DRIVER_MEM "2g"
setvar ZSPARK_DRIVER_CORES "2"
setvar ZSPARK_MASTER_URL "local[2]"
setvar ZETARIS_API_MAX_HEAP "1g"
setvar UI_PORT "3000"
setvar ALLOWED_ORIGINS "http://localhost:3000"
setvar GUI_URL "http://localhost:3000"
setvar ZETARIS_SEED_TPCH "true"
chmod 600 .env
docker compose config --quiet && echo "Configuration valid."

say "6/7 Pull and start (first time: 10 to 30 minutes)"
docker compose pull
docker compose up -d

say "7/7 Waiting for bootstrap, then verify"
for i in $(seq 1 60); do
  state="$(docker compose ps --all --format '{{.Service}} {{.State}}' 2>/dev/null | awk '$1=="bootstrap"{print $2}')"
  [ "$state" = "exited" ] && break
  sleep 15
done
docker compose ps --all
./verify.sh || { echo "Some checks failed: wait a minute and run ./verify.sh again in $DEST."; exit 1; }
echo
echo "Zetaris is up: open http://localhost:3000, sign in, create an API key, and tell Claude 'zetaris ok'."
