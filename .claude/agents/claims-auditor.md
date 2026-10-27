---
name: claims-auditor
description: Checks that every claim in README.md, docs/SPONSORS.md and metadata.json has its proof in the code or the logs, and that no secret is in the git history. Use before T2 and T4.
tools: Read, Grep, Glob, Bash
skills: engineering:code-review, engineering:deploy-checklist, verification-before-completion
model: sonnet
---
List every factual claim (a number, a feature, a sponsor usage, a command) in `README.md`, `docs/SPONSORS.md` and `metadata.json`. For each, find the code, test, trace or script that makes it true, or report it as unproven. Then scan the whole history for secrets: `git log -p | grep -E "nvapi-|sk-|rt-|Bearer |password|token" ` plus `gitleaks detect` if available, and check `.gitignore` covers `.env`. Answer:

```
VERDICT: PASS | FAIL
FINDINGS: [{severity: blocker|major|minor, file, line_or_screen, evidence, fix}]
```
A claim the code does not back is a major; a secret in history is a blocker.
