"""Run scripts/zetaris/register_steward.sql against Zetaris, one statement per request, then read every table back.

  python scripts/zetaris/run_steward_sql.py --dry-run        # print the statements only
  python scripts/zetaris/run_steward_sql.py                  # run them all, stop at the first error, then verify
  python scripts/zetaris/run_steward_sql.py --from 12        # resume at statement 12
  python scripts/zetaris/run_steward_sql.py --verify-only    # only the read-back check (counts vs the CSVs)
  python scripts/zetaris/run_steward_sql.py --commit <sha>   # re-pin source 3 on another commit of procedures.json
Needs ZETARIS_API_KEY (and ZETARIS_REST_URL / ZETARIS_ORG_ID if not default) in .env.
The read-back check (app/adapters/verify_sources.py) counts each table Steward reads and compares with its CSV;
it is the quality rule of docs/ARCHITECTURE.md section 4, and it is tested offline on the SQLite copy.
"""
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

STARTS = re.compile(r"^(CREATE DATASOURCE|REGISTER|SELECT|CREATE LIGHTNING|CREATE SCHEMASTORE|CREATE NAMESPACE|"
                    r"COMPILE USL|ACTIVATE USL|CACHE TABLE|SHOW|DESCRIBE)\b", re.I)


def last_commit_of(rel_path: str) -> str:
    import subprocess
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel_path], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        out = ""
    return out or "main"


def statements(path: Path) -> list[str]:
    out, cur = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("--"):
            continue
        continues = cur and cur[-1].rstrip().upper().endswith(" AS")
        if STARTS.match(line) and not continues:
            if cur:
                out.append("\n".join(cur))
            cur = [line]
        else:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "scripts" / "zetaris" / "register_steward.sql"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from", dest="start", type=int, default=1)
    ap.add_argument("--source-repo", default=os.getenv("ZETARIS_SOURCE_REPO", "abouchet109-del/Hackathon-GenAI-public"),
                    help="GitHub repo that serves domains/project_memory/data/procedures.json (source 3)")
    ap.add_argument("--commit", default=None, help="commit that holds the JSON (default: the last one that touched it)")
    ap.add_argument("--verify-only", action="store_true", help="skip the statements, only read the tables back")
    ap.add_argument("--no-verify", action="store_true", help="register without the read-back check")
    args = ap.parse_args()
    commit = args.commit or last_commit_of("domains/project_memory/data/procedures.json")
    stmts = [s.replace("{{SOURCE_REPO}}", args.source_repo).replace("{{COMMIT}}", commit)
             for s in statements(Path(args.file))]
    url = next((line.split('"')[1] for s in stmts for line in s.splitlines() if "cdn.jsdelivr.net" in line), None)
    if args.dry_run:
        for i, s in enumerate(stmts, 1):
            print(f"--- [{i}]\n{s}\n")
        return 0
    from app.adapters.zetaris import ZetarisClient
    from app.config import SETTINGS
    if not SETTINGS.zetaris_api_key:
        print("ZETARIS_API_KEY is missing in .env", file=sys.stderr)
        return 2
    if url and args.start <= 1:
        import requests
        try:
            code = requests.get(url, timeout=20).status_code
        except requests.RequestException as error:
            code = str(error)
        if code != 200:
            print(f"Source 3 is not reachable yet ({code}): {url}\n"
                  "Push the commit that holds procedures.json to the public repository first, or pass --commit.",
                  file=sys.stderr)
            return 2
        print(f"source 3 reachable: {url}")
    client = ZetarisClient(SETTINGS)
    if not args.verify_only:
        for i, s in enumerate(stmts, 1):
            if i < args.start:
                continue
            print(f"[{i}/{len(stmts)}] {s.splitlines()[0][:90]}")
            try:
                rows = client.run_sql(s, [])
                print(f"    ok ({len(rows)} rows) {str(rows[:3])[:200]}")
            except Exception as error:  # noqa: BLE001
                print(f"    FAILED: {error}\n    Fix it, then resume with --from {i}", file=sys.stderr)
                return 1
        if args.no_verify:
            return 0
    return verify_registration(client)


def verify_registration(client) -> int:
    """Read every table Steward reads back through Zetaris and compare the counts with the CSVs (exit 1 on a gap)."""
    import yaml
    from app.adapters.verify_sources import report, verify
    from app.config import SETTINGS
    domain = yaml.safe_load((SETTINGS.domain_dir / "domain.yaml").read_text(encoding="utf-8"))
    lines = verify(client, SETTINGS.domain_dir / "data", domain.get("zetaris_tables", {}),
                   domain.get("zetaris_usl_tables", {}) if os.getenv("ZETARIS_USE_USL", "").lower() == "true" else None)
    print(report(lines))
    return 0 if all(l["ok"] for l in lines) else 1


if __name__ == "__main__":
    sys.exit(main())
