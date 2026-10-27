# Three reflections on the Unified Semantic Layer

Written on 27 October by the team, from what the code does; where a figure is an estimate it says so.

## a. Time saved versus the hand-coded approach (and what we hand-coded anyway)

What a USL replaced for us: three connectors (a Postgres driver, a REST client with JSON flattening, a file/catalogue reader) plus the glue that joins them, each with its own error handling, retries and credentials. With Zetaris the three sources are 21 SQL statements (`scripts/zetaris/register_steward.sql`), one runner that sends them one per request, and every read in Steward is a `SELECT` through one door (`app/adapters/zetaris.py::ZetarisClient.run_sql`, under a hundred lines for the whole adapter, retries included). The code that reads governance data does not know which system it comes from: `domain.yaml` maps a logical table (`members`, `finance`, `procedures`) to a physical name, and `ZETARIS_USE_USL=true` swaps the physical names for the USL ones without touching a line of logic.

The comparison we can make honestly, because we built it: `SAMPLE_MODE` is the hand-coded path. It loads the same CSVs into SQLite (`SampleData`, about twenty lines) so that the same SQL runs offline. It took under an hour and it only works because every source is a flat file we own. The moment source 2 became a live API (budgets served by a finance tool) and source 3 a document store, the hand-coded path would have needed a flattening step per source and a join layer; the SchemaStore views (`LATERAL VIEW explode`) did that in two statements each. Estimate for a real company with those three systems: a day of connector code and a recurring maintenance cost per source, against half a day of DDL once. The honest counterweight: that half day was spent learning the Lightning SQL dialect (one statement per request, `COALESCE` on NOT NULL columns before `ACTIVATE USL TABLE`, REST tables that need a public URL), and the registration has not run live from this code yet.

## b. Would a USL help in our own work?

Yes for one of our two projects, no for the other.

Steward itself is the case where it helps: the product's promise is that each person's AI gets governance facts it should never carry in its prompt (who weighs what, who owns a topic, what the budget says). Those facts are spread across HR, finance and a document space in any company; a USL is the only way to keep one SQL contract while the systems behind it change. The feature that profits most is the CEO's weak signals (`context.py::weak_signals`): "two open topics on the same theme while the owning department is at 88 % of its budget" is one join across the org chart, the journal and the finance API. Estimated saving if Brikk were real and its finance tool were, say, Pennylane: the connector plus the join layer, about two days, and every budget change becomes visible without a deploy.

The Atlas corpus (the team's project-coordination case) is where it helps less: its sources are messages, tickets and meeting notes, text with little structure. Zetaris served them as REST tables fine (the team reports registering them live on 27 October with `scripts/register_zetaris.py`), but the value sat in the extraction and the arbitration, not in the join; a plain file loader would have done as much for that part. The lesson we keep: a USL pays when the questions are relational (who, how much, which limit) and the sources are owned by different tools; it pays little when the work is reading prose.

## c. How to make the USL stronger (written as a PM)

Three product changes, in order of value for a team like ours.

1. **Row-level provenance in query results.** Steward's trust model needs to say which source a figure came from and when it was read ("Budget read from the finance API at 21:34, not re-checked"). Today we add that in code around the read. If a USL query could return, per row, the source table and the fetch time, the Limits line of every Steward verdict would come for free and the audit trail would be the engine's, not ours. Mock-up: `SELECT ..., _source, _fetched_at FROM brikk_usl.department`.
2. **A quality rule as a first-class object.** Our rule (read every table back, compare the count with the system of record) lives in a Python script. A `CREATE QUALITY RULE member_count AS SELECT COUNT(*) FROM brikk_usl.member EXPECT 13` that runs after each registration, with its result queryable, would make the quality state part of the USL rather than a script next to it; a UI badge per USL table ("verified 21:34, 13 rows") would answer the jury's question in one look.
3. **Private file sources without cloud storage.** Our third source is a document catalogue. To register it we had to publish the JSON on a public URL pinned on a commit (a FILESTORE needs S3-compatible storage). A local-folder or SFTP source type for the single-node platform would have let the company drive stay private, which is where role procedures actually live.

Smaller items: `--dry-run` for the SQL editor API (we wrote our own), and a compile error that names the column when a `COMPILE USL` fails on a NOT NULL column (today the rule "wrap NOT NULL columns in `COALESCE`" has to be known in advance from the getting-started guide).
