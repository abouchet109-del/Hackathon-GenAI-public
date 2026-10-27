"""Run scripts/zetaris/register_steward.sql against Zetaris, one statement per request.

  python scripts/zetaris/run_steward_sql.py --dry-run        # print the statements only
  python scripts/zetaris/run_steward_sql.py                  # run them all, stop at the first error
  python scripts/zetaris/run_steward_sql.py --from 12        # resume at statement 12
Needs ZETARIS_API_KEY (and ZETARIS_REST_URL / ZETARIS_ORG_ID if not default) in .env.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

STARTS = re.compile(r"^(CREATE DATASOURCE|REGISTER|SELECT|CREATE LIGHTNING|CREATE SCHEMASTORE|CREATE NAMESPACE|"
                    r"COMPILE USL|ACTIVATE USL|CACHE TABLE|SHOW|DESCRIBE)\b", re.I)


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
    args = ap.parse_args()
    stmts = statements(Path(args.file))
    if args.dry_run:
        for i, s in enumerate(stmts, 1):
            print(f"--- [{i}]\n{s}\n")
        return 0
    from app.adapters.zetaris import ZetarisClient
    from app.config import SETTINGS
    if not SETTINGS.zetaris_api_key:
        print("ZETARIS_API_KEY is missing in .env", file=sys.stderr)
        return 2
    client = ZetarisClient(SETTINGS)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
