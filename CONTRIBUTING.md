# Contributing

Steward is built by team OSEF (Ryan Dalier-Dulys, Adam Semlali, Alexandre Bouchet). The rules below are the ones we hold each other to; `CLAUDE.md` is the same list for the AI sessions that work in this repository.

- **Start green.** `SAMPLE_MODE=true python -m pytest -q` passes before you touch anything. It must still pass before you commit.
- **Small commits, in English**, one task each, with a message that says what changes and why. No `push --force`, no rewriting of published history.
- **Tests before fixes.** A bug gets a failing test first. Never weaken or delete a test to make it pass; never edit `evaluation/` or `domains/*/cases.jsonl` expected results to match an output.
- **No secrets, ever.** Keys and tokens live in `.env` (ignored) or in Nightshift. `.env.example` holds placeholders only. Run `git log -p | grep -E "nvapi-|sk-|Bearer "` before you push if in doubt.
- **The code decides, the model qualifies.** Authority, limits, secrets and injection are hard checks in code (`domains/project_memory/logic.py`, `atlas/decisions.py`); prompts are versioned and reviewed like code.
- **One writer per memory.** Anything that writes to H-MEM, the journal, the inboxes or the progress store goes through `app/steward.py` and its lock.
- **No hard-coded demo paths.** The scenario, the examples and the traces are produced by running the code (`scripts/make_examples.py`, `logs/samples/`).
- **Honest docs.** The README says what the code does today; limits are listed, not hidden. Decisions go to `docs/DECISIONS.md` as new lines, never by erasing old ones.
- **Design.** Visible surfaces use the Steward kit (`app/static/brand/`): tokens `--st-*`, classes `st-`, no inline styles, no invented colours or fonts.

Run the review agents in `.claude/agents/` before a merge into `main`: `qa-runner` on a fresh clone, `claims-auditor` on the README, `brand-consistency`, `ui-reviewer` and `ux-reviewer` after an interface change.
