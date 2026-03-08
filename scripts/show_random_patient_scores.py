# -*- coding: utf-8 -*-
"""Show scores for a random patient."""
import sqlite3
import math
from datetime import datetime, date
from pathlib import Path

DB = Path(__file__).parent.parent / "atieh_clinic.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Pick random patient with real name (not دندانپزشکی) and appointments
row = conn.execute("""
    SELECT p.id, p.name, p.phone, p.first_visit_date, p.payment_type
    FROM patients p
    WHERE EXISTS (SELECT 1 FROM appointments a WHERE a.patient_id = p.id)
      AND p.name IS NOT NULL
      AND TRIM(p.name) != ''
      AND p.name NOT IN ('دندانپزشکی', 'nan')
      AND (p.phone IS NULL OR p.phone NOT LIKE 'UNKNOWN_%')
    ORDER BY RANDOM()
    LIMIT 1
""").fetchone()

if not row:
    row = conn.execute("""
        SELECT p.id, p.name, p.phone, p.first_visit_date, p.payment_type
        FROM patients p
        JOIN appointments a ON a.patient_id = p.id
        WHERE p.name IS NOT NULL AND LENGTH(TRIM(p.name)) > 2
        GROUP BY p.id
        ORDER BY RANDOM()
        LIMIT 1
    """).fetchone()

pid = row["id"]
name = row["name"]
phone = row["phone"] or ""
first_visit = row["first_visit_date"]
pay_type = row["payment_type"]

stats = conn.execute("""
    SELECT
        COUNT(*) as total_appts,
        COALESCE(SUM(CASE WHEN final_amount_paid IS NOT NULL THEN final_amount_paid ELSE 0 END), 0) as total_revenue,
        MIN(appointment_date) as first_appt,
        MAX(appointment_date) as last_appt
    FROM appointments WHERE patient_id = ?
""", (pid,)).fetchone()

# Payment type score (0-25)
INSURANCE_SCORES = {"cash": 25, "CASH": 25, "insurance": 10, "default": 10}
pt = str(pay_type).lower() if pay_type else ""
pay_score = INSURANCE_SCORES.get(pt, INSURANCE_SCORES["default"])

# Frequency (0-15)
total_appts = stats["total_appts"] or 0
freq_score = min(15, total_appts * 1.5)

# Tenure (0-25)
tenure_score = 0.0
fa = stats["first_appt"]
if fa:
    try:
        d0 = datetime.strptime(str(fa)[:10], "%Y-%m-%d").date()
        tenure_days = (date.today() - d0).days
        tenure_score = min(25, (tenure_days / 365.0) * 25)
    except Exception:
        pass

# Financial (0-100)
total_rev = float(stats["total_revenue"] or 0)
financial_score = min(100, math.log1p(total_rev / 1000) * 15) if total_rev > 0 else 0.0

print("=" * 50)
print("بیمار تصادفی:", name)
print("ID:", pid, "| تلفن:", (phone[:15] + "...") if len(phone) > 15 else phone)
print("تعداد مراجعات:", total_appts)
print("اولین نوبت:", fa)
print()
print("امتیازات:")
print("  مالی (0-100):", round(financial_score, 1), "- مجموع درآمد:", int(total_rev), "ریال")
print("  نوع پرداخت (0-25):", round(pay_score, 1))
print("  دفعات مراجعه (0-15):", round(freq_score, 1))
print("  طول عمر در کلینیک (0-25):", round(tenure_score, 1))
print("=" * 50)

conn.close()
