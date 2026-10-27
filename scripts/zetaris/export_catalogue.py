"""Write domains/project_memory/data/procedures.json from procedures.csv, the file Zetaris reads as source 3.

  python scripts/zetaris/export_catalogue.py
Commit the JSON, push, then register with run_steward_sql.py (the URL is pinned on the commit that holds it).
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "domains" / "project_memory" / "data" / "procedures.csv"
DST = SRC.with_suffix(".json")

if __name__ == "__main__":
    with SRC.open(encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    DST.write_text(json.dumps({"source": "Brikk company catalogue (synthetic)", "records": records},
                              indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{DST.relative_to(ROOT)}: {len(records)} records")
