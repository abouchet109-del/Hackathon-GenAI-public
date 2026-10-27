# Trace samples from real runs

One JSONL file per arbitration, copied from `logs/` after a real execution (`python run.py steward-demo` and
`python scripts/make_examples.py`). One line per agent action: `agent`, `action`, `target`, `model` (the model that
actually answered, read from Nightshift's receipt), `confidence`, `retries`, `status`, `cached`.

These samples were produced in the build container **without Nightshift**: no model was called, so `model` is
`null` on every line and the `run_started` line's stack says `llm: offline (replay + deterministic fallback)`,
`data: sample-sqlite`, `memory: local-fallback`. A run on a machine with Nightshift writes `nvidia/nemotron-...`
in the `model` field of the Decider and Critic lines; such a trace is added here once the team has run it
(README, "Real stack"). Nothing in these files was written by hand.
