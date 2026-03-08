import sqlite3
import re

DB_PATH = "atieh_clinic.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n--- patient_name_raw profiling ---")
    row = cur.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN patient_name_raw IS NULL THEN 1 ELSE 0 END) AS nulls,
            SUM(CASE WHEN patient_name_raw IS NOT NULL AND TRIM(patient_name_raw)='' THEN 1 ELSE 0 END) AS empty,
            SUM(CASE WHEN patient_name_raw IS NOT NULL AND TRIM(patient_name_raw)<>'' THEN 1 ELSE 0 END) AS nonempty
        FROM stg_payments
    """).fetchone()
    print("total, nulls, empty, nonempty =", row)

    print("\n--- sample patient_name_raw ---")
    rows = cur.execute("""
        SELECT LENGTH(patient_name_raw), patient_name_raw
        FROM stg_payments
        WHERE patient_name_raw IS NOT NULL
          AND TRIM(patient_name_raw) <> ''
        LIMIT 30
    """).fetchall()
    for ln, txt in rows:
        print(ln, "|", txt)

    print("\n--- sample row_json ---")
    rows = cur.execute("""
        SELECT row_json
        FROM stg_payments
        WHERE row_json IS NOT NULL
          AND TRIM(row_json) <> ''
        LIMIT 3
    """).fetchall()
    for (rj,) in rows:
        print(rj[:500])
        print("---")

    print("\n--- phone_raw profiling ---")
    row = cur.execute("""
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN phone_raw IS NULL OR TRIM(phone_raw)='' THEN 1 ELSE 0 END) AS missing_phone,
          SUM(CASE WHEN phone_raw IS NOT NULL AND TRIM(phone_raw)<>'' THEN 1 ELSE 0 END) AS has_phone
        FROM stg_payments
    """).fetchone()
    print("total, missing_phone, has_phone =", row)

    print("\n--- record_no extraction test (from patient_name_raw) ---")
    pat = re.compile(r"\((\d+)\)\s*$")
    rows = cur.execute("""
        SELECT patient_name_raw
        FROM stg_payments
        WHERE patient_name_raw IS NOT NULL
        LIMIT 200
    """).fetchall()

    ok = 0
    bad = 0
    samples = []
    for (s,) in rows:
        s2 = (s or "").strip()
        m = pat.search(s2)
        if m:
            ok += 1
            if len(samples) < 10:
                samples.append((s2, m.group(1)))
        else:
            bad += 1

    print("ok, bad =", ok, bad)
    for name, rec in samples:
        print(name, "=>", rec)

    conn.close()


if __name__ == "__main__":
    main()