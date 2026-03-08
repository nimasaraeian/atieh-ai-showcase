import pandas as pd
import sqlite3
from pathlib import Path

repo = Path(r"C:\Users\USER\Documents\GitHub\atieh")
db_path = repo / "atieh_clinic.db"
appt_path = repo / "data" / "inputs" / "history" / "1403" / "نوبت_دهی_بیمارانی_که_حضور_پیدا_کردند_1403.xlsx"

print("=" * 80)
print("APPOINTMENT FILE CHECK")
print("=" * 80)

xls = pd.ExcelFile(appt_path)
print("Sheets:", xls.sheet_names)

for s in xls.sheet_names:
    print(f"\n--- SHEET: {s} ---")
    df = pd.read_excel(appt_path, sheet_name=s)
    print("Shape:", df.shape)
    print("Columns:")
    for c in df.columns:
        print(" -", repr(c))
    print("\nHead:")
    print(df.head(5).to_string())

print("\n" + "=" * 80)
print("PAYMENTS TABLE CHECK")
print("=" * 80)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("\nPayments schema:")
schema = cur.execute("PRAGMA table_info(payments_clean)").fetchall()
for row in schema:
    print(row)

print("\nSample payment rows:")
rows = cur.execute("SELECT * FROM payments_clean LIMIT 5").fetchall()
for r in rows:
    print(r)

conn.close()
