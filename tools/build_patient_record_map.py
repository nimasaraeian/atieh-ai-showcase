import sqlite3

DB_PATH = "atieh_clinic.db"


def norm_persian(s):
    """نرمال کردن نام برای تطبیق."""
    if not s:
        return ""
    s = (str(s) or "").strip().replace("ي", "ی").replace("ك", "ک")
    s = s.replace("\u200c", " ")
    return " ".join(s.split())


def norm_phone(s):
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

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # patients phone_norm -> patient_id (keep first; duplicates will be ignored)
    phone_to_patient = {}
    rows = cur.execute("SELECT id, phone FROM patients").fetchall()
    for pid, phone in rows:
        p = norm_phone(phone)
        if p and p not in phone_to_patient:
            phone_to_patient[p] = pid

    # map record_no via phone_norm in financial_patient_dim
    rows = cur.execute("""
        SELECT record_no, phone_norm
        FROM financial_patient_dim
        WHERE phone_norm IS NOT NULL AND TRIM(phone_norm) <> ''
    """).fetchall()

    # نام → patient_id (فقط وقتی یک نام به یک بیمار منحصر باشد)
    name_to_patient = {}
    for pid, name in cur.execute("SELECT id, name FROM patients").fetchall():
        n = norm_persian(name or "")
        if n:
            if n not in name_to_patient:
                name_to_patient[n] = []
            name_to_patient[n].append(pid)

    mapped_phone = 0
    mapped_name = 0
    for record_no, phone_norm in rows:
        pid = phone_to_patient.get(phone_norm)
        if pid:
            cur.execute("""
                INSERT INTO patient_record_map (record_no, patient_id, match_method, confidence, updated_at)
                VALUES (?, ?, 'phone', 1.0, datetime('now'))
                ON CONFLICT(record_no) DO UPDATE SET
                  patient_id=excluded.patient_id,
                  match_method=excluded.match_method,
                  confidence=excluded.confidence,
                  updated_at=datetime('now')
            """, (record_no, pid))
            mapped_phone += 1

    # Pass 2: map via name for record_no not yet mapped
    already_mapped = {r[0] for r in cur.execute(
        "SELECT record_no FROM patient_record_map WHERE patient_id IS NOT NULL"
    ).fetchall()}
    rows_name = cur.execute("""
        SELECT record_no, name_clean
        FROM financial_patient_dim
        WHERE name_clean IS NOT NULL AND TRIM(name_clean) <> ''
    """).fetchall()

    mapped_name = 0
    for record_no, name_clean in rows_name:
        if record_no in already_mapped:
            continue
        n = norm_persian(name_clean or "")
        if not n:
            continue
        candidates = name_to_patient.get(n, [])
        if len(candidates) == 1:
            pid = candidates[0]
            cur.execute("""
                INSERT INTO patient_record_map (record_no, patient_id, match_method, confidence, updated_at)
                VALUES (?, ?, 'name', 0.85, datetime('now'))
                ON CONFLICT(record_no) DO UPDATE SET
                  patient_id=excluded.patient_id,
                  match_method=excluded.match_method,
                  confidence=excluded.confidence,
                  updated_at=datetime('now')
            """, (record_no, pid))
            mapped_name += 1
            already_mapped.add(record_no)

    conn.commit()

    total_map = cur.execute("SELECT COUNT(*) FROM patient_record_map").fetchone()[0]
    mapped = cur.execute("SELECT COUNT(*) FROM patient_record_map WHERE patient_id IS NOT NULL").fetchone()[0]
    print("mapped via phone:", mapped_phone, "| via name:", mapped_name, "| total mapped:", mapped)
    print("patient_record_map total rows:", total_map)

    conn.close()

if __name__ == "__main__":
    main()