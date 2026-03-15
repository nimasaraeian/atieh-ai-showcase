import sqlite3
import re

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"
pattern = re.compile(r"\b\d{10}\b")

def is_valid_national_id(code: str) -> bool:
    if not code or len(code) != 10 or not code.isdigit():
        return False
    if len(set(code)) == 1:
        return False
    check = int(code[-1])
    s = sum(int(code[i]) * (10 - i) for i in range(9))
    r = s % 11
    if r < 2:
        return check == r
    return check == (11 - r)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.executescript("""
DROP TABLE IF EXISTS payments_national_id_map;

CREATE TABLE payments_national_id_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id    INTEGER NOT NULL,
    national_id   TEXT    NOT NULL,
    confidence    REAL    NOT NULL DEFAULT 0.98,
    source_method TEXT    NOT NULL DEFAULT 'row_json_regex_checksum',
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX idx_pay_nid_payment   ON payments_national_id_map(payment_id);
CREATE INDEX idx_pay_nid_national  ON payments_national_id_map(national_id);
""")

cur.execute("SELECT id, row_json FROM stg_payments")

rows = 0
inserted = 0

for payment_id, row_json in cur:
    rows += 1
    nums = pattern.findall(row_json or "")
    valid_nids = sorted({x for x in nums if not x.startswith("9") and is_valid_national_id(x)})

    for nid in valid_nids:
        cur.execute("""
            INSERT INTO payments_national_id_map(payment_id, national_id, confidence, source_method)
            VALUES (?, ?, 0.98, 'row_json_regex_checksum')
        """, (payment_id, nid))
        inserted += 1

    if rows % 50000 == 0:
        print(f"scanned: {rows} | inserted: {inserted}")
        conn.commit()

conn.commit()

cur.execute("SELECT COUNT(*) FROM payments_national_id_map")
total_map_rows = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT national_id) FROM payments_national_id_map")
distinct_nids = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT payment_id) FROM payments_national_id_map")
distinct_payments = cur.fetchone()[0]

print("\n=== FINAL ===")
print("TOTAL_SCANNED_ROWS:", rows)
print("TOTAL_MAP_ROWS:", total_map_rows)
print("DISTINCT_NATIONAL_IDS:", distinct_nids)
print("DISTINCT_PAYMENTS_WITH_NID:", distinct_payments)

conn.close()