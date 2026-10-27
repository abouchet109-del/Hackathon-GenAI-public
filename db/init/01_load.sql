-- Runs once, on the first start of the osef-db container. Loads the synthetic CSVs.
CREATE TABLE rules (rule_id TEXT PRIMARY KEY, item_type TEXT, condition TEXT, decision TEXT, rationale TEXT);
CREATE TABLE senders (sender_domain TEXT PRIMARY KEY, organisation TEXT, category TEXT, verified TEXT);
CREATE TABLE profile (key TEXT PRIMARY KEY, value TEXT);
COPY rules FROM '/seed/rules.csv' WITH (FORMAT csv, HEADER true);
COPY senders FROM '/seed/senders.csv' WITH (FORMAT csv, HEADER true);
COPY profile FROM '/seed/profile.csv' WITH (FORMAT csv, HEADER true);
