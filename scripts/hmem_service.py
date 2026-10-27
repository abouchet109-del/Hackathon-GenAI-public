"""Start the H-MEM service (services/hmem/server.ts) on http://127.0.0.1:8765.

Fetches the Meterless repository into external/ (git-ignored) if needed and
installs the reference's dev tools (tsx, via npm ci); the reference has no
runtime dependency. Memories persist in .state/hmem/ (git-ignored).
Options: HMEM_PORT, HMEM_DATA_DIR. Stop with Ctrl+C.

    python scripts/hmem_service.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "external" / "meterless"
REFERENCE = REPO / "engines" / "hmem" / "reference"
SERVER = ROOT / "services" / "hmem" / "server.ts"


def tool(name):
    path = shutil.which(name)
    if path is None:
        sys.exit(f"{name} not found: install it (README, section H-MEM)")
    return path


def main():
    if not REPO.exists():
        subprocess.run([tool("git"), "clone", "--depth", "1",
                        "https://github.com/Meterless/Meterless.git", str(REPO)], check=True)
    if not (REFERENCE / "node_modules").exists():
        subprocess.run([tool("npm"), "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
                       cwd=REFERENCE, check=True)
    tsx = REFERENCE / "node_modules" / "tsx" / "dist" / "cli.mjs"
    try:
        return subprocess.run([tool("node"), str(tsx), str(SERVER)], cwd=REFERENCE).returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
