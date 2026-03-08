# -*- coding: utf-8 -*-
"""Quick script to check patient details."""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from database import SessionLocal
from sqlalchemy import text

# Get patient 140 (ملازاده سیما) full info + insurance from appointments
db = SessionLocal()
p = db.execute(text("SELECT id, name, phone, national_id, payment_type FROM patients WHERE id = 140")).fetchone()
ins = db.execute(text("""
    SELECT DISTINCT raw_text_insurance FROM appointments 
    WHERE patient_id = 140 AND raw_text_insurance IS NOT NULL AND raw_text_insurance != ''
    LIMIT 10
""")).fetchall()
db.close()
print("Patient:", p[1])
print("Phone:", p[2])
print("National ID:", p[3])
print("Patient payment_type:", p[4])
print("Insurance (from appointments):", [x[0] for x in ins] if ins else "در نوبت‌ها ذخیره نشده")
