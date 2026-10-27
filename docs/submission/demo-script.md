# Demo video script (target 3:00, hard limit 4:00)

Record the real runs. Hide `.env`. Terminal font large. Name: `OAH2026-OSEF-ReasoningArchitecture-Demo.mp4`.

| Time | Screen | Narration (draft) |
| --- | --- | --- |
| 0:00-0:20 | Title slide, then an inbox mixing bills, an aid request and a phishing mail | "Our entry is for Reasoning Architecture. Students drown in admin mail: bills, aid paperwork, school forms, and scams that look exactly like them. One wrong click costs money." |
| 0:20-0:45 | Architecture diagram from the README | "Our agent decides what to do with each item and prepares the action. The owner approves in one click. Every block that makes it reliable can be switched off and measured." |
| 0:45-1:25 | Run example_2 (CAF refund scam): trace scrolling | "Intake flags the credential request. The Researcher asks Zetaris whether the sender is verified: it is not. The Decider proposes block_scam, the Critic checks it, done." |
| 1:25-2:05 | `python run.py demo-memory` | "Session one: an 86-euro EDF bill is above the auto-pay limit, so the agent asks. The owner says: I always pay EDF up to 120. Session three: a new 104-euro EDF bill. The agent pays it and cites the correction stored in Meterless H-MEM. A 142-euro bill still escalates." |
| 2:05-2:35 | Run example_3 (injection inside a real invoice): Critic rejecting | "This invoice hides an instruction to send the card number. The guard flags it; the Critic refuses any action that moves money; the item is blocked." |
| 2:35-3:00 | Ablation table + `npm run conformance` 13/13 + a trace line showing the Nemotron model | "Model alone: X percent. With Zetaris rules: Y. With H-MEM memory: Z on the cases that depend on the owner's history. Every model call goes through Nightshift to Nemotron, logged per call." |

Fill X, Y, Z from `logs/ablation-*.md` produced with Nightshift online and `--repeats 3`.
