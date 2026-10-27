"""Generate the three example inputs and their outputs by running Steward, never by hand.

  python scripts/make_examples.py           # (re)write input_examples/ and output_examples/
  python scripts/make_examples.py --check   # run the inputs again and compare the decisions with output_examples/

Each input is what POST /run accepts: {"run_id", "input": {content, author, ai_tool, kind, topic}, "options"}.
Each output is the full response of the harness on a freshly seeded company memory, in SAMPLE_MODE (the
stack line says so). Run-specific fields (timestamps, trace paths, journal ids) are kept in the files and
ignored by --check.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SAMPLE_MODE", "true")
os.environ.setdefault("HMEM_URL", "http://127.0.0.1:1")  # the local fallback: the files must not depend on a service

from app.steward import Steward  # noqa: E402

INPUTS = [
    {"run_id": "example_1_supersede", "input": {
        "content": "Support hours move to 9:00-18:00 on weekdays, with a 4-hour first-response target.",
        "author": "Yanis Moreau", "ai_tool": "Claude", "kind": "decision", "topic": "support_policy"},
     "options": {"profile": "full"},
     "about": "The head of Customer Success changes the policy of his own topic: the new decision replaces the old "
              "record, which is kept in the history (supersede), both cited."},
    {"run_id": "example_2_escalate", "input": {
        "content": "Sponsor the Salon des Artisans for 15,000 EUR.",
        "author": "Inès Roux", "ai_tool": "ChatGPT", "kind": "decision", "topic": "marketing_spend"},
     "options": {"profile": "full"},
     "about": "Marketing commits above the topic limit and above the CEO's standing policy (12,000 EUR per trade "
              "show): escalated to the CEO, nothing written."},
    {"run_id": "example_3_clarify", "input": {
        "content": "The price is now 19 EUR per user per month.",
        "author": "Julie Caron", "ai_tool": "ChatGPT", "kind": "decision", "topic": "pricing"},
     "options": {"profile": "full"},
     "about": "An account executive contradicts the CEO's price: her AI is asked 'error or real change?' first."},
]
KEEP = ("decision", "summary", "citations", "critic_score", "needs_ceo")


def run_all() -> list[dict]:
    st = Steward(space="examples")
    outs = []
    for ex in INPUTS:
        st.reset()  # every example starts from the seeded company memory
        res = st.remember(ex["input"]["content"], ex["input"]["author"], ex["input"]["ai_tool"],
                          ex["input"]["kind"], ex["input"]["topic"], run_id=ex["run_id"])
        outs.append({"run_id": ex["run_id"], "about": ex["about"], "stack": res.get("stack"),
                     "decision": res["decision"], "summary": res["why"], "citations": res["citations"],
                     "critic_score": res.get("critic_score"), "needs_ceo": res.get("needs_ceo"),
                     "applied": res.get("applied"), "alerts_sent": res.get("alerts_sent"), "trace": res.get("trace")})
    return outs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    outs = run_all()
    inp_dir, out_dir = ROOT / "input_examples", ROOT / "output_examples"
    if args.check:
        bad = []
        for ex, out in zip(INPUTS, outs):
            saved = json.loads((out_dir / f"{ex['run_id']}.json").read_text(encoding="utf-8"))
            for k in KEEP:
                if saved.get(k) != out.get(k):
                    bad.append(f"{ex['run_id']}.{k}: saved {saved.get(k)!r} != fresh {out.get(k)!r}")
        print("\n".join(bad) if bad else f"{len(outs)} examples: outputs match a fresh run")
        return 1 if bad else 0
    inp_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)
    for ex, out in zip(INPUTS, outs):
        (inp_dir / f"{ex['run_id']}.json").write_text(json.dumps(
            {k: ex[k] for k in ("run_id", "input", "options")}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out_dir / f"{ex['run_id']}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{ex['run_id']}: {out['decision']} {out['citations']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
