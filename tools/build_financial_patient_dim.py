import sqlite3
import re

DB_PATH = "atieh_clinic.db"
RECNO_RE = re.compile(r"\((\d+)\)\s*$")

def norm_persian(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    s = " ".join(s.split())
    return s

def norm_phone(s: str | None) -> str | None:
    if not s:
        return None
    digits = "".join(ch for ch in str(s) if ch.isdigit())
    if not digits:
        return None

    if digits.startswith("0098"):
        digits = digits[2:]
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits

    if len(digits) > 11:
        digits = digits[-11:]

    if len(digits) < 10:
        return None

    return digits

def split_name_and_record_no(patient_name_raw: str | None):
    s = norm_persian(patient_name_raw or "")
    m = RECNO_RE.search(s)
    if not m:
        return (s or None), None
    record_no = m.group(1)
    name = RECNO_RE.sub("", s).strip() or None
    return name, record_no

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM stg_payments").fetchone()[0]
    print("stg_payments total:", total)

    batch = 50000
    offset = 0
    processed = 0

    while True:
        rows = cur.execute("""
            SELECT patient_name_raw, phone_raw, loaded_at
            FROM stg_payments
            ORDER BY id
            LIMIT ? OFFSET ?
        """, (batch, offset)).fetchall()

        if not rows:
            break

        for patient_name_raw, phone_raw, loaded_at in rows:
            name_clean, record_no = split_name_and_record_no(patient_name_raw)
            if not record_no:
                continue

            phone_norm = norm_phone(phone_raw)

            cur.execute("""
                INSERT INTO financial_patient_dim
                (record_no, name_clean, phone_norm, first_seen_loaded_at, last_seen_loaded_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(record_no) DO UPDATE SET
                    name_clean = COALESCE(financial_patient_dim.name_clean, excluded.name_clean),
                    phone_norm = COALESCE(financial_patient_dim.phone_norm, excluded.phone_norm),
                    first_seen_loaded_at = MIN(financial_patient_dim.first_seen_loaded_at, excluded.first_seen_loaded_at),
                    last_seen_loaded_at = MAX(financial_patient_dim.last_seen_loaded_at, excluded.last_seen_loaded_at),
                    updated_at = datetime('now')
            """, (record_no, name_clean, phone_norm, loaded_at, loaded_at))

        conn.commit()

        processed += len(rows)
        offset += batch
        print(f"processed {min(processed, total)}/{total}")

    final_count = cur.execute("SELECT COUNT(*) FROM financial_patient_dim").fetchone()[0]
    print("financial_patient_dim rows:", final_count)

    conn.close()

if __name__ == "__main__":
    main()