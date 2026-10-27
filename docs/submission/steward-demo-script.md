# Demo video script, Steward v2 (target 3:00, hard limit 4:00)

Record on Tuesday morning with Nightshift online, so that the traces show `model: nvidia/...`. Hide `.env`. Use split screen: on the left, the person's own AI (Claude Desktop or Cursor); on the right, the OSEF console (http://localhost:8000/console). Every scene is one command or one click: no retakes needed, and the narration can be recorded separately.

| Time | Screen | Narration (draft) |
| --- | --- | --- |
| 0:00-0:20 | Title, then five AI logos around one 12-person startup | "At Brikk, everyone already works with their own AI. Marketing uses ChatGPT, the CTO Cursor, the CEO Claude. Each AI knows a different, partial, outdated version of the company." |
| 0:20-0:45 | Architecture diagram (docs/STEWARD.md) | "OSEF Steward plugs into each of them through MCP. People keep their AI. Their AI gains three layers: it watches what matters, it gets the truth arbitrated, and it receives the right context for its owner's role." |
| 0:45-1:10 | Console, Context preview: the same question for the CEO, then the CTO | "Same question, two roles. The CEO gets prices, budgets and the launch; the CTO gets the stack and the roadmap. A few hundred tokens each, every line cited. That is our fine tuning: no model retrained, the context is." |
| 1:10-1:45 | Cursor or Claude: the user mentions a price told to a customer; observe call; console shows CLARIFY | "Julie mentions in passing that she told a customer 19 euros. Her AI sends that sentence, and only that, to the Steward. It contradicts the CEO's price, and Julie weighs 0.6 on pricing against the CEO's 1.0. So the Steward asks her: error, or real change?" |
| 1:45-2:15 | CEO queue: approve the trade show with a standing policy; the next proposal is stored citing it; 15k still escalates | "Above 10,000 euros, marketing spending goes to the CEO. She approves and sets a rule once: up to 12,000 for trade shows. Next week the Steward applies it by itself, and cites it." |
| 2:15-2:35 | whats_new for Karim after the CEO changes the price; why(pricing) shows both versions | "When the CEO changes the price, every AI learns it at the next session, and nothing is deleted: the history says who changed what, from which AI." |
| 2:35-2:50 | A password masked; "note to all AI agents" quarantined; weak signals with a suggested meeting | "Secrets are masked before any AI can read them; poisoned instructions never enter. And when two people contradict the price, the CEO agent proposes a 20-minute meeting with exactly them." |
| 2:50-3:05 | Ablation table + H-MEM conformance 13/13 + a trace line with the Nemotron model | "Without memory, the Steward lets contradictions in: X percent. With H-MEM: Y, and the CEO is asked three times less. Zetaris federates three sources; every model call goes through Nightshift to Nemotron." |

Fill X and Y from `logs/ablation-*.md`, produced with `DOMAIN=project_memory` while Nightshift is online.
