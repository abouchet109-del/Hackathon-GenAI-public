-- Brikk org data for Steward (source 1 of 3 in Zetaris). Runs once, on the first start of brikk-db.
CREATE TABLE members (member_id TEXT PRIMARY KEY, name TEXT, department TEXT, role TEXT, ai_tool TEXT, level TEXT);
CREATE TABLE trust (level TEXT PRIMARY KEY, own_domain_weight TEXT, other_domain_weight TEXT, description TEXT);
CREATE TABLE topics (topic TEXT PRIMARY KEY, owner_department TEXT, singleton TEXT, budget_limit_eur TEXT,
                     description TEXT, keywords TEXT);
CREATE TABLE rules (rule_id TEXT PRIMARY KEY, item_type TEXT, condition TEXT, decision TEXT, rationale TEXT);
CREATE TABLE project (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE profiles (member_id TEXT PRIMARY KEY, focus TEXT, detail_level TEXT, topics_followed TEXT,
                       responsibilities TEXT);
COPY members FROM '/seed/members.csv' WITH (FORMAT csv, HEADER true);
COPY trust FROM '/seed/trust.csv' WITH (FORMAT csv, HEADER true);
COPY topics FROM '/seed/topics.csv' WITH (FORMAT csv, HEADER true);
COPY rules FROM '/seed/rules.csv' WITH (FORMAT csv, HEADER true);
COPY project FROM '/seed/project.csv' WITH (FORMAT csv, HEADER true);
COPY profiles FROM '/seed/profiles.csv' WITH (FORMAT csv, HEADER true);
CREATE TABLE tasks (task_id TEXT PRIMARY KEY, member TEXT, topic TEXT, title TEXT, due TEXT, depends_on TEXT);
COPY tasks FROM '/seed/tasks.csv' WITH (FORMAT csv, HEADER true);
-- Fallback copies: if the REST or MinIO registration fails in Zetaris, map finance/procedures to these.
CREATE TABLE finance (department TEXT PRIMARY KEY, period TEXT, budget_eur NUMERIC, committed_eur NUMERIC, note TEXT);
CREATE TABLE procedures (procedure_id TEXT PRIMARY KEY, department TEXT, level TEXT, when_to_use TEXT, steps TEXT);
COPY finance FROM '/seed/finance.csv' WITH (FORMAT csv, HEADER true);
COPY procedures FROM '/seed/procedures.csv' WITH (FORMAT csv, HEADER true);
