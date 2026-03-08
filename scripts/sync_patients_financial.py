# -*- coding: utf-8 -*-
"""
پایپلاین یکپارچه: تطبیق تمام بیماران کلینیک با وضعیت مالی و به‌روزرسانی دیتابیس.

این اسکریپت به ترتیب انجام می‌دهد:
  1. ایمپورت نوبت‌دهی (patients, appointments)
  2. اینجست پرداخت‌ها (stg_payments)
  3. build_payments_clean (تطبیق پرداخت ← بیمار با phone/name)
  4. build_financial_patient_dim
  5. build_patient_record_map (record_no → patient_id)
  6. build_patient_financial_summary
  7. ایجاد/به‌روزرسانی نمای بیماران با وضعیت مالی

اجرا از ریشه پروژه:
  python scripts/sync_patients_financial.py
  python scripts/sync_patients_financial.py --skip-import   # اگر نوبت‌دهی قبلاً ایمپورت شده
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).parent.parent


def run(cmd: list[str], cwd: Path) -> bool:
    """اجرای دستور؛ در صورت خطا False برمی‌گرداند."""
    print(f"\n>>> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd)
    return r.returncode == 0


def main():
    import argparse
    p = argparse.ArgumentParser(description="تطبیق بیماران با وضعیت مالی")
    p.add_argument("--skip-import", action="store_true", help="رد کردن ایمپورت نوبت‌دهی")
    p.add_argument("--skip-payments-ingest", action="store_true", help="رد کردن اینجست پرداخت‌ها")
    args = p.parse_args()

    if not args.skip_import:
        ok = run([sys.executable, "scripts/import_history_batch.py"], REPO)
        if not ok:
            print("خطا در ایمپورت نوبت‌دهی")
            sys.exit(1)

    if not args.skip_payments_ingest:
        ok = run([sys.executable, "scripts/ingest_payments.py"], REPO)
        if not ok:
            print("خطا در اینجست پرداخت‌ها")
            sys.exit(1)

    ok = run([sys.executable, "tools/build_payments_clean.py"], REPO)
    if not ok:
        print("خطا در build_payments_clean")
        sys.exit(1)

    ok = run([sys.executable, "tools/build_financial_patient_dim.py"], REPO)
    if not ok:
        print("خطا در build_financial_patient_dim")
        sys.exit(1)

    ok = run([sys.executable, "tools/build_patient_record_map.py"], REPO)
    if not ok:
        print("خطا در build_patient_record_map")
        sys.exit(1)

    ok = run([sys.executable, "tools/build_patient_financial_summary.py"], REPO)
    if not ok:
        print("خطا در build_patient_financial_summary")
        sys.exit(1)

    # ایجاد نمای بیماران با وضعیت مالی
    ensure_financial_view()

    print("\n" + "=" * 60)
    print("پایپلاین کامل شد.")
    print_stats()


def ensure_financial_view():
    """ایجاد نمای v_patients_with_financial."""
    import sqlite3
    db = REPO / "atieh_clinic.db"
    mig = REPO / "app" / "db" / "migrations" / "012_v_patients_with_financial.sql"
    if not db.exists():
        return
    if mig.exists():
        conn = sqlite3.connect(db)
        with open(mig, encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()
    print("\n>>> نمای v_patients_with_financial اعمال شد.")


def print_stats():
    """چاپ آمار تطبیق."""
    import sqlite3
    db = REPO / "atieh_clinic.db"
    if not db.exists():
        print("دیتابیس یافت نشد.")
        return
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    total_patients = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    matched = cur.execute("""
        SELECT COUNT(DISTINCT patient_id) FROM payments_clean
        WHERE patient_id IS NOT NULL
    """).fetchone()[0]
    total_payments = cur.execute("SELECT COUNT(*) FROM payments_clean").fetchone()[0]
    conn.close()
    print(f"  کل بیماران (نوبت‌دهی): {total_patients}")
    print(f"  بیماران با وضعیت مالی (منطبق): {matched}")
    print(f"  کل ردیف‌های پرداخت: {total_payments}")


if __name__ == "__main__":
    main()
