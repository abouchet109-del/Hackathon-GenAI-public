-- Register the synthetic Postgres database (docker compose service osef-db) in Zetaris.
-- Run ONE statement at a time in the Zetaris SQL Editor (http://localhost:3000),
-- or: python3 vendor/zetaris-getting-started/scripts/run_sql.py scripts/zetaris/register_sources.sql --dry-run
-- Not yet verified against a live instance: syntax from Zetaris' SQL command reference (section 4).
-- From inside the Zetaris containers, the host is host.docker.internal; osef-db listens on 5433.

CREATE DATASOURCE osef DESCRIBE BY "OSEF synthetic admin data" OPTIONS (
  jdbcdriver "org.postgresql.Driver",
  jdbcurl "jdbc:postgresql://host.docker.internal:5433/osef",
  username "osef",
  password "osef_local_only",
  fetchsize "1000"
);

REGISTER DATASOURCE TABLES ("rules", "senders", "profile") FROM osef;

-- Checks
SHOW DATASOURCES;
SELECT rule_id, decision FROM osef.rules;
SELECT sender_domain, verified FROM osef.senders WHERE sender_domain = 'edf.fr';
