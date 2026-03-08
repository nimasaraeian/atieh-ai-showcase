# -*- coding: utf-8 -*-
"""مجموع مراجعات و بیماران یونیک به تفکیک سال (فقط اعداد). Run: python scripts/stats_by_year.py"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import jdatetime
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# سال‌های موجود در اسکریپت‌های verify
years = [1395, 1396, 1398, 1399, 1400, 1401, 1402]

print("سال\tمجموع_مراجعات\tبیماران_یونیک")
for y in years:
    start = jdatetime.date(y, 1, 1).togregorian().isoformat()
    end = jdatetime.date(y + 1, 1, 1).togregorian().isoformat()
    row = db.execute(text("""
        SELECT COUNT(*) AS appts, COUNT(DISTINCT patient_id) AS patients
        FROM appointments
        WHERE appointment_date >= :s AND appointment_date < :e
    """), {"s": start, "e": end}).fetchone()
    appts, patients = row
    print(f"{y}\t{appts}\t{patients}")

db.close()
