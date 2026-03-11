#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Populate doctor_dim from distinct appointments.raw_text_doctor.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.normalizers.doctor_normalizer import normalize_doctor

DB_PATH = os.environ.get("FINANCIAL_DB_PATH") or (
    "atieh_clinic_working.db" if os.path.exists("atieh_clinic_working.db") else "atieh_clinic.db"
)


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("PRAGMA table_info(appointments)")
        if not any(r[1] == "raw_text_doctor" for r in cur.fetchall()):
            print("appointments.raw_text_doctor not found.")
            return 1
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='doctor_dim'"
        )
        if not cur.fetchone():
            print("doctor_dim not found. Run migration 017 first.")
            return 1
        cur = conn.execute(
            "SELECT DISTINCT raw_text_doctor FROM appointments "
            "WHERE raw_text_doctor IS NOT NULL AND TRIM(raw_text_doctor) != ''"
        )
        count = 0
        for (raw,) in cur.fetchall():
            name, spec = normalize_doctor(raw)
            if not name:
                name = raw[:100]
            conn.execute(
                "INSERT OR REPLACE INTO doctor_dim (raw_doctor_text, clean_doctor_name, doctor_specialty) VALUES (?, ?, ?)",
                (raw, name, spec),
            )
            count += 1
        conn.commit()
        print(f"Populated doctor_dim with {count} mappings.")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
