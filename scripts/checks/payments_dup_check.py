import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

rows = cur.execute("""
SELECT file_name, COUNT(1) as cnt
FROM stg_payments
GROUP BY file_name
ORDER BY file_name
""").fetchall()

print("counts:", rows)

# quick heuristic: check duplicates by (file_name, sheet_name, row_number)
dups = cur.execute("""
SELECT file_name, COUNT(1) as dup_groups
FROM (
  SELECT file_name, sheet_name, row_number, COUNT(1) c
  FROM stg_payments
  GROUP BY file_name, sheet_name, row_number
  HAVING c > 1
)
GROUP BY file_name
ORDER BY dup_groups DESC
LIMIT 20
""").fetchall()

print("\nduplicate groups by (file,sheet,row):", dups)
c.close()