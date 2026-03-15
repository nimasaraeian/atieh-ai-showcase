import sqlite3
import re

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(patients)")
cols = [r[1] for r in cur.fetchall()]

print("PATIENT COLUMNS:")
for c in cols:
    print("-", c)

print("\nCHECKING POSSIBLE NATIONAL ID COLUMNS...\n")

for c in cols:
    try:
        q = f'''
        SELECT
            COUNT(*) AS total_nonnull,
            SUM(CASE WHEN length(trim(CAST("{c}" AS TEXT))) = 10 THEN 1 ELSE 0 END) AS len10,
            SUM(CASE
                    WHEN trim(CAST("{c}" AS TEXT)) GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
                    THEN 1 ELSE 0
                END) AS digit10
        FROM patients
        WHERE "{c}" IS NOT NULL
          AND trim(CAST("{c}" AS TEXT)) <> ''
        '''
        cur.execute(q)
        row = cur.fetchone()
        total_nonnull, len10, digit10 = row
        if total_nonnull and (len10 or digit10):
            print(f"{c} | nonnull={total_nonnull} | len10={len10} | digit10={digit10}")
    except Exception:
        pass

conn.close()
