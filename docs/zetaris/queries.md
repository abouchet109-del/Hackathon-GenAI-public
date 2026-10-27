# Exploratory queries, per source, and the USL queries

Every query is one Steward's code runs (or the exploratory form of it). **Executed on the SQLite copy of the same tables (`SAMPLE_MODE`, `app/adapters/zetaris.py::SampleData`, 27 October 20:50 Paris)**: the outputs below are real outputs of that execution. On Zetaris the same statements run through `POST /sql-editor/sqls/run` with the schema-qualified names shown (`brikk.*`, `brikk_api.finance`, `brikk_drive.procedures`, `lightning.metastore.osef.brikk_usl.*`); they are marked `NOT RUN ON ZETARIS` until the live registration happens (see README).

Reproduce: `SAMPLE_MODE=true python - <<'EOF'` with `SampleData(Path('domains/project_memory/data'), 'brikk').conn.execute(sql)`, or run `scripts/zetaris/run_steward_sql.py --verify-only` once Zetaris answers.


## Source 1, Postgres `brikk` (org chart, trust, topics, rules)

### S1-1 — who is the author, what is their level

```sql
SELECT member_id, name, department, role, ai_tool, level FROM brikk.members WHERE name = 'Julie Caron'
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| member_id | name | department | role | ai_tool | level |
| --- | --- | --- | --- | --- | --- |
| m09 | Julie Caron | sales | Account executive | ChatGPT | member |

### S1-2 — who owns the topic, its limit

```sql
SELECT topic, owner_department, singleton, budget_limit_eur FROM brikk.topics WHERE topic = 'marketing_spend'
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| topic | owner_department | singleton | budget_limit_eur |
| --- | --- | --- | --- |
| marketing_spend | marketing | no | 10000 |

### S1-3 — trust weights by level

```sql
SELECT level, own_domain_weight, other_domain_weight FROM brikk.trust
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| level | own_domain_weight | other_domain_weight |
| --- | --- | --- |
| ceo | 1.0 | 1.0 |
| lead | 0.9 | 0.4 |
| member | 0.6 | 0.25 |
| intern | 0.3 | 0.1 |

### S1-4 — rules that apply to a decision

```sql
SELECT rule_id, decision FROM brikk.rules WHERE item_type IN ('decision','any') ORDER BY rule_id
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| rule_id | decision |
| --- | --- |
| S01 | quarantine |
| S02 | redact |
| S04 | reject |
| S05 | escalate |
| S06 | clarify |
| S07 | supersede |
| S08 | store |
| S09 | escalate |


## Source 2, the finance REST API (`brikk_api.finance`)

### S2-1 — budget ratios per department

```sql
SELECT department, period, budget_eur, committed_eur, ROUND(CAST(committed_eur AS REAL)/CAST(budget_eur AS REAL)*100) AS pct FROM brikk.finance ORDER BY pct DESC
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| department | period | budget_eur | committed_eur | pct |
| --- | --- | --- | --- | --- |
| ops | 2026-Q4 | 4000 | 3900 | 98.0 |
| marketing | 2026-Q4 | 30000 | 26500 | 88.0 |
| tech | 2026-Q4 | 18000 | 9100 | 51.0 |
| sales | 2026-Q4 | 12000 | 4200 | 35.0 |
| executive | 2026-Q4 | 20000 | 7000 | 35.0 |
| product | 2026-Q4 | 6000 | 1500 | 25.0 |
| finance | 2026-Q4 | 5000 | 1200 | 24.0 |

### S2-2 — departments at 85 % or more

```sql
SELECT department, committed_eur, budget_eur FROM brikk.finance WHERE CAST(committed_eur AS REAL)/CAST(budget_eur AS REAL) >= 0.85
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| department | committed_eur | budget_eur |
| --- | --- | --- |
| marketing | 26500 | 30000 |
| ops | 3900 | 4000 |


## Source 3, the company catalogue (`brikk_drive.procedures`)

### S3-1 — procedures of a department

```sql
SELECT procedure_id, level, when_to_use FROM brikk.procedures WHERE department IN ('sales','any')
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| procedure_id | level | when_to_use |
| --- | --- | --- |
| P01 | any | grant a discount |
| P04 | intern | state a figure |

### S3-2 — count of procedures

```sql
SELECT COUNT(*) AS n FROM brikk.procedures
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| n |
| --- |
| 5 |


## The USL `brikk_usl` (joins across sources)

### USL-1 — members with the budget of their department (join across sources 1 and 2)

```sql
SELECT m.name, m.department, f.committed_eur, f.budget_eur FROM brikk.members m JOIN brikk.finance f ON f.department = m.department WHERE m.level = 'lead' ORDER BY m.department
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| name | department | committed_eur | budget_eur |
| --- | --- | --- | --- |
| Nadia Benali | finance | 1200 | 5000 |
| Inès Roux | marketing | 26500 | 30000 |
| Yanis Moreau | ops | 3900 | 4000 |
| Hugo Lambert | product | 1500 | 6000 |
| Paul Lefèvre | sales | 4200 | 12000 |
| Sami Haddad | tech | 9100 | 18000 |

### USL-2 — topics whose owner department is over 85 % of budget

```sql
SELECT t.topic, t.owner_department FROM brikk.topics t JOIN brikk.finance f ON f.department = t.owner_department WHERE CAST(f.committed_eur AS REAL)/CAST(f.budget_eur AS REAL) >= 0.85
```

Output (SQLite copy; `NOT RUN ON ZETARIS`):

| topic | owner_department |
| --- | --- |
| brand | marketing |
| marketing_spend | marketing |
| support_policy | ops |


### USL-3 — the cross-source check of the registration script (who is near their budget), through the USL

```sql
SELECT m.name, d.department, d.committed_eur, d.budget_eur
FROM lightning.metastore.osef.brikk_usl.member m
JOIN lightning.metastore.osef.brikk_usl.department d ON d.department = m.department
WHERE m.level IN ('lead', 'ceo')
```

`NOT RUN ON ZETARIS` (the USL names only exist there). The same join on the SQLite copy is USL-1 above.

## What proves the USL is active, once registered

1. `SELECT COUNT(*) FROM lightning.metastore.osef.brikk_usl.member` returns 13 (the read-back check of `run_steward_sql.py --verify-only` compares it with `members.csv`).
2. `ZETARIS_USE_USL=true python run.py steward-demo` runs the whole scenario through the USL tables (`domain.yaml: zetaris_usl_tables`) and every trace line of the Researcher names them.
3. USL-3 returns the leads with their department's budget: two sources (Postgres and the REST API) in one answer.
