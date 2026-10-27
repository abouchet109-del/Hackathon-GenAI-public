# Skills used by the review agents

Session skills (already available in Claude Code / claude.ai for this team) and skills vendored into `.claude/skills/` from a trusted source, so that the agents in `.claude/agents/` can load them. Vendored skills are plain Markdown instructions; they run nothing by themselves.

| Skill | Source | Commit | Used by | Why |
| --- | --- | --- | --- | --- |
| `engineering:architecture`, `engineering:system-design` | session (Anthropic engineering plugin) | — | `architect-reviewer` | component boundaries, failure points, trade-off framing |
| `engineering:code-review` | session | — | `architect-reviewer`, `claims-auditor` | reading a diff for correctness and doc/code gaps |
| `engineering:debug` | session | — | `debugger` | reproduce, isolate, fix |
| `engineering:testing-strategy` | session | — | `qa-runner` | what a fresh-clone run must cover |
| `engineering:deploy-checklist` | session | — | `qa-runner`, `claims-auditor` | pre-release checks (secrets, env, docs) |
| `design:design-critique`, `design:accessibility-review`, `design:ux-copy` | session (Anthropic design plugin) | — | `ui-reviewer`, `ux-reviewer`, `brand-consistency` | hierarchy, WCAG AA, copy clarity |
| `anthropic-skills:frontend-design` | session | — | `ui-reviewer` | layout and state quality |
| `anthropic-skills:mcp-builder` | session | — | `architect-reviewer` | MCP server conventions (tool annotations, resources, prompts) |
| `systematic-debugging` | github.com/obra/superpowers | `2ce8aa1` | `debugger` | error first, hypothesis, smallest failing test |
| `test-driven-development` | github.com/obra/superpowers | `2ce8aa1` | `debugger` | failing test before the fix |
| `verification-before-completion` | github.com/obra/superpowers | `2ce8aa1` | all reviewers | a verdict needs a command and its output |
| `dispatching-parallel-agents` | github.com/obra/superpowers | `2ce8aa1` | orchestrator | independent reviews in parallel |
| `requesting-code-review` | github.com/obra/superpowers | `2ce8aa1` | orchestrator | how to brief a reviewer without leaking conclusions |

Not installed (no such skill in the trusted sources on 27/10/2026): `impeccable`, `emil-design-eng`, `webapp-testing`. The `ux-reviewer` uses Playwright directly instead.
