-- OSEF Steward: three Brikk sources behind one SQL door, plus a Unified Semantic Layer over them.
-- Run ONE statement per request (no trailing semicolons), e.g. python scripts/zetaris/run_steward_sql.py
-- Syntax from the Zetaris getting-started repo (docs/guides/zetaris-lightning-sql-commands.md and recipes).
-- NOT yet run live. Untested in that repo: a JDBC datasource, a local MinIO, host.docker.internal.
-- Before running: docker compose up -d brikk-db drive drive-init, and `python run.py serve` (finance API on :8000).

-- ===== Source 1/3: Postgres "brikk" (org chart, trust, topics, rules, profiles) =====
CREATE DATASOURCE brikk DESCRIBE BY "Brikk org data, OSEF Steward" OPTIONS (
  jdbcdriver "org.postgresql.Driver",
  jdbcurl "jdbc:postgresql://host.docker.internal:5434/brikk",
  username "osef",
  password "osef_local_only",
  fetchsize "1000"
)
REGISTER DATASOURCE TABLES FROM brikk
SELECT name, department, level FROM brikk.members

-- ===== Source 2/3: the Brikk finance REST API (served by the app: GET /finance/budgets) =====
CREATE LIGHTNING DATABASE BRIKK_FINANCE_REST DESCRIBE BY "Brikk finance API"
CREATE SCHEMASTORE CONTAINER brikk_api
CREATE LIGHTNING REST TABLE budgets_raw FROM BRIKK_FINANCE_REST REQUEST(
    endpoint "http://host.docker.internal:8000/finance/budgets",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
) BODY ()
CREATE SCHEMASTORE VIEW finance WITH CONTAINER brikk_api AS
SELECT b.department, b.period, b.budget_eur, b.committed_eur, b.note
FROM brikk_finance_rest.budgets_raw
LATERAL VIEW explode(budgets) AS b
SELECT department, budget_eur, committed_eur FROM brikk_api.finance

-- ===== Source 3/3: the company catalogue (role procedures), a JSON file on the public repository =====
-- Served by jsDelivr, pinned on a commit (run_steward_sql.py fills {{SOURCE_REPO}} and {{COMMIT}}): the same
-- recipe the team verified live on 27/10 for the Atlas sources. A FILESTORE on S3-compatible storage is the
-- alternative, in register_steward_minio.sql.
CREATE LIGHTNING DATABASE BRIKK_CATALOGUE DESCRIBE BY "Brikk company catalogue"
CREATE SCHEMASTORE CONTAINER brikk_drive
CREATE LIGHTNING REST TABLE procedures_raw FROM BRIKK_CATALOGUE REQUEST(
    endpoint "https://cdn.jsdelivr.net/gh/{{SOURCE_REPO}}@{{COMMIT}}/domains/project_memory/data/procedures.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
) BODY ()
CREATE SCHEMASTORE VIEW procedures WITH CONTAINER brikk_drive AS
SELECT p.procedure_id, p.department, p.level, p.when_to_use, p.steps
FROM brikk_catalogue.procedures_raw
LATERAL VIEW explode(records) AS p
SELECT procedure_id, department, when_to_use FROM brikk_drive.procedures

-- ===== Unified Semantic Layer over the three sources (optional: set ZETARIS_USE_USL=true) =====
CREATE NAMESPACE IF NOT EXISTS lightning.metastore
CREATE NAMESPACE IF NOT EXISTS lightning.metastore.osef
-- The next statement is ONE request (it contains its own semicolons).
COMPILE USL IF NOT EXISTS brikk_usl DEPLOY NAMESPACE lightning.metastore.osef DDL
CREATE TABLE department (
    department varchar(40) NOT NULL PRIMARY KEY,
    period varchar(20), budget_eur double, committed_eur double, note varchar(300)
);
CREATE TABLE member (
    member_id varchar(10) NOT NULL PRIMARY KEY,
    name varchar(100) NOT NULL, department varchar(40) NOT NULL FOREIGN KEY REFERENCES department(department),
    role varchar(100), ai_tool varchar(40), level varchar(20)
);
CREATE TABLE topic (
    topic varchar(40) NOT NULL PRIMARY KEY,
    owner_department varchar(40) NOT NULL FOREIGN KEY REFERENCES department(department),
    singleton varchar(5), budget_limit_eur varchar(20), description varchar(200), keywords varchar(400)
);
CREATE TABLE procedure (
    procedure_id varchar(10) NOT NULL PRIMARY KEY,
    department varchar(40), level varchar(20), when_to_use varchar(200), steps varchar(1000)
)
ACTIVATE USL TABLE lightning.metastore.osef.brikk_usl.department AS
SELECT COALESCE(department, '') AS department, period, CAST(budget_eur AS double) AS budget_eur,
       CAST(committed_eur AS double) AS committed_eur, note FROM brikk_api.finance
ACTIVATE USL TABLE lightning.metastore.osef.brikk_usl.member AS
SELECT COALESCE(member_id, '') AS member_id, COALESCE(name, '') AS name, COALESCE(department, '') AS department,
       role, ai_tool, level FROM brikk.members
ACTIVATE USL TABLE lightning.metastore.osef.brikk_usl.topic AS
SELECT COALESCE(topic, '') AS topic, COALESCE(owner_department, '') AS owner_department, singleton,
       budget_limit_eur, description, keywords FROM brikk.topics
ACTIVATE USL TABLE lightning.metastore.osef.brikk_usl.procedure AS
SELECT COALESCE(procedure_id, '') AS procedure_id, department, level, when_to_use, steps FROM brikk_drive.procedures
-- Cross-source check: who is over budget, joined across Postgres and the REST API through the USL
SELECT m.name, d.department, d.committed_eur, d.budget_eur
FROM lightning.metastore.osef.brikk_usl.member m
JOIN lightning.metastore.osef.brikk_usl.department d ON d.department = m.department
WHERE m.level IN ('lead', 'ceo')
