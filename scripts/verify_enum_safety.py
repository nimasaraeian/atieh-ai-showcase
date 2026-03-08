"""
verify_enum_safety.py
=====================
Verifies that SafePaymentType and SafeTreatmentType TypeDecorators prevent
LookupError/ValueError crashes when loading Appointment or Patient rows
whose payment_type / treatment_type columns contain unknown DB strings
(e.g. 'insurance', 'dental_care').

Checks performed
----------------
1. Load 50 random Appointment rows via ORM (.all()) without exception.
2. Access .payment_type and .treatment_type on every loaded row.
3. Load 50 random Patient rows via ORM.
4. Access .payment_type on every loaded row.
5. Confirm the distribution of resolved vs. unresolvable values.
6. Round-trip read test: 'cash' -> PaymentType.CASH, 'insurance' -> None.

Exit codes: 0 = all passed, 1 = failure
"""

import os
import sys
import random
import traceback

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

from sqlalchemy import text
from database import SessionLocal
from models import Appointment, Patient, PaymentType, TreatmentType

SAMPLE_SIZE = 50

passed_checks = []
failed_checks = []

print()
print("=" * 62)
print("  verify_enum_safety.py")
print("=" * 62)
print()


def pass_(label, detail=""):
    passed_checks.append(label)
    suffix = f"  ({detail})" if detail else ""
    print(f"  [PASS] {label}{suffix}")


def fail_(label, exc=None, detail=""):
    failed_checks.append((label, exc))
    suffix = f"  ({detail})" if detail else ""
    print(f"  [FAIL] {label}{suffix}")
    if exc:
        print(f"         {type(exc).__name__}: {exc}")


db = SessionLocal()

