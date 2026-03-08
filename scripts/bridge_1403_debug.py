# -*- coding: utf-8 -*-
"""Debug bridge 1403 - why 0 matches. Run: python scripts/bridge_1403_debug.py"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from pathlib import Path
from scripts.bridge_1403_payment_appointment import (
    load_payments,
    load_appointments,
    build_pay_rows,
    build_appt_rows,
    REPO,
)

def main():
    payments_path = REPO / "data" / "inputs" / "payments" / "payments_1403_full.xlsx"
    appt_dir = REPO / "data" / "inputs" / "history" / "1403"
    xlsx = list(appt_dir.glob("*.xlsx")) if appt_dir.exists() else []
    appt_path = sorted(xlsx)[0] if xlsx else None

    if not payments_path.exists():
        print("ERROR: Payments not found")
        return
    if not appt_path:
        print("ERROR: Appointment file not found")
        return

    print("=== Load payments ===")
    df_pay, col_pay = load_payments(payments_path)
    print("Col map:", col_pay)
    pay_rows = build_pay_rows(df_pay, col_pay)
    print(f"Total pay rows: {len(pay_rows)}")

    # Stats
    with_record_no = sum(1 for p in pay_rows if p.record_no)
    with_date = sum(1 for p in pay_rows if p.date_key)
    with_phone = sum(1 for p in pay_rows if p.phones)
    with_name = sum(1 for p in pay_rows if p.name_norm)
    print(f"  With record_no: {with_record_no}")
    print(f"  With date_key: {with_date}")
    print(f"  With phones: {with_phone}")
    print(f"  With name_norm: {with_name}")

    # Sample date_keys
    dates_pay = {p.date_key for p in pay_rows if p.date_key}
    print(f"  Sample date_keys (pay): {sorted(dates_pay)[:5]}")

    # Sample names
    print("  Sample names (pay):")
    for p in pay_rows[:5]:
        print(f"    date={p.date_key!r} name={p.name_norm!r} record_no={p.record_no!r} phones={len(p.phones)}")

    print()
    print("=== Load appointments ===")
    df_appt, col_appt = load_appointments(appt_path)
    print("Col map:", col_appt)
    appt_rows = build_appt_rows(df_appt, col_appt)
    print(f"Total appt rows: {len(appt_rows)}")

    with_date_appt = sum(1 for a in appt_rows if a.date_key)
    with_phone_appt = sum(1 for a in appt_rows if a.phones)
    with_name_appt = sum(1 for a in appt_rows if a.name_norm)
    print(f"  With date_key: {with_date_appt}")
    print(f"  With phones: {with_phone_appt}")
    print(f"  With name_norm: {with_name_appt}")

    dates_appt = {a.date_key for a in appt_rows if a.date_key}
    print(f"  Sample date_keys (appt): {sorted(dates_appt)[:5]}")

    print("  Sample names (appt):")
    for a in appt_rows[:5]:
        print(f"    date={a.date_key!r} name={a.name_norm!r} phones={len(a.phones)}")

    # Overlap
    overlap_dates = dates_pay & dates_appt
    names_pay = {p.name_norm for p in pay_rows if p.name_norm}
    names_appt = {a.name_norm for a in appt_rows if a.name_norm}
    overlap_names = names_pay & names_appt
    print()
    print("=== Overlap ===")
    print(f"  Overlap date_keys: {len(overlap_dates)}")
    print(f"  Overlap name_norm: {len(overlap_names)}")
    if overlap_names:
        print(f"  Sample overlap names: {list(overlap_names)[:5]}")

if __name__ == "__main__":
    main()
