import sqlite3
import re

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

pattern = re.compile(r"\b\d{10}\b")

cur.execute("SELECT id, row_json FROM stg_payments")

total = 0
found = 0
samples = []

for row_id, row_json in cur:
    total += 1

    matches = pattern.findall(row_json or "")

    if matches:
        found += 1
        if len(samples) < 20:
            samples.append((row_id, matches))

    if total % 50000 == 0:
        print("scanned:", total)

conn.close()

print("\nTOTAL ROWS:", total)
print("ROWS WITH 10 DIGIT NUMBERS:", found)

print("\nSAMPLES:")
for s in samples:
    print(s)