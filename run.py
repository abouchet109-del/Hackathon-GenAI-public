"""OSEF decision agent - single entry point.

  python run.py run --input input_examples/example_1.json [--profile full]
  python run.py serve                      # POST /run on 0.0.0.0:$PORT
  python run.py ablation [--repeats 3]     # what each block adds, written to logs/
  python run.py learn --input item.json --decision pay --note "EDF up to 120 EUR"
  python run.py demo-memory                # 3 sessions: wrong, corrected, remembered
  python run.py seed-memory                # load domains/<domain>/memory_seed.jsonl

Steward (shared project memory for a team of different AIs):
  python run.py mcp                        # MCP server on stdio (Claude Desktop, Cursor...)
  python run.py steward-demo               # the demo: escalation, CEO policy, remembered, replaced, protected
  python run.py steward-brief              # the current shared truth
  DOMAIN=project_memory python run.py ablation
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252: keep names and EUR signs readable
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from app.config import SETTINGS


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--input", required=True)
    p_run.add_argument("--profile", default="full")
    p_run.add_argument("--space", default=None, help="H-MEM space (default from HMEM_SPACE)")
    sub.add_parser("serve")
    p_abl = sub.add_parser("ablation")
    p_abl.add_argument("--profiles", default="model_only,rules_only,no_memory,no_critic,full")
    p_abl.add_argument("--repeats", type=int, default=1)
    p_abl.add_argument("--limit", type=int, default=None)
    p_learn = sub.add_parser("learn")
    p_learn.add_argument("--input", required=True)
    p_learn.add_argument("--decision", required=True)
    p_learn.add_argument("--note", default="")
    p_learn.add_argument("--space", default=None)
    sub.add_parser("demo-memory")
    p_seed = sub.add_parser("seed-memory")
    p_seed.add_argument("--space", default=None)
    sub.add_parser("mcp")
    sub.add_parser("steward-demo")
    p_brief = sub.add_parser("steward-brief")
    p_brief.add_argument("--space", default="project")
    args = parser.parse_args(argv)

    if args.cmd == "mcp":
        from app.mcp_server import main as mcp_main
        mcp_main()
        return 0

    if args.cmd == "steward-brief":
        from app.steward import Steward, dumps
        print(dumps(Steward(space=args.space).brief()))
        return 0

    if args.cmd == "steward-demo":
        from app.steward_demo import run_demo
        _print(run_demo())
        return 0

    if args.cmd == "serve":
        import uvicorn
        uvicorn.run("app.server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
        return 0

    from app.pipeline import Harness

    if args.cmd == "run":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        item = payload.get("input", payload)
        profile = (payload.get("options") or {}).get("profile", args.profile)
        _print(Harness(memory_space=args.space).run(item, profile=profile, run_id=payload.get("run_id")))
        return 0

    if args.cmd == "learn":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        _print(Harness(memory_space=args.space).learn(payload.get("input", payload), args.decision, args.note))
        return 0

    if args.cmd == "seed-memory":
        from app.evaluation import seed_memory
        h = Harness(memory_space=args.space)
        print(f"{seed_memory(h, SETTINGS.domain_dir)} owner corrections loaded into {h.memory.name}", file=sys.stderr)
        return 0

    if args.cmd == "ablation":
        from app.evaluation import run_ablation
        report = run_ablation(args.profiles.split(","), repeats=args.repeats, limit=args.limit)
        print(Path(report["files"][0]).read_text(encoding="utf-8") if Path(report["files"][0]).exists() else report["results"])
        return 0

    if args.cmd == "demo-memory":
        from app.evaluation import load_cases
        h = Harness(memory_space="demo")
        h.memory.reset()
        cases = {c["id"]: c for c in load_cases(SETTINGS.domain_dir)}
        print("\n=== Session 1: an EDF invoice above the auto-pay limit ===", file=sys.stderr)
        first = h.run(cases["c03"], run_id="demo-session1")
        print(f"Decision: {first['output']['decision']}  ({first['output']['summary']})", file=sys.stderr)
        print("\n=== Session 2: the owner corrects the agent ===", file=sys.stderr)
        learned = h.learn(cases["c03"], "pay", "I always pay EDF up to 120 EUR without asking.")
        print(f"Stored in {learned['engine']}: {learned['content']}", file=sys.stderr)
        print("\n=== Session 3: a new, similar EDF invoice ===", file=sys.stderr)
        third = h.run(cases["c04"], run_id="demo-session3")
        print(f"Decision: {third['output']['decision']}  citations={third['output']['citations']}", file=sys.stderr)
        print("\n=== Control: an EDF invoice above the owner's ceiling ===", file=sys.stderr)
        ctrl = h.run(cases["c05"], run_id="demo-control")
        print(f"Decision: {ctrl['output']['decision']}", file=sys.stderr)
        _print({"session1": first["output"]["decision"], "session3": third["output"]["decision"],
                "control": ctrl["output"]["decision"], "traces": [first["log_file"], third["log_file"], ctrl["log_file"]]})
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
