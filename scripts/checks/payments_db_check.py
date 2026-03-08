import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

# اگر اسم جدول staging فرق داشت، همینجا خطا میده و سریع می‌فهمیم
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("has_stg_payments =", "stg_payments" in tables)

if "stg_payments" not in tables:
    print("tables =", tables)
    c.close()
    raise SystemExit(1)

print("\n--- rows per file ---")
rows = cur.execute("""
SELECT file_name, COUNT(1)
FROM stg_payments
GROUP BY file_name
ORDER BY file_name
""").fetchall()
for r in rows:
    print(r)

print("\n--- status counts ---")
print(cur.execute("""
SELECT parse_status, COUNT(1)
FROM stg_payments
GROUP BY parse_status
ORDER BY COUNT(1) DESC
""").fetchall())

c.close()