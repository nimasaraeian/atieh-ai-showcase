import re
import sqlite3
from collections import Counter, defaultdict

DB = "atieh_clinic.db"

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
ARABIC_DIGITS  = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def norm_phone(s: str | None) -> str | None:
    if not s:
        return None
    s = str(s).strip().translate(PERSIAN_DIGITS).translate(ARABIC_DIGITS)
    s = re.sub(r"\D+", "", s)  # keep digits only

    if not s:
        return None

    # normalize Iran mobile patterns
    # examples: 09xxxxxxxxx, 989xxxxxxxxx, 00989xxxxxxxxx
    if s.startswith("0098"):
        s = "0" + s[4:]
    elif s.startswith("98"):
        s = "0" + s[2:]

    # keep only likely mobile length
    if len(s) == 10 and s.startswith("9"):
        s = "0" + s
    if len(s) != 11 or not s.startswith("09"):
        return None

    return s

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # pull patients phones
    patients = cur.execute("SELECT id, phone FROM patients WHERE phone IS NOT NULL AND TRIM(phone) <> ''").fetchall()
    phone_to_patient = {}
    for r in patients:
        p = norm_phone(r["phone"])
        if p:
            # if duplicates exist, keep the first; we’ll measure collisions later
            phone_to_patient.setdefault(p, r["id"])

    # pull payments phones per record_no
    rows = cur.execute("""
        SELECT record_no, phone_raw
        FROM payments_clean
        WHERE record_no IS NOT NULL AND TRIM(record_no) <> ''
    """).fetchall()

    phones_by_record = defaultdict(list)
    for r in rows:
        rn = str(r["record_no"]).strip()
        ph = norm_phone(r["phone_raw"])
        if ph:
            phones_by_record[rn].append(ph)

    # build mapping rows
    mapping_rows = []
    for rn, phs in phones_by_record.items():
        cnt = Counter(phs)
        best_phone, best_count = cnt.most_common(1)[0]
        total = sum(cnt.values())
        confidence = best_count / total if total else 0.0

        patient_id = phone_to_patient.get(best_phone)

        mapping_rows.append((rn, patient_id, best_phone, "phone_mode", confidence, total))

    cur.execute("DELETE FROM record_no_patient_map;")
    cur.executemany("""
        INSERT INTO record_no_patient_map(record_no, patient_id, phone_norm, match_method, confidence, evidence_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, mapping_rows)

    con.commit()

    # quick report
    stats = cur.execute("""
      SELECT
        COUNT(*) AS total_record_no,
        SUM(CASE WHEN patient_id IS NOT NULL THEN 1 ELSE 0 END) AS mapped,
        ROUND(100.0 * SUM(CASE WHEN patient_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_mapped,
        ROUND(AVG(confidence), 3) AS avg_conf
      FROM record_no_patient_map;
    """).fetchone()

    print(dict(stats))
    con.close()

if __name__ == "__main__":
    main()