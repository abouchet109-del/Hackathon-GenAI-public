# Sponsor technology explanation (draft for the submission form)

**Zetaris (data layer).** Our operational data (verified senders, decision rules, the owner's profile) lives in a Postgres database registered in Zetaris as the `osef` datasource. For every item, the Researcher agent sends three SQL statements to the Zetaris REST API (`/sql-editor/sqls/run`): sender verification, the rules applicable to the item type, and the owner's auto-pay limit. Remove Zetaris and the agent has no grounds to pay, block or ask. Queries and row counts appear in every trace.

**Meterless (engine: H-MEM).** Owner corrections are stored as H-MEM records with a mandatory source (`user_correction`), a confidence, tags and an append-only ledger. Before each decision the MemoryKeeper recalls the top records; the Decider must cite the memory it uses, and the Critic rejects citations that do not exist. We run the Meterless H-MEM reference implementation behind a small local HTTP service; `npm run conformance` passes the official suite (13/13). Feature it powers: a correction given once changes the next similar decision (`python run.py demo-memory`).

**Meterless Nightshift (AI provider).** All model calls use Nightshift's OpenAI-compatible endpoint with `meterless-app` and `meterless-scope` headers, over three lanes: fast, deep (Decider) and judge (Critic).

**NVIDIA.** Nemotron models are pinned on the deep and judge lanes in Nightshift; each trace event records the model that answered.

**Cursor.** The project was developed in Cursor.

**What is unique.** We use the sponsor stack to make reliability measurable: the same 30 labelled cases run with and without Zetaris rules, H-MEM memory and the Critic, and the ablation report shows what each block adds.