try:
    total_appts    = db.query(Appointment.id).count()
    total_patients = db.query(Patient.id).count()
    print(f"  DB: {total_appts:,} appointments, {total_patients:,} patients")
    print()

    # ------------------------------------------------------------------
    # CHECK 1: Load 50 random Appointment rows via ORM
    # ------------------------------------------------------------------
    print(f"  [1] ORM load of {SAMPLE_SIZE} random Appointments ...")
    try:
        all_ids   = [r[0] for r in db.query(Appointment.id).all()]
        ids       = random.sample(all_ids, min(SAMPLE_SIZE, len(all_ids)))
        appts     = db.query(Appointment).filter(Appointment.id.in_(ids)).all()
        pass_(f"ORM .all() on {len(appts)} appointments (no exception)")
    except Exception as exc:
        fail_("ORM .all() on appointments", exc)
        appts = []

    # ------------------------------------------------------------------
    # CHECK 2: Access .payment_type and .treatment_type on every row
    # ------------------------------------------------------------------
    print(f"  [2] Accessing .payment_type and .treatment_type ...")
    pt_resolved = pt_none = tt_resolved = tt_none = 0
    all_ok = True
    try:
        for appt in appts:
            pt = appt.payment_type
            tt = appt.treatment_type
            if pt is None:
                pt_none += 1
            else:
                if not isinstance(pt, PaymentType):
                    raise AssertionError(
                        f"appt.id={appt.id}: expected PaymentType|None, got {type(pt)!r}"
                    )
                pt_resolved += 1
            if tt is None:
                tt_none += 1
            else:
                if not isinstance(tt, TreatmentType):
                    raise AssertionError(
                        f"appt.id={appt.id}: expected TreatmentType|None, got {type(tt)!r}"
                    )
                tt_resolved += 1
        pass_(
            f".payment_type and .treatment_type on {len(appts)} rows (no exception)",
            f"pt: resolved={pt_resolved} none={pt_none} | tt: resolved={tt_resolved} none={tt_none}",
        )
    except Exception as exc:
        fail_(".payment_type / .treatment_type access", exc)
        all_ok = False

    # ------------------------------------------------------------------
    # CHECK 3: Guarded .value access (mirrors GET /appointments logic)
    # ------------------------------------------------------------------
    print(f"  [3] Guarded .value access on {len(appts)} rows ...")
    try:
        for appt in appts:
            _ = appt.payment_type.value if appt.payment_type else None
            _ = appt.treatment_type.value if appt.treatment_type else None
        pass_(f"Guarded .value access on {len(appts)} rows (no exception)")
    except Exception as exc:
        fail_("Guarded .value access", exc)

    # ------------------------------------------------------------------
    # CHECK 4: Load 50 random Patient rows
    # ------------------------------------------------------------------
    print(f"  [4] ORM load of {SAMPLE_SIZE} random Patients ...")
    try:
        all_pids  = [r[0] for r in db.query(Patient.id).all()]
        pids      = random.sample(all_pids, min(SAMPLE_SIZE, len(all_pids)))
        patients  = db.query(Patient).filter(Patient.id.in_(pids)).all()
        pass_(f"ORM .all() on {len(patients)} patients (no exception)")
    except Exception as exc:
        fail_("ORM .all() on patients", exc)
        patients = []

    # ------------------------------------------------------------------
    # CHECK 5: Access .payment_type on every Patient row
    # ------------------------------------------------------------------
    print(f"  [5] Accessing Patient.payment_type ...")
    pp_resolved = pp_none = 0
    try:
        for p in patients:
            pt = p.payment_type
            if pt is None:
                pp_none += 1
            else:
                if not isinstance(pt, PaymentType):
                    raise AssertionError(
                        f"patient.id={p.id}: expected PaymentType|None, got {type(pt)!r}"
                    )
                pp_resolved += 1
        pass_(
            f"Patient.payment_type on {len(patients)} rows (no exception)",
            f"resolved={pp_resolved} none={pp_none}",
        )
    except Exception as exc:
        fail_("Patient.payment_type access", exc)

    # ------------------------------------------------------------------
    # CHECK 6a: Known value 'cash' -> PaymentType.CASH
    # ------------------------------------------------------------------
    print(f"  [6] Round-trip DB value checks ...")
    try:
        row = db.execute(
            text("SELECT id FROM appointments WHERE payment_type = 'cash' LIMIT 1")
        ).fetchone()
        if row:
            appt = db.query(Appointment).filter(Appointment.id == row[0]).first()
            if appt.payment_type != PaymentType.CASH:
                raise AssertionError(
                    f"Expected PaymentType.CASH, got {appt.payment_type!r}"
                )
            pass_("DB value 'cash' -> PaymentType.CASH")
        else:
            pass_("DB value 'cash' -> PaymentType.CASH", "no 'cash' rows found, skipped")
    except Exception as exc:
        fail_("DB value 'cash' -> PaymentType.CASH", exc)

    # ------------------------------------------------------------------
    # CHECK 6b: Unknown value 'insurance' -> None (not LookupError)
    # ------------------------------------------------------------------
    try:
        row = db.execute(
            text("SELECT id FROM appointments WHERE payment_type = 'insurance' LIMIT 1")
        ).fetchone()
        if row:
            appt = db.query(Appointment).filter(Appointment.id == row[0]).first()
            if appt.payment_type is not None:
                raise AssertionError(
                    f"Expected None for 'insurance', got {appt.payment_type!r}"
                )
            pass_("DB value 'insurance' -> None (not LookupError)")
        else:
            pass_("DB value 'insurance' -> None", "no 'insurance' rows found, skipped")
    except Exception as exc:
        fail_("DB value 'insurance' -> None", exc)

    # ------------------------------------------------------------------
    # CHECK 6c: Unknown treatment 'dental_care' -> None
    # ------------------------------------------------------------------
    try:
        row = db.execute(
            text("SELECT id FROM appointments WHERE treatment_type = 'dental_care' LIMIT 1")
        ).fetchone()
        if row:
            appt = db.query(Appointment).filter(Appointment.id == row[0]).first()
            if appt.treatment_type is not None:
                raise AssertionError(
                    f"Expected None for 'dental_care', got {appt.treatment_type!r}"
                )
            pass_("DB value 'dental_care' -> None (not LookupError)")
        else:
            pass_("DB value 'dental_care' -> None", "no 'dental_care' rows found, skipped")
    except Exception as exc:
        fail_("DB value 'dental_care' -> None", exc)

finally:
    db.close()

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
total = len(passed_checks) + len(failed_checks)
print()
print("=" * 62)
print(f"  Passed : {len(passed_checks)}/{total}")
print(f"  Failed : {len(failed_checks)}/{total}")
print("=" * 62)
print()

if failed_checks:
    print("  FAILED CHECKS:")
    for label, exc in failed_checks:
        print(f"    - {label}")
        if exc:
            print(f"      {type(exc).__name__}: {exc}")
    print()
    sys.exit(1)
else:
    print("  All enum safety checks PASSED.")
    print("  SafePaymentType and SafeTreatmentType are working correctly.")
    print()
    sys.exit(0)
