import sqlite3
import re

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def clean_name(name: str) -> str:
    s = normalize_text(name)
    s = re.sub(r"\(\s*\d+\s*\)", " ", s)   # remove (101182)
    s = re.sub(r"\b\d+\b", " ", s)         # remove standalone digits
    s = re.sub(r"[\(\)\[\]\{\}\-_/\\]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def canonicalize_name(name: str) -> str:
    s = clean_name(name)
    parts = [p for p in re.split(r"[ \-_]+", s) if p]
    return " ".join(sorted(parts))

def extract_record_no(name: str) -> str:
    if not name:
        return ""
    m = re.search(r"\(\s*(\d{4,12})\s*\)", str(name))
    if m:
        return m.group(1)
    nums = re.findall(r"\b\d{4,12}\b", str(name))
    if nums:
        return nums[0]
    return ""

def normalize_mobile(phone: str) -> str:
    if phone is None:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 10 and digits.startswith("9"):
        return "0" + digits
    if len(digits) == 11 and digits.startswith("09"):
        return digits
    return digits

def main():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("START PHASE 09D", flush=True)

    cur.executescript("""
    DROP TABLE IF EXISTS payments_identity_clean_v3;

    CREATE TABLE payments_identity_clean_v3 AS
    SELECT
        rowid AS payment_rowid,
        "نام بيمار" AS payment_name_raw,
        "موبايل" AS phone_raw
    FROM payments_lookup_norm;

    ALTER TABLE payments_identity_clean_v3 ADD COLUMN payment_name_clean TEXT;
    ALTER TABLE payments_identity_clean_v3 ADD COLUMN payment_name_canonical TEXT;
    ALTER TABLE payments_identity_clean_v3 ADD COLUMN record_no_token TEXT;
    ALTER TABLE payments_identity_clean_v3 ADD COLUMN phone_norm TEXT;
    """)

    rows = conn.execute("""
        SELECT payment_rowid, payment_name_raw, phone_raw
        FROM payments_identity_clean_v3
    """).fetchall()

    print(f"rows loaded: {len(rows):,}", flush=True)

    update_sql = """
    UPDATE payments_identity_clean_v3
    SET payment_name_clean = ?,
        payment_name_canonical = ?,
        record_no_token = ?,
        phone_norm = ?
    WHERE payment_rowid = ?
    """

    for i, row in enumerate(rows, start=1):
        raw_name = row["payment_name_raw"]
        raw_phone = row["phone_raw"]

        payment_name_clean = clean_name(raw_name)
        payment_name_canonical = canonicalize_name(raw_name)
        record_no_token = extract_record_no(raw_name)
        phone_norm = normalize_mobile(raw_phone)

        cur.execute(update_sql, (
            payment_name_clean,
            payment_name_canonical,
            record_no_token,
            phone_norm,
            row["payment_rowid"]
        ))

        if i % 10000 == 0:
            conn.commit()
            print(f"processed: {i:,}", flush=True)

    conn.commit()

    cur.executescript("""
    CREATE INDEX IF NOT EXISTS idx_picv3_recordno
        ON payments_identity_clean_v3(record_no_token);

    CREATE INDEX IF NOT EXISTS idx_picv3_clean_name
        ON payments_identity_clean_v3(payment_name_clean);

    CREATE INDEX IF NOT EXISTS idx_picv3_canonical
        ON payments_identity_clean_v3(payment_name_canonical);

    CREATE INDEX IF NOT EXISTS idx_picv3_phone
        ON payments_identity_clean_v3(phone_norm);
    """)

    summary = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        SUM(CASE WHEN TRIM(COALESCE(payment_name_clean,'')) <> '' THEN 1 ELSE 0 END) AS with_clean_name,
        SUM(CASE WHEN TRIM(COALESCE(record_no_token,'')) <> '' THEN 1 ELSE 0 END) AS with_record_no_token,
        SUM(CASE WHEN TRIM(COALESCE(phone_norm,'')) <> '' THEN 1 ELSE 0 END) AS with_phone_norm
    FROM payments_identity_clean_v3
    """).fetchone()

    print("\n=== PHASE 09D SUMMARY ===", flush=True)
    for k in summary.keys():
        print(f"{k:24}: {summary[k]}", flush=True)

    conn.close()

if __name__ == "__main__":
    main()
