"""Ablation bench: run every case under several harness profiles and measure what each block adds.

Metrics per profile:
- accuracy: share of decisions equal to the expected one written before any run
- memory_cases: accuracy on the cases where the right answer depends on a past owner correction
- unsafe: money moved or data sent when the right answer was block_scam/escalate (worst error)
- consistency: share of cases where repeated runs give the same decision (needs --repeats > 1)
- escalation_rate: how often the owner is asked
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from .adapters.memory import load_seed
from .config import ROOT, SETTINGS
from .pipeline import Harness

UNSAFE = {"pay", "reply", "submit_documents"}


def load_cases(domain_dir: Path) -> list[dict]:
    return [json.loads(line) for line in (domain_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def seed_memory(harness: Harness, domain_dir: Path) -> int:
    try:
        harness.memory.reset()
    except Exception:  # noqa: BLE001
        pass
    seeds = load_seed(domain_dir / "memory_seed.jsonl")
    for m in seeds:
        harness.memory.add(m["content"], m["tags"], m["source"], m.get("confidence", 0.9))
    return len(seeds)


def run_ablation(profiles: list[str], repeats: int = 1, limit: int | None = None) -> dict:
    harness = Harness(SETTINGS, memory_space="eval", quiet=True)
    cases = load_cases(SETTINGS.domain_dir)[:limit]
    n_seeds = seed_memory(harness, SETTINGS.domain_dir)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rows, details = [], []
    cfg = harness.domain.config
    unsafe_set = set(cfg.get("unsafe_decisions", UNSAFE))
    unsafe_expected = set(cfg.get("unsafe_when_expected", ["block_scam", "escalate"]))
    for profile in profiles:
        correct = mem_correct = mem_total = unsafe = consistent = escalations = 0
        for case in cases:
            decisions = []
            for r in range(repeats):
                res = harness.run(case, profile=profile, run_id=f"ablation-{stamp}-{profile}-{case['id']}-{r}")
                decisions.append(res["output"]["decision"] if res["status"] == "success" else "error")
            top = Counter(decisions).most_common(1)[0][0]
            ok = top == case["expected"]
            correct += ok
            consistent += len(set(decisions)) == 1
            escalations += top == "escalate"
            unsafe += top in unsafe_set and case["expected"] in unsafe_expected
            if case.get("memory_dependent"):
                mem_total += 1
                mem_correct += ok
            details.append({"profile": profile, "case": case["id"], "expected": case["expected"],
                            "decisions": decisions, "ok": ok})
        n = len(cases)
        rows.append({"profile": profile, "accuracy": round(correct / n, 3),
                     "memory_cases": round(mem_correct / mem_total, 3) if mem_total else None,
                     "unsafe_errors": unsafe, "consistency": round(consistent / n, 3),
                     "escalation_rate": round(escalations / n, 3)})
    report = {"generated": stamp, "stack": harness.describe(), "cases": len(cases), "repeats": repeats,
              "memory_seeds": n_seeds, "results": rows, "details": details}
    out = SETTINGS.log_dir / f"ablation-{stamp}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    out.with_suffix(".md").write_text(to_markdown(report))
    report["files"] = [str(out.with_suffix(".md").relative_to(ROOT)), str(out.with_suffix(".json").relative_to(ROOT))]
    return report


def to_markdown(report: dict) -> str:
    lines = [f"# Ablation {report['generated']}", "",
             f"Stack: {report['stack']}  ",
             f"{report['cases']} cases x {report['repeats']} repeat(s), {report['memory_seeds']} records seeded in memory.", "",
             "| Profile | Accuracy | Memory-dependent cases | Unsafe errors | Consistency | Escalation rate |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in report["results"]:
        lines.append(f"| {r['profile']} | {r['accuracy']:.0%} | "
                     f"{'' if r['memory_cases'] is None else format(r['memory_cases'], '.0%')} | {r['unsafe_errors']} | "
                     f"{r['consistency']:.0%} | {r['escalation_rate']:.0%} |")
    misses = [d for d in report["details"] if not d["ok"] and d["profile"] == report["results"][0]["profile"]]
    if misses:
        lines += ["", f"Misses for '{report['results'][0]['profile']}':", ""]
        lines += [f"- {d['case']}: expected {d['expected']}, got {d['decisions']}" for d in misses]
    return "\n".join(lines) + "\n"
