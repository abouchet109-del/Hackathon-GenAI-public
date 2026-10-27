"""Start a Meterless engine service: H-MEM on :8765 or World Model on :8766.

    python scripts/engine_service.py hmem
    python scripts/engine_service.py world_model

Fetches the Meterless repository into external/ (git-ignored) if needed and
installs the reference's dev tools (tsx, via npm ci); the references have no
runtime dependency. Data persists in .state/hmem/ or .state/world-model/
(git-ignored). Options: HMEM_PORT, HMEM_DATA_DIR, WORLD_MODEL_PORT,
WORLD_MODEL_DATA_DIR. Stop with Ctrl+C.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "external" / "meterless"
ENGINES = {"hmem": "hmem", "world_model": "world-model"}  # service -> engine folder


def tool(name):
    path = shutil.which(name)
    if path is None:
        sys.exit(f"{name} not found: install it (README, section Engines)")
    return path


def reference(engine):
    """The engine's reference folder, fetched and installed if needed."""
    if not REPO.exists():
        subprocess.run([tool("git"), "clone", "--depth", "1",
                        "https://github.com/Meterless/Meterless.git", str(REPO)], check=True)
    folder = REPO / "engines" / engine / "reference"
    if not (folder / "node_modules").exists():
        subprocess.run([tool("npm"), "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
                       cwd=folder, check=True)
    return folder


def tsx(folder, script):
    """Run a TypeScript file with the reference's own tsx."""
    cli = folder / "node_modules" / "tsx" / "dist" / "cli.mjs"
    return subprocess.run([tool("node"), str(cli), str(script)], cwd=folder).returncode


def main(argv):
    if len(argv) != 2 or argv[1] not in ENGINES:
        print(__doc__)
        return 2
    folder = reference(ENGINES[argv[1]])
    try:
        return tsx(folder, ROOT / "services" / argv[1] / "server.ts")
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
