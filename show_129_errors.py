import sqlite3, json

c = sqlite3.connect('atieh_clinic.db')
cur = c.cursor()

rows = cur.execute("""
SELECT id, row_number, file_name, sheet_name, row_json
FROM stg_appointments
WHERE parse_status='error'
  AND parse_error='Cannot create patient without name or phone'
LIMIT 5
""").fetchall()

for (rid, rownum, fname, sheet, rj) in rows:
    d = json.loads(rj)
    print("\n==============================")
    print("id:", rid, "| row_number:", rownum, "| sheet:", sheet)
    # print the two key fields in Persian (best effort)
    print("نام بیمار:", d.get("نام بیمار(تشکیل پرونده شده)") or d.get("نام بیمار") or d.get("نام بيمار(تشكيل پرونده شده)"))
    print("تلفن:", d.get("تلفن"))
    # show all keys with potentially empty values
    empties = [k for k,v in d.items() if v is None or str(v).strip()=="" or str(v).strip().lower() in ("none","nan")]
    print("empty_fields_count:", len(empties))
    print("empty_fields_sample:", empties[:10])
    # if you want full row:
    # print(json.dumps(d, ensure_ascii=False, indent=2))

c.close()