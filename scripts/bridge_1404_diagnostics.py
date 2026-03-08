# -*- coding: utf-8 -*-
"""Diagnostics for 1404 bridge: phone loading, overlap, dedup."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

# Import from bridge script
from bridge_1404_payment_appointment import (
    load_payments,
    load_appointments,
    build_pay_rows,
    build_appt_rows,
    normalize_phones,
    REPO,
)

def main():
    payments_path = REPO / "data" / "inputs" / "payments" / "payments_1404_full.xlsx"
    appt_dir = REPO / "data" / "inputs" / "history" / "1404"
    appt_path = sorted(appt_dir.glob("*.xlsx"))[0] if appt_dir.exists() else None

    if not payments_path.exists() or not appt_path:
        print("Files not found")
        return

    df_pay, col_pay = load_payments(payments_path)
    df_appt, col_appt = load_appointments(appt_path)

    print("=== COLUMN MAPPING ===")
    print("Payments:", col_pay)
    print("Appointments:", col_appt)
    print()

    # Sample raw values
    if col_pay.get("phone"):
        sample_pay_phone = df_pay[col_pay["phone"]].dropna().head(20)
        print("Payment phone RAW sample (first 20 non-null):")
        for i, v in enumerate(sample_pay_phone):
            print(f"  [{i}] {repr(v)[:80]}")
    else:
        print("Payment: NO PHONE COLUMN FOUND")
    print()

    if col_appt.get("phone"):
        sample_appt_phone = df_appt[col_appt["phone"]].dropna().head(20)
        print("Appointment phone RAW sample (first 20 non-null):")
        for i, v in enumerate(sample_appt_phone):
            print(f"  [{i}] {repr(v)[:80]}")
    else:
        print("Appointment: NO PHONE COLUMN FOUND")
    print()

    pay_rows = build_pay_rows(df_pay, col_pay)
    appt_rows = build_appt_rows(df_appt, col_appt)

    # 1. Payment rows with usable phone
    pay_with_phone = sum(1 for p in pay_rows if p.phones)
    print("=== PHONE COUNTS ===")
    print(f"Payment rows with usable normalized phone: {pay_with_phone:,} / {len(pay_rows):,}")

    # 2. Appointment rows with usable phone
    appt_with_phone = sum(1 for a in appt_rows if a.phones)
    print(f"Appointment rows with at least one usable phone: {appt_with_phone:,} / {len(appt_rows):,}")

    # 3. Exact phone overlaps (any payment phone in any appointment phone, by name)
    from collections import defaultdict
    appt_phones_by_name = defaultdict(set)
    for a in appt_rows:
        if a.name_norm and a.phones:
            appt_phones_by_name[a.name_norm].update(a.phones)

    overlaps = 0
    date_name_match_phone_missing = 0
    date_name_phone_should_a = 0
    for p in pay_rows:
        if not p.name_norm or not p.record_no:
            continue
        appt_phones = appt_phones_by_name.get(p.name_norm, set())
        has_overlap = bool(p.phones and appt_phones and (p.phones & appt_phones))
        if has_overlap:
            overlaps += 1
        # date+name match but phone missing one/both
        # (we need to check against appt_by_date_name - simplified: if date+name would match)
        if p.date_key and p.name_norm:
            appt_same = [a for a in appt_rows if a.date_key == p.date_key and a.name_norm == p.name_norm]
            if appt_same:
                a = appt_same[0]
                pay_has = bool(p.phones)
                appt_has = bool(a.phones)
                if not pay_has or not appt_has:
                    date_name_match_phone_missing += 1
                elif pay_has and appt_has and (p.phones & a.phones):
                    date_name_phone_should_a += 1

    print(f"Payment rows with name+phone overlap to ANY appointment (by name): {overlaps:,}")
    print(f"Rows where date+name match exists but phone missing on one/both sides: {date_name_match_phone_missing:,}")
    print(f"Rows where date+name+phone should match (Tier A candidates): {date_name_phone_should_a:,}")

    # 4. Name+phone without date - Tier C candidates
    tier_c_candidates = 0
    for p in pay_rows:
        if not p.name_norm or not p.record_no or not p.phones:
            continue
        appt_phones = appt_phones_by_name.get(p.name_norm, set())
        if appt_phones and (p.phones & appt_phones):
            # Would be C if date weak/missing or not unique on date+name
            tier_c_candidates += 1
    print(f"Rows where name+phone overlap exists (Tier C candidates): {tier_c_candidates:,}")

    # Sample normalized phones
    print()
    print("=== NORMALIZED PHONE SAMPLES ===")
    for i, p in enumerate(pay_rows[:50]):
        if p.phones:
            print(f"Pay row {p.row_idx}: raw={repr(p.phone_raw)[:50]} -> norm={p.phones}")
            break
    for i, a in enumerate(appt_rows[:200]):
        if a.phones:
            print(f"Appt row {a.row_idx}: raw={repr(a.phone_raw)[:50]} -> norm={a.phones}")
            break

    # Check Persian digits in raw
    print()
    print("=== PERSIAN/ARABIC DIGIT CHECK ===")
    persian = "۰۱۲۳۴۵۶۷۸۹"
    for i, p in enumerate(pay_rows[:5000]):
        if p.phone_raw and any(c in p.phone_raw for c in persian):
            print(f"Payment has Persian digits: {repr(p.phone_raw)[:60]}")
            print(f"  normalized: {normalize_phones(p.phone_raw)}")
            break
    else:
        print("No Persian digits in first 5000 payment phones")
    for i, a in enumerate(appt_rows[:2000]):
        if a.phone_raw and any(c in a.phone_raw for c in persian):
            print(f"Appointment has Persian digits: {repr(a.phone_raw)[:60]}")
            print(f"  normalized: {normalize_phones(a.phone_raw)}")
            break
    else:
        print("No Persian digits in first 2000 appointment phones")


if __name__ == "__main__":
    main()
