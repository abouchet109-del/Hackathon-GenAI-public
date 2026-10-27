#!/bin/bash
# Copies the Meterless H-MEM reference implementation and its conformance suite
# (Apache-2.0, github.com/Meterless/Meterless) into vendor/, then installs tsx.
set -euo pipefail
cd "$(dirname "$0")"
SRC="${METERLESS_REPO:-../vendor/meterless}"
if [ ! -d "$SRC/engines/hmem" ]; then
  echo "Meterless repo not found at $SRC; cloning it."
  git clone --depth 1 https://github.com/Meterless/Meterless.git /tmp/meterless-$$
  SRC=/tmp/meterless-$$
fi
rm -rf vendor && mkdir -p vendor
mkdir -p vendor/hmem-reference
tar -C "$SRC/engines/hmem/reference" --exclude=node_modules -cf - . | tar -C vendor/hmem-reference -xf -
cp -R "$SRC/engines/hmem/conformance" vendor/hmem-conformance
cp "$SRC/LICENSE" vendor/LICENSE-meterless
npm install --silent
echo "H-MEM reference vendored. Run: npm start   |   npm run conformance"
