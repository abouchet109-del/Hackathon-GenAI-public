"""Point the app at the Nemotron lanes of Nightshift and prove a real call works.

  .venv/bin/python scripts/configure_nightshift.py            # pick lanes, write them to .env, test one call
  .venv/bin/python scripts/configure_nightshift.py --check    # only list models and test, change nothing

Reads METERLESS_BASE_URL and METERLESS_RUNTIME_TOKEN from .env (the token is never printed).
Lanes: fast = a small Nemotron (Nano / Lightning), deep and judge = a large one (Super / Ultra).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"


def pick(models: list[str], *patterns: str) -> str | None:
    for pat in patterns:
        for m in models:
            if re.search(pat, m, re.I):
                return m
    return None


def set_env(key: str, value: str) -> None:
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    lines = [l for l in lines if not l.startswith(f"{key}=")] + [f"{key}={value}"]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    cfg = dotenv_values(ENV)
    base = (cfg.get("METERLESS_BASE_URL") or "http://127.0.0.1:8088/v1").rstrip("/")
    token = cfg.get("METERLESS_RUNTIME_TOKEN") or ""
    if not token or token.startswith("your-"):
        print("METERLESS_RUNTIME_TOKEN is missing in .env: copy it from the Nightshift Console.")
        return 2
    headers = {"Authorization": f"Bearer {token}", "meterless-app": cfg.get("METERLESS_APP", "osef-hackathon"),
               "meterless-scope": "user"}
    try:
        r = requests.get(f"{base}/models", headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"Nightshift does not answer at {base}: {e}. Is the app running?")
        return 1
    if r.status_code in (401, 403):
        print("Nightshift refused the token (401/403): copy the runtime token again from its Console.")
        return 1
    r.raise_for_status()
    models = [m.get("id") for m in r.json().get("data", []) if m.get("id")]
    print(f"{len(models)} models/lanes visible. Nemotron: {[m for m in models if 'nemotron' in m.lower()] or 'none'}")
    fast = pick(models, r"nemotron.*(nano|lightning|mini)", r"nemotron")
    deep = pick(models, r"nemotron.*super", r"nemotron.*ultra", r"nemotron")
    judge = pick(models, r"nemotron.*ultra", r"nemotron.*super", r"nemotron")
    if not (fast and deep and judge):
        print("No Nemotron lane found. In Nightshift: Setup > Providers > NVIDIA (paste the key), then assign Nemotron"
              " models to lanes, and run this again.")
        return 1
    print(f"fast={fast}\ndeep={deep}\njudge={judge}")
    if not args.check:
        shutil.copy(ENV, ENV.with_name(f".env.bak-{int(time.time())}"))
        set_env("METERLESS_MODEL_FAST", fast)
        set_env("METERLESS_MODEL_DEEP", deep)
        set_env("METERLESS_MODEL_JUDGE", judge)
        set_env("SAMPLE_MODE", "false")
        print(".env updated (backup kept).")
    body = {"model": deep, "temperature": 0, "messages": [{"role": "user", "content": 'Answer with {"ok": true} only.'}]}
    r = requests.post(f"{base}/chat/completions", headers=headers, json=body, timeout=120)
    r.raise_for_status()
    data = r.json()
    print(f"Test call served by: {data.get('model')} -> {data['choices'][0]['message']['content'][:80]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
