# Slide deck outline (8 required points)

1. **Problem and users.** Students and young workers: one inbox, five kinds of admin mail, phishing that copies real senders. Cost of a wrong action.
2. **Solution.** A decision agent that prepares the action and cites its evidence; the owner approves or corrects; corrections become memory.
3. **Agent workflow.** The README diagram. Highlight the Critic loop (max 2 revisions, then escalate) and the correction loop into H-MEM.
4. **Technical stack.** Python, FastAPI, Zetaris (Postgres datasource), Meterless H-MEM (Node service around the reference engine), Nightshift lanes with Nemotron, Docker.
5. **How Zetaris and Meterless were used.** Researcher's three SQL questions; H-MEM records with source, confidence and ledger; conformance 13/13; Nightshift as the only model provider.
6. **What is unique.** Reliability is measured, not claimed: ablation table per block; memory changes decisions and the trace shows which correction was used; hard checks that a model cannot argue with.
7. **Product visuals.** Output JSON for the scam and the EDF cases; a trace excerpt; the ablation table.
8. **Future enhancements.** Real inbox connector with read-only scope; Scout Intent contracts before any action; World Model of senders and recurring bills; owner-tunable risk thresholds.
