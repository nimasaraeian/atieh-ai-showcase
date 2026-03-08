import sqlite3
import json
import sys
from pathlib import Path

DB = "atieh_clinic.db"

# ---------------------------------------------------------------------------
# Normalize-and-scan helpers (mirrors reprocess_staging_errors.py)
# ---------------------------------------------------------------------------

def _norm_key(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    if len(s) >= 2 and ((s[0] == s[-1] == "'") or (s[0] == s[-1] == '"')):
        s = s[1:-1].strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("\u200c", " ").replace("\u00a0", " ")
    s = " ".join(s.split())
    return s


def find_in_dict(d: dict, candidates: list):
    norm_map = {_norm_key(k): v for k, v in d.items()}
    for candidate in candidates:
        v = norm_map.get(_norm_key(candidate))
        if v is not None and str(v).strip() not in ("", "None", "nan"):
            return str(v).strip()
    return None


# ---------------------------------------------------------------------------

conn = sqlite3.connect(DB)
cur = conn.cursor()

rows = cur.execute(
    "SELECT row_json FROM stg_appointments WHERE row_json IS NOT NULL LIMIT 10"
).fetchall()

for i, (s,) in enumerate(rows, 1):
    d = json.loads(s)
    desc      = find_in_dict(d, ["توضیحات", "توضيحات", "خدمات"])
    doctor    = find_in_dict(d, ["نام پزشک", "پزشک", "دکتر", "Doctor"])
    insurance = find_in_dict(d, ["سازمان بیمه گر", "سازمان بيمه گر", "بیمه", "Insurance"])
    print(i, "| desc:", desc, "| doctor:", doctor, "| insurance:", insurance)

conn.close()
