"""Register the Atlas sources in Zetaris as REST tables, then verify them.

Each source of data/sample/ is published by the public GitHub repo and served
by jsDelivr, pinned on a commit (a branch URL is cached by the CDN). Zetaris
reads the URL on each query; the agents only send SQL.

Idempotent: the Lightning database and the tables that already exist are
kept. A table's URL cannot be changed in place: --repin drops the listed
tables and creates them again on the new commit.

    python scripts/register_zetaris.py --dry-run
    python scripts/register_zetaris.py                 # create what is missing, verify
    python scripts/register_zetaris.py --verify-only
    python scripts/register_zetaris.py --repin tasks   # after changing data/sample/tasks.json
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from atlas.sources import (SOURCES, ZETARIS_DATABASE, load_source,  # noqa: E402
                           load_source_zetaris)
from atlas.zetaris import ZetarisClient, ZetarisError  # noqa: E402

REPO = "abouchet109-del/Hackathon-GenAI-public"
DESCRIPTION = "Atlas project sources, synthetic data"  # alphanumeric, _ . - , only


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def last_data_commit():
    return git("log", "-1", "--format=%H", "--", "data/sample")


def source_url(commit, name):
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{commit}/data/sample/{name}.json"


def create_table_sql(commit, name):
    return (f'CREATE LIGHTNING REST TABLE {name} FROM {ZETARIS_DATABASE.upper()} REQUEST( '
            f'endpoint "{source_url(commit, name)}", method "get", response_type "json", '
            f'http_encoding "URLENCODED" ) HEADER ( ) BODY ( )')


def plan(client, commit, names, repin):
    databases = {row[0].lower() for row in
                 client.query("SHOW LIGHTNING DATABASES", use_cache=False).rows}
    statements = []
    existing = set()
    if ZETARIS_DATABASE not in databases:
        statements.append(f'CREATE LIGHTNING DATABASE {ZETARIS_DATABASE.upper()} '
                          f'DESCRIBE BY "{DESCRIPTION}"')
    else:
        rows = client.query(f"SHOW TABLES IN {ZETARIS_DATABASE}", use_cache=False).rows
        existing = {row[0].split(".")[-1].lower() for row in rows}
    for name in names:
        if name in existing and name in repin:
            statements.append(f"DROP LIGHTNING DATABASE TABLE {ZETARIS_DATABASE}.{name}")
            statements.append(create_table_sql(commit, name))
        elif name not in existing:
            statements.append(create_table_sql(commit, name))
    return statements


def verify(client, names):
    """Each table must give back exactly the records of the local file."""
    ok = True
    for name in names:
        try:
            remote, origin = load_source_zetaris(name, client)
        except (ZetarisError, ValueError) as error:
            print(f"FAIL {name}: {error}")
            ok = False
            continue
        local = load_source(name)
        same = remote == local
        ok &= same
        print(f"{'PASS' if same else 'FAIL'} {name}: {len(remote)} records from {origin}, "
              f"{len(local)} in data/sample/{name}.json")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", help="commit to pin (default: last commit of data/sample)")
    parser.add_argument("--only", nargs="+", choices=sorted(SOURCES), help="sources to handle")
    parser.add_argument("--repin", nargs="+", default=[], choices=sorted(SOURCES),
                        help="drop and recreate these tables on the commit")
    parser.add_argument("--dry-run", action="store_true", help="print the statements only")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    client = ZetarisClient(sample=False)
    names = args.only or list(SOURCES)
    if not args.verify_only:
        commit = args.commit or last_data_commit()
        if f"origin/main" not in git("branch", "-r", "--contains", commit).split():
            sys.exit(f"Commit {commit[:8]} is not on origin/main: push it first, "
                     "jsDelivr serves only what GitHub has.")
        statements = plan(client, commit, names, set(args.repin))
        print(f"Commit {commit[:8]}: {len(statements)} statement(s)")
        for statement in statements:
            print("  " + statement)
            if not args.dry_run:
                client.query(statement, use_cache=False)
        if args.dry_run:
            return 0
    return 0 if verify(client, names) else 1


if __name__ == "__main__":
    sys.exit(main())
