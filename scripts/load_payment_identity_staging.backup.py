import sqlite3
import pandas as pd
from pathlib import Path
import re

DB = r".\atieh_clinic_working.db"

EXCLUDE_YEARS = {"1401"}

TARGETS = {
    "receipt": "????? ????",
    "record": "????? ??????",
    "name": "??? ?????",
    "mobile": "??????",
    "nid": "?? ???",
    "date": "????? ?????",
    "net": "???? ???????",
}

def clean_str(x):
    if pd.isna(x):
        return ""
    s = str(x).strip()
    return "" if s.lower() == "nan" else s

def detect_year_from_filename(name: str) -> str:
    m = re.search(r"(13\d{2}|14\d{2})", name)
    return m.group(1) if m else ""

def normalize_header(col):
    s = str(col).strip()

    # remove wrapping quotes repeatedly
    for _ in range(3):
        if len(s) >= 2 and ((s[0] == "'" and s[-1] == "'") or (s[0] == '"' and s[-1] == '"')):
            s = s[1:-1].strip()

    # normalize Arabic/Persian chars
    s = s.replace("?", "?").replace("?", "?")

    # normalize separators and spacing
    s = s.replace("|", " ")
    s = s.replace("\u200c", " ")
    s = " ".join(s.split())
    return s

base = Path(".")
all_files = sorted(base.rglob("payments_*.xlsx"))

files = []
for p in all_files:
    year = detect_year_from_filename(p.name)
    if year in EXCLUDE_YEARS:
        continue
    files.append(p)

if not files:
    raise FileNotFoundError("No payments_*.xlsx files found (excluding 1401).")

print("Files selected for staging:")
for f in files:
    print(" -", f)

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("DELETE FROM payment_identity_staging")

insert_rows = []

for path in files:
    df = pd.read_excel(path)

    # build normalized column map
    norm_map = {}
    for c in df.columns:
        norm_map[normalize_header(c)] = c

    missing = [v for v in TARGETS.values() if v not in norm_map]
    if missing:
        print(f"Skipping {path.name} | missing normalized columns: {missing}")
        print("Available normalized columns sample:")
        for k in list(norm_map.keys())[:30]:
            print("   ", repr(k))
        continue

    col_receipt = norm_map[TARGETS["receipt"]]
    col_record  = norm_map[TARGETS["record"]]
    col_name    = norm_map[TARGETS["name"]]
    col_mobile  = norm_map[TARGETS["mobile"]]
    col_nid     = norm_map[TARGETS["nid"]]
    col_date    = norm_map[TARGETS["date"]]
    col_net     = norm_map[TARGETS["net"]]

    work = df[[col_receipt, col_record, col_name, col_mobile, col_nid, col_date, col_net]].copy()

    inserted_for_file = 0

    for _, row in work.iterrows():
        receipt_no = clean_str(row[col_receipt])
        record_no = clean_str(row[col_record])
        patient_name = clean_str(row[col_name])
        mobile = clean_str(row[col_mobile])
        national_id = clean_str(row[col_nid])
        admission_date = clean_str(row[col_date])
        net_received = clean_str(row[col_net])

        if not record_no:
            continue

        insert_rows.append((
            path.name,
            receipt_no,
            record_no,
            patient_name,
            mobile,
            national_id,
            admission_date,
            net_received
        ))
        inserted_for_file += 1

    print(f"{path.name}: inserted rows prepared = {inserted_for_file}")

cur.executemany("""
INSERT INTO payment_identity_staging (
    source_file,
    receipt_no,
    record_no,
    patient_name_raw,
    mobile_raw,
    national_id_raw,
    admission_date_raw,
    net_received_raw
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", insert_rows)

conn.commit()

count_all = cur.execute("SELECT COUNT(*) FROM payment_identity_staging").fetchone()[0]
count_record = cur.execute("SELECT COUNT(DISTINCT record_no) FROM payment_identity_staging").fetchone()[0]
count_nid = cur.execute("""
    SELECT COUNT(*)
    FROM payment_identity_staging
    WHERE national_id_raw IS NOT NULL
      AND TRIM(national_id_raw) <> ''
""").fetchone()[0]

print()
print(f"rows inserted: {count_all}")
print(f"distinct record_no: {count_record}")
print(f"rows with national_id_raw: {count_nid}")

conn.close()

