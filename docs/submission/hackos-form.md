# HackOS submission form: ready-to-paste answers

Track: **03 Reasoning Architecture**. Team: **OSEF**. Fill the bracketed parts on Tuesday.

## Project name
Steward

## One-sentence description
Steward is a company context layer for every AI: through MCP it watches what matters in each person's own AI conversations, rules on what becomes the team's shared truth (sources weighted by role and domain, contradictions clarified then escalated), and serves each person the right context for their role and task.

## Description (short)
In a small company, everyone already works with a different AI, and each of those AIs knows a different, partial, outdated version of the company. Steward plugs into Claude, Cursor, ChatGPT and others through MCP. People keep their interface, and their AI gains three layers. The watch layer sends relevant excerpts. The truth layer runs a prosecutor/judge pair of agents over Nemotron, reads governance data through Zetaris (who leads what, budget limits, trust weights by role and domain), and decides for each proposal whether to store it, supersede an older decision (kept, never deleted, in Meterless H-MEM), reject it, redact it, ask its author "error or real change?", escalate it to the CEO, or quarantine it as an injection. The context layer gives each person's AI the smallest useful, cited context for their role and task. An ablation on 34 labelled cases measures what memory adds: without H-MEM, contradictions enter the record. With it, they don't, and the CEO is asked three times less often.

## Links
- Repository: https://github.com/rdalierdulys-arch/[repository]
- Video: [YouTube or Drive link, 1 to 4 min]
- Deck: [PDF exported from the deck]

## Team
| Name | HackOS email | GitHub | Role |
| --- | --- | --- | --- |
| Ryan Dalier-Dulys | rdalierdulys@gmail.com | rdalierdulys-arch | Lead, architecture and build (main contact) |
| Adam Semlali | [email] | [github] | Product vision (department agents, CEO agent), deck review |
| Alexandre Bouchet | [email] | [github] | Product vision (organisation memory), data framing |

## Sponsor technology (short version; long version in docs/STEWARD.md and README)
- **Zetaris:** one SQL door over three sources: Postgres org chart and trust weights, the finance REST API, and an S3 drive with role procedures. A Unified Semantic Layer spans them. Every arbitration reads who the author is, how much they weigh, who owns the topic and its limits.
- **Meterless H-MEM:** the company record. It holds versioned decisions (`supersedes`; replaced, never deleted), provenance, confidence set to the author's trust weight, CEO policies and the trust ledger. Conformance 13/13.
- **Meterless Nightshift:** primary AI provider, with three lanes: extraction, arbitration, judgment.
- **NVIDIA Nemotron:** pinned on the three lanes; the model is logged on every trace line.
- **Cursor:** development environment, and one of the MCP clients in the demo.

## Pre-existing work declaration
The code was written during the event (from 22 October 2026). Third-party components:
- the Meterless H-MEM reference implementation and conformance suite (Apache-2.0), vendored unchanged in `hmem-service/vendor/` and wrapped by our `hmem-service/server.ts`;
- open-source libraries installed from PyPI and npm (FastAPI, openai, mcp, pyyaml, requests, tsx).

AI coding assistants were used to write code; the team can explain every part.

## Limitations to state honestly
- The offline ablation shows 100% because the rules and the cases were written together. The Nemotron run gives [__% accuracy, __% consistency over 3 runs].
- The watch layer relies on each client AI following the MCP server instructions.
- Identity is declared in the client configuration; production would use OAuth.
