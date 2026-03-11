#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Populate service_dim from distinct appointments.raw_text_service.

Run after migration 016_service_dim.sql. Uses the service normalizer
to compute clean_service_category, is_noise, etc. for each distinct raw value.

Usage:
  python scripts/populate_service_dim.py
"""
import os
import sqlite3
import sys

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.normalizers.service_normalizer import normalize_service

DB_PATH = os.environ.get("FINANCIAL_DB_PATH") or (
    "atieh_clinic_working.db" if os.path.exists("atieh_clinic_working.db") else "atieh_clinic.db"
)


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Check raw_text_service exists
        cur = conn.execute("PRAGMA table_info(appointments)")
        cols = {r[1] for r in cur.fetchall()}
        if "raw_text_service" not in cols:
            print("appointments.raw_text_service not found. Skipping.")
            return 0

        cur = conn.execute(
            "SELECT DISTINCT raw_text_service FROM appointments "
            "WHERE raw_text_service IS NOT NULL AND TRIM(raw_text_service) != ''"
        )
        raw_values = [r[0] for r in cur.fetchall()]

        # Ensure service_dim exists
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='service_dim'"
        )
        if not cur.fetchone():
            print("service_dim table not found. Run migration 016 first.")
            return 1

        upserted = 0
        for raw in raw_values:
            r = normalize_service(raw)
            conn.execute(
                """
                INSERT OR REPLACE INTO service_dim
                (raw_service_text, clean_service_category, clean_service_subtype,
                 duration_hint_minutes, is_noise)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    raw,
                    r.clean_service_category,
                    r.clean_service_subtype,
                    r.duration_hint_minutes,
                    1 if r.is_noise else 0,
                ),
            )
            upserted += 1

        conn.commit()
        print(f"Populated service_dim with {upserted} mappings.")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
