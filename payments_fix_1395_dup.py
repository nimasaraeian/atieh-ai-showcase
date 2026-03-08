import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

before = cur.execute("""
SELECT COUNT(1)
FROM stg_payments
WHERE file_name='payments_1395_full.xlsx'
""").fetchone()[0]
print("before_1395 =", before)

cur.execute("""
DELETE FROM stg_payments
WHERE file_name='payments_1395_full.xlsx'
AND id NOT IN (
  SELECT MIN(id)
  FROM stg_payments
  WHERE file_name='payments_1395_full.xlsx'
  GROUP BY sheet_name, row_number
)
""")
c.commit()
print("deleted_rows =", cur.rowcount)

after = cur.execute("""
SELECT COUNT(1)
FROM stg_payments
WHERE file_name='payments_1395_full.xlsx'
""").fetchone()[0]
print("after_1395 =", after)

# sanity: should be exactly half of before
print("expected_after =", before // 2)

c.close()