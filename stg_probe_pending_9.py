import sqlite3, json

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

rows = cur.execute("""
SELECT id, row_json
FROM stg_appointments
WHERE parse_status='pending'
ORDER BY id
""").fetchall()

print("pending_count =", len(rows))

for rid, rj in rows:
    d = json.loads(rj)
    date = d.get("تاریخ نوبت")
    time = d.get("ساعت نوبت")
    name = d.get("نام بیمار(تشکیل پرونده شده)")
    phone = d.get("تلفن")
    print("\nID:", rid)
    print("date=", date, "| time=", time)
    print("name=", name, "| phone=", phone)

c.close()