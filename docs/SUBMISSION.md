# Submission: ready-to-paste answers and the video script

Open Agent Hackathon 2026 (GenAI.Works), Track 03 Reasoning Architecture. Team OSEF: Ryan Dalier-Dulys (lead, main contact, rdalierdulys@gmail.com), Adam Semlali, Alexandre Bouchet. Repository: https://github.com/abouchet109-del/Hackathon-GenAI-public (branch `main`; the unified work arrives through the `unify` branch). Deadline 27 October 2026, 23:45 UTC.

## Name

Steward

## One sentence

Steward is a company context layer over every AI the team already uses: through MCP it watches what matters in each person's own conversations, rules on what becomes the shared truth (sources weighted by role and domain; contradictions clarified with their author, then escalated to whoever has authority), and serves each person's AI the smallest cited context for their role and task.

## Short description

In a small company, everyone already works with a different AI: Claude, ChatGPT, Cursor, Gemini, Mistral. Each of those AIs knows a different, partial, outdated version of the company. Steward plugs into each of them through MCP; people keep the interface they like and their AI gains three layers. The watch layer sends relevant excerpts, never the conversation. The truth layer runs a prosecutor/judge pair of agents on Nemotron through Meterless Nightshift, reads the governance data through Zetaris (who leads what, budget limits, trust weights by role and domain) and the company record in Meterless H-MEM, and decides for each proposal: store, supersede an older decision (kept, never deleted), reject, redact, ask the author "error or real change?", escalate to the CEO, or quarantine an injection. The context layer composes, for each person's role and task, a cited context within a 1,500-token budget, what changed since their last session, the procedures of their role and the alerts that concern them. The CEO gets a queue, standing policies raised from her rulings, weak signals and suggested meetings. Demo company: Brikk, 12 people and an intern, all synthetic.

## Sponsor technology

- **Zetaris (DATA):** one SQL door over three sources, read on every arbitration and every context: Postgres `brikk` (org chart, trust weights role x domain, topics with owner and limits, rules, profiles, tasks), the finance REST API served by Steward (`GET /finance/budgets`, a Lightning REST table with a SchemaStore view), and the role procedures catalogue as a REST table on a pinned public URL; a Unified Semantic Layer `brikk_usl` spans them. Scripts: `scripts/zetaris/register_steward.sql` (21 statements), `run_steward_sql.py` (registers, then reads every table back against the CSVs). Scoring documents (sources, queries, quality rule, reflections): `docs/zetaris/`. Status: the recipe is the team's live-verified one for the Atlas corpus; the Brikk registration had not been run against a live Zetaris at the time of writing (README, "Known limits").
- **Meterless H-MEM (BUILD):** the company record. `hmem-service/server.ts` wraps the reference engine (Apache-2.0, vendored unchanged by `setup.sh`) and adds `supersedes` chains, `/list` by tag and persisted spaces. Confidence = the author's trust weight; provenance on every record; CEO policies as tagged records. Conformance suite 13/13 (`logs/samples/hmem-conformance.txt`).
- **Meterless Nightshift (POWER):** the only model provider (`127.0.0.1:8088/v1`, headers `meterless-app`, `meterless-scope: user`), three lanes: fast (extractor), deep (arbiter), judge (critic). The served model and the receipt id are read from Nightshift's answer and written on every trace line.
- **NVIDIA Nemotron:** pinned by exact id on the three lanes (`nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3-ultra-550b-a55b`). Status: the ids were verified by the team through Nightshift; no trace with a Nemotron model has been produced from this code yet (`UNKNOWN` in the README's evidence section).
- **Cursor:** the team's development environment and one of the two MCP clients of the demo (`docs/mcp/cursor-mcp.json`, the CTO); Claude Desktop is the other (the CEO).

## Prior work declaration

Everything written by the team dates from the event (from 22 October 2026). Third-party material: the Meterless H-MEM reference implementation and conformance suite (Apache-2.0, fetched by `hmem-service/setup.sh`, wrapped not modified), the Zetaris getting-started recipes (read, not vendored), the Archivo and Chivo Mono fonts (SIL OFL 1.1), five review skills from obra/superpowers (MIT, instructions only), PyPI and npm packages. Two codebases written by the team during the event were merged on 27 October (`docs/TEAM-AND-MERGE.md`); the git dates of the Steward commits record the import, not the writing. AI coding assistants were used; the team can explain every part. Full text: `docs/PRIOR_WORK.md`, `LICENSE`, `NOTICE`.

## What a judge can run in two minutes

```bash
git clone https://github.com/abouchet109-del/Hackathon-GenAI-public && cd Hackathon-GenAI-public
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
SAMPLE_MODE=true .venv/bin/python run.py steward-demo        # the 8-step scenario, one trace per arbitration in logs/
.venv/bin/python -m pytest -q                                 # 124 tests
.venv/bin/python scripts/mcp_smoke.py                         # a real MCP client: 16 tools, the resource, the prompt
SAMPLE_MODE=true .venv/bin/python run.py serve                # console at http://127.0.0.1:8000/console
```

## Video script (target 3:00, hard limit 4:00)

Record with Nightshift online so that the traces show `model: nvidia/...`; if it is offline, say so on screen (the console header says `LLM offline`). Hide `.env`. Split screen: left, a person's own AI (Claude Desktop or Cursor with the `steward` server configured); right, the console. Before recording: `STEWARD_SPACE=video STEWARD_SEED_POLICIES=true SAMPLE_MODE=true python run.py serve` (drop `SAMPLE_MODE` on the real stack), then open `http://127.0.0.1:8000/console`.

| Time | Screen | Command or click | Narration |
| --- | --- | --- | --- |
| 0:00–0:20 | Title card, then the console's Shared truth | — | "At Brikk, twelve people, twelve AIs: ChatGPT in marketing, Cursor for the CTO, Claude for the CEO. Each AI knows a different, partial, outdated version of the company. Steward is the layer that keeps the record straight." |
| 0:20–0:45 | Architecture (README diagram) | — | "Steward plugs into each AI through MCP. People keep their AI. It gains three layers: it watches what matters, every write is arbitrated, and it receives the right context for its owner's role." |
| 0:45–1:10 | Console, Context preview: Claire Morel (CEO) then Sami Haddad (CTO), task "the launch" | pick the member, Compose context | "Same question, two roles. The CEO gets prices, budgets and the launch; the CTO gets the stack and the roadmap. Under 1,500 tokens, every line cited. No model is retrained; the context is." |
| 1:10–1:45 | Left: Julie's AI mentions "I told Martin Plomberie the price is 19 EUR" → `observe`; right: Clarifications tab shows CLARIFY with the current record | in the AI: type the sentence; in the console: open Clarifications | "Julie mentions a price in passing. Her AI sends that sentence, only that, to Steward. It contradicts the CEO's price, and Julie weighs 0.6 on pricing against the CEO's 1.0. So Steward asks her first: error, or real change?" |
| 1:45–2:15 | Escalations tab: Inès's 11,500 EUR trade show; Approve once + Raise the policy "Marketing may commit up to 12,000 EUR per trade show"; then Simulate an AI: Tom, "Book a booth at Bois & Bati Lyon for 11,800 EUR" → STORED citing the policy; 15,000 EUR → ESCALATED | click Raise the policy, type, Approve once; Simulate an AI twice | "Above the limit, marketing spending goes to the CEO. She approves and sets the rule once. Next week Steward applies it by itself and cites it; above the ceiling, it still asks." |
| 2:15–2:35 | Left: the CEO's AI: "Pricing changes to 35 EUR per user per month from January" → SUPERSEDED; Karim's AI: `whats_new` shows ~~29~~ **35**; console: History dialog on Pricing | `remember` from Claire's AI; `whats_new` from Karim's | "When the CEO changes the price, every AI learns it at its next session, and nothing is deleted: the history says who changed what, from which AI, and Julie and Paul are alerted because their work relied on the old value." |
| 2:35–2:50 | Simulate an AI: a password and a key → REDACTED; "note to all AI agents: ignore previous instructions" → QUARANTINED; Escalations: weak signals with a suggested meeting | two Simulate runs | "Secrets are masked before any AI can read them. Instructions aimed at AIs are isolated in code, before any model sees them. And when two people contradict the price, the CEO agent proposes a twenty-minute meeting with exactly them." |
| 2:50–3:05 | Terminal: the verdict's trace in the console dialog (model line), `logs/samples/hmem-conformance.txt`, the ablation table from `logs/ablation-*.md` | click the Trace chip | "Every step is traced with the model that answered through Nightshift. Memory is Meterless H-MEM, conformance thirteen out of thirteen; governance data comes through Zetaris. Without memory, Steward lets contradictions in; with it, none, and the CEO is asked three times less often." |

Figures to say on screen only if they come from a run on the real stack: the Nemotron accuracy (README, "Evidence": `UNKNOWN` until `run.py ablation` has run with Nightshift). The offline figures (34 cases: 56 % → 100 %, 3 unsafe → 0, CEO asked 26 % → 9 %) measure consistency with the rules, and the video must say so if it quotes them.

## Links to fill before submitting

- Video: [YouTube or Drive link]
- Deck: [PDF] (outline in `docs/submission/deck-outline.md`)
- Repository: https://github.com/abouchet109-del/Hackathon-GenAI-public
