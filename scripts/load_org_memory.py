"""Load the lessons of past projects (Orion, Vega) into H-MEM's organisation memory.

The archives are read through Zetaris (or its cache, see agent/zetaris.py);
each lesson becomes a long-term memory with its provenance, so S9 can recall
Orion's lesson. Idempotent: a lesson already in memory is not written again.
Start the H-MEM service first (README, section Engines); without it, the client
falls back to its local memory and says so.

    python scripts/load_org_memory.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.hmem import HMem, load_org_lessons  # noqa: E402
from agent.sources import load_source_zetaris  # noqa: E402
from agent.zetaris import ZetarisClient  # noqa: E402


def main():
    projects, source_origin = load_source_zetaris("past_projects", ZetarisClient())
    memory = HMem()
    written = load_org_lessons(memory, projects)
    total = sum(len(p.lessons) for p in projects)
    print(f"past projects read from {source_origin}: {len(projects)}, lessons: {total}")
    print(f"lessons written to H-MEM ({memory.origin}): {written}, already there: {total - written}")
    if memory.fallback_reason:
        print(f"fallback: {memory.fallback_reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
