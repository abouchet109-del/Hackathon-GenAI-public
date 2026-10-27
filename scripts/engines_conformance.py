"""Run the official conformance suites of the engines the services serve.

H-MEM (13 checks) and World Model (8 checks), each against the reference
implementation that services/hmem/ and services/world_model/ load unchanged.
Exit code 0 only if both suites pass.

    python scripts/engines_conformance.py
"""
import sys

from engine_service import ENGINES, reference, tsx


def main():
    failed = []
    for engine in ENGINES.values():
        folder = reference(engine)
        print(f"--- {engine} ---", flush=True)
        if tsx(folder, folder.parent / "conformance" / "runner.ts") != 0:
            failed.append(engine)
    print("all suites pass" if not failed else f"FAILED: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
