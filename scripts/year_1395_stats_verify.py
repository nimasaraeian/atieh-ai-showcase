# -*- coding: utf-8 -*-
"""Verify 1395 stats with cross-checks. Run: python scripts/year_1395_stats_verify.py"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import jdatetime
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text

# Step 1: Verify date boundaries for 1395
start_1395 = jdatetime.date(1395, 1, 1).togregorian()
start_1396 = jdatetime.date(1396, 1, 1).togregorian()
s = start_1395.isoformat()
e = start_1396.isoformat()

print("=== تایید بازه سال 1395 ===")
print("شروع 1395 (شمسی): 1395/01/01")
print("شروع 1395 (میلادی):", start_1395)
print("پایان بازه - قبل از 1396/01/01 (میلادی):", start_1396)
print("شرط: appointment_date >=", s, "AND appointment_date <", e)
print()

db = SessionLocal()

# Step 2: Main counts
row = db.execute(text("""
    SELECT COUNT(*) AS appts, COUNT(DISTINCT patient_id) AS patients
    FROM appointments
    WHERE appointment_date >= :s AND appointment_date < :e
"""), {"s": s, "e": e}).fetchone()
appts, patients = row

# Step 3: Unique names and phones
row2 = db.execute(text("""
    SELECT COUNT(DISTINCT p.name), COUNT(DISTINCT p.phone)
    FROM patients p
    JOIN appointments a ON a.patient_id = p.id
    WHERE a.appointment_date >= :s AND a.appointment_date < :e
"""), {"s": s, "e": e}).fetchone()
uniq_names, uniq_phones = row2

# Step 4: Verify min/max dates in result
row3 = db.execute(text("""
    SELECT MIN(appointment_date), MAX(appointment_date)
    FROM appointments
    WHERE appointment_date >= :s AND appointment_date < :e
"""), {"s": s, "e": e}).fetchone()
min_dt, max_dt = row3

# Step 5: Payment distribution (include NULL handling)
rows_pay = db.execute(text("""
    SELECT COALESCE(payment_type_norm, payment_type, 'unknown') as pt, COUNT(*)
    FROM appointments
    WHERE appointment_date >= :s AND appointment_date < :e
    GROUP BY pt ORDER BY COUNT(*) DESC
"""), {"s": s, "e": e}).fetchall()

# Step 6: Top insurance orgs
rows_ins = db.execute(text("""
    SELECT raw_text_insurance, COUNT(*)
    FROM appointments
    WHERE appointment_date >= :s AND appointment_date < :e
    AND raw_text_insurance IS NOT NULL AND TRIM(raw_text_insurance) != ''
    GROUP BY raw_text_insurance ORDER BY COUNT(*) DESC LIMIT 20
"""), {"s": s, "e": e}).fetchall()

db.close()

# Cross-check: convert min/max back to Shamsi
min_shamsi = jdatetime.date.fromgregorian(date=datetime.fromisoformat(str(min_dt)).date()) if min_dt else None
max_shamsi = jdatetime.date.fromgregorian(date=datetime.fromisoformat(str(max_dt)).date()) if max_dt else None

print("=== نتایج نهایی سال 1395 (تایید شده) ===")
print()
print("تعداد مراجعه (نوبت):", appts)
print("تعداد بیماران یونیک:", patients)
print("تعداد نام‌های یونیک:", uniq_names)
print("تعداد شماره‌تلفن‌های یونیک:", uniq_phones)
print()
print("تایید بازه داده: اولین نوبت", min_dt, "-> شمسی:", min_shamsi)
print("تایید بازه داده: آخرین نوبت", max_dt, "-> شمسی:", max_shamsi)
print()
print("نوع پرداخت:")
for pt, cnt in rows_pay:
    print(" ", pt, ":", cnt)
print()
print("20 بیمه/وضعیت پرتکرار:")
for name, cnt in rows_ins:
    print(" ", name, ":", cnt)

