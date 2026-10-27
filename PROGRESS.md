# Progress log (unification, 27 October 2026, Paris time)

Resume protocol: `pwd`, read this file, `tests.json`, `git log --oneline -20`, run `python -m pytest -q` and `python run.py steward-demo`, then continue at "Next action".

## 18:12 Phase 0, inventory
- Mac linked at 18:12, dropped at 18:18, back at 18:20 (it drops often). Teammates' repo fetched: 27 commits, last 18:09; their tests: 92 passed, 48 subtests (run here in SAMPLE_MODE). Steward: 43 passed, mcp_smoke PASS, H-MEM conformance 13/13, steward-demo runs.
- Push to the shared repo refused for this session (GitHub App not installed on `abouchet109-del`): `unify` will be handed to Ryan as a git bundle to push from his Mac.
- Contradiction surfaced to Ryan at 18:20 (one message): the team plans an Atlas submission (freeze 22:30), Ryan's prompt plans Steward in the same repo. Waiting for "envoyé" and "ok licence". Work continues on what does not depend on him.
- `docs/INVENTORY.md` written.

## 18:27 Phase 1, skills
- 5 skills vendored from obra/superpowers @ 2ce8aa1 into `.claude/skills/`; `docs/SKILLS.md` written. `impeccable`, `emil-design-eng`, `webapp-testing` do not exist in the trusted sources: skipped.

## Next action
- Write `docs/ARCHITECTURE.md`, launch `architect-reviewer`, write `docs/PLAN.md` and `tests.json`, then build `unify` (git merge of both histories, `agent/` -> `atlas/`).

## 18:45 Phase 2 and 3, architecture and plan
- `docs/ARCHITECTURE.md`, `docs/PLAN.md`, `tests.json`, `.claude/agents/` (7) written. Architect review round 1 at 18:55: FAIL (1 blocker, 5 majors): all fixed in `57c2a56`; answers in the document's review log.

## 19:00 Phase 4, build on `unify` (clone of the shared repo, /home/claude/abouchet109-del/hackathon-genai-public)
- `35c18ee` merge of both histories; `d81f26f` agent/ -> atlas/, docs -> docs/atlas/, bridge imports atlas; `57c2a56` review fixes + examples + traces + server tests; `bbc39a3` Zetaris source 3 as a jsDelivr REST table; `f482b03` CI, CONTRIBUTING, PRIOR_WORK, SPONSORS, metadata; `1ba1ba8` README, CLAUDE.md, smoke test. 118 tests pass; demo, MCP smoke and examples check pass.
- Not done yet: MCP text mode (design rules section 12), trace viewer in the console, SUBMISSION.md, the bundle for Ryan, LICENSE line (Ryan), the real-stack run (team or Mac).
- Ryan has not answered the 18:20 message yet (team alignment, license).

## 19:30 Reviews answered, submission files complete
- `3d0acb4` text mode for MCP results and the CLI. Six review agents ran 18:50-19:05: architect round 2 FAIL (1 blocker, 5 majors), claims-auditor FAIL (2 majors), qa-runner PASS on a fresh clone (1 major: bare pytest red), brand FAIL (6 majors), ui FAIL (1 major), ux FAIL (4 majors).
- All blockers and majors fixed: `b50419d` (console loopback + operator checks, guard before the model, receipt ids, typed boundary, author-only answers, conftest), `65e49be` (policy scope, rulings restamped, trace viewer, escalation facts, text mode polish, console kit compliance), `fcb00f5` (labelled context, why/recall/brief text), `fe53c66` (conformance log, README/metadata/SPONSORS/PRIOR_WORK claims, fake token), then this commit (ARCHITECTURE review log, DECISIONS D31 applied + D33-D36, SUBMISSION.md, LICENSE line with the three names after Ryan's "ok licence").
- State: 124 tests (with or without SAMPLE_MODE), mcp_smoke PASS, make_examples --check OK, steward-demo runs, console checked with Playwright (every tab, a ruling with a policy, the trace dialog, 375 px). tests.json: 22 passing, 0 failing, 6 not started (R14-R17 real stack, R26 push, R28 Windows).
- Not re-run after the fixes: the review agents themselves (time); `tests/test_review_round2.py` covers the architect's points.

## 20:10 Merges, round 3, push attempts
- Merged the team's main twice (`9889b6b`: extractor/updater/controller/writer/manager/World Model/services; `903d1b2`: orchestrator, `POST /run` on 8080, Nemotron replay cache, D16-D17); their new files live in `atlas/` with `atlas.*` imports, their docs in `docs/atlas/`; `ATLAS_HMEM_URL` separates their H-MEM wrapper (8765) from Steward's (8787).
- `9cfb6b3` Zetaris quality rule in code (read-back counts vs CSVs, tested offline). `cdb0fad` architect round 3 (opus): blocker + 3 majors fixed (loopback compose, hard cases decided in code with masked evidence, alerts/seed under the lock, accountable console operator), 4 tests. Fresh clone of `cdb0fad`: 197 passed, 9 skipped; demo, smoke, examples OK.
- Push: `git push` from this session is refused (403: the Claude GitHub App is not installed on Alexandre's account; the GitHub API confirms Ryan has push rights). Ryan ran `push-unify.sh`: the Mac is on `unify` but has no GitHub credential, so the push step failed. Prepared: `~/open-agent-hack/_transport/import-bundle.yml` (a workflow on a `transport` branch that turns an uploaded bundle into `unify`), to be uploaded through Ryan's GitHub session in Chrome; the Mac and the Chrome extension dropped at 20:00.
- Session B/C (Ryan's plan of 19:20): not seen yet (`~/steward-lanes/` absent); Project docs `contexte/04` and `06` rewritten for them.

## 20:35 unify is on GitHub
- Push path found: branch `transport` (created from Ryan's GitHub session in Chrome) + `unify.bundle` uploaded through the web UI + `.github/workflows/import-bundle.yml` on that branch, which fetches the bundle and pushes `refs/heads/unify` (fast-forward). First run failed (an App token cannot create workflow files), fixed by carrying the CI workflow at `docs/ci-tests.yml` and restoring `.github/workflows/tests.yml` on `unify` from Ryan's session (`30f1a30`). `unify` = `d61d06d` on GitHub at 20:33.
- CI run 40568677619 on `unify`: pytest in SAMPLE_MODE on ubuntu-latest and windows-latest, H-MEM conformance: all green.
- `main` untouched; Ryan's go awaited for the merge (diff summary sent 20:20).

## 21:35 Final checks before the freeze
- `unify` = `d9a1707` on GitHub (transport run 40578219363). Fresh clone **from GitHub** of that commit, judge commands as written in the README: pip install OK, `steward-demo` exit 0, `pytest` 197 passed / 9 skipped / 48 subtests in 13 s, `mcp_smoke` PASS, `make_examples --check` OK; 35 seconds end to end. Only `scripts/after-zetaris.sh` changed since CI run 40568677619, so that run still covers the Python code.
- Relative links in the team's documents moved to `docs/atlas/` (19 broken by the move) fixed; a link checker over the 53 markdown files finds 0 broken. `docs/atlas/README.md.orig` (a merge leftover) is left for Ryan to delete: no deletion without his word.
- Mac unchanged (`~/open-agent-hack` at 9889b6b, Zetaris log of 12:49, no `_lane-b/`): the real-stack run has not happened; README keeps `UNKNOWN` for Nemotron. `main` untouched, Ryan's go awaited.

## 21:55 Demo path checked end to end, small fixes
- On the fresh clone, through the console's own door (`/api/remember`, seeded policies): a trade-show booking entered as a **fact** is stored as shared knowledge (S11) whatever the amount; as a **decision**, 11,800 EUR is stored citing the CEO policy and 15,000 EUR escalates (S05); the CEO's price change supersedes as a decision (S07) and is clarified first as a fact (S10); Julie's 19 EUR mention clarifies; injection quarantines; password + key redact; `whats_new` relays `~~29~~ **35**`. Playwright on the console: 6 tabs, 0 errors, 375 px clean.
- Fixes pushed: `a277f3a` hint under the Kind selector (the form already starts on decision), `c21ab2f` the `remember` tool description says what a decision is + README known limit, `e4bd4de` clone commands name `-b unify` (a plain clone lands on the old `main` where `run.py` does not exist), `72955a5`/`afcac7a` video script (kind = decision, prime Karim's cursor). `POST /run` is the harness door: no journal, no policies; the console and MCP are the product doors.
- `unify` = `c21ab2f` on GitHub at 21:52 (`afcac7a` pending in the next bundle). Mac still at 9889b6b, no real-stack run, no `_lane-b/`; no word from Ryan since 20:10.

## Next action
- Each new commit: `git bundle create /mnt/user-data/uploads/unify.bundle unify`, upload to `transport` via Chrome, wait for the import run. If `logs/steward-demo-real.json` appears on the Mac: read it, copy a Nemotron trace into `logs/samples/`, replace the README's `UNKNOWN`, update R14-R16. Feature freeze 23:15 (docs only after that), final report by 23:45, vault note.
