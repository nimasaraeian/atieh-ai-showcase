# -*- coding: utf-8 -*-
"""Inspect DB schema for patient search design."""
import sqlite3
import os

db = "atieh_clinic_working.db" if os.path.exists("atieh_clinic_working.db") else "atieh_clinic.db"
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("TABLES:", tables)

for t in [
    "patients",
    "record_no_patient_map",
    "patient_recordno_map",
    "patient_record_map",
    "financial_identity_profile",
    "patient_financial_summary",
    "appointment_recordno_bridge",
]:
    if t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        print(f"\n{t} columns:", [c[1] for c in cols])

cur.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
views = [r[0] for r in cur.fetchall()]
print("\nVIEWS:", views)

for v in views:
    if "financial" in v.lower() or "patient" in v.lower():
        cur.execute(f"PRAGMA table_info({v})")
        cols = cur.fetchall()
        print(f"\n{v} columns:", [c[1] for c in cols])

for t in ["patients", "record_no_patient_map", "patient_recordno_map", "financial_identity_profile", "patient_financial_summary"]:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"\n{t} row count:", cur.fetchone()[0])
    except Exception as e:
        print(f"\n{t}: {e}")

# Sample from patients
try:
    cur.execute("SELECT * FROM patients LIMIT 1")
    row = cur.fetchone()
    cur.execute("PRAGMA table_info(patients)")
    cols = [c[1] for c in cur.fetchall()]
    print("\npatients sample:", dict(zip(cols, row) if row else []))
except Exception as e:
    print("patients sample:", e)

cur.execute(
    "SELECT sql FROM sqlite_master WHERE type='view' AND name='v_financial_identity_profile'"
)
row = cur.fetchone()
print("\nv_financial_identity_profile definition:")
print(row[0][:1500] if row else "NOT FOUND")

conn.close()
