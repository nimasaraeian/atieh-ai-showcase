"""
seed_clinic_schedules.py
========================
Populates clinic_schedules with a standard working week for two concurrent
doctor shifts (morning + afternoon/evening).

Schedule design
---------------
Working days (Iranian dental-clinic calendar):
  Saturday  (Python weekday 5)
  Sunday    (Python weekday 6)
  Monday    (Python weekday 0)
  Tuesday   (Python weekday 1)
  Wednesday (Python weekday 2)
  Thursday  (Python weekday 3)  -- half-day for many clinics; included here

Two shifts per working day represent two simultaneous doctors (or two
booking lanes in one room):

  Shift A – Morning    : 08:00 - 13:00  (doctor 1)
  Shift B – Afternoon  : 14:00 - 19:00  (doctor 2)

This gives 6 days × 2 shifts = 12 active schedule rows, which covers the
next 14 days (and any future date) without modification.

Idempotency
-----------
Each candidate row is identified by (day_of_week, start_time).  If that pair
already exists the row is skipped regardless of any other field value.  Safe
to run multiple times.

Usage
-----
  python scripts/seed_clinic_schedules.py
  python scripts/seed_clinic_schedules.py --dry-run   # prints plan, no DB write
  python scripts/seed_clinic_schedules.py --reset      # deletes ALL rows first
"""

import os
import sys
import argparse
from datetime import datetime, timezone

# Make sure repo root is on sys.path.
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

from database import SessionLocal
from models import ClinicSchedule


# ---------------------------------------------------------------------------
# Schedule definition
# ---------------------------------------------------------------------------

# Python weekday numbers for the Iranian work week (Sat–Thu)
WORK_DAYS: list[int] = [5, 6, 0, 1, 2, 3]   # Sat Sun Mon Tue Wed Thu

DAY_NAMES: dict[int, str] = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday",  5: "Saturday", 6: "Sunday",
}

# (start_time, end_time) pairs – one entry per doctor / booking lane per day
SHIFTS: list[tuple[str, str]] = [
    ("08:00", "13:00"),   # Doctor A – morning
    ("14:00", "19:00"),   # Doctor B – afternoon / evening
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------

def _build_rows() -> list[dict]:
    """Return the full list of schedule rows that should exist."""
    rows = []
    for day in WORK_DAYS:
        for start_time, end_time in SHIFTS:
            rows.append({
                "day_of_week": day,
                "start_time":  start_time,
                "end_time":    end_time,
                "is_active":   1,
            })
    return rows


def seed(dry_run: bool = False, reset: bool = False) -> None:
    db = SessionLocal()
    inserted = skipped = deleted = 0

    try:
        if reset:
            if dry_run:
                existing = db.query(ClinicSchedule).count()
                print(f"  [DRY-RUN] Would delete {existing} existing rows.")
            else:
                deleted = db.query(ClinicSchedule).delete()
                db.commit()
                print(f"  [RESET] Deleted {deleted} existing rows.")

        rows = _build_rows()
        print(f"\n  Schedule plan: {len(rows)} rows "
              f"({len(WORK_DAYS)} days x {len(SHIFTS)} shifts)")
        print()

        for row in rows:
            day_name = DAY_NAMES[row["day_of_week"]]
            label = f"  day={day_name:<10} shift={row['start_time']}-{row['end_time']}"

            if dry_run:
                print(f"{label}  [DRY-RUN] would insert")
                inserted += 1
                continue

            existing = (
                db.query(ClinicSchedule)
                .filter(
                    ClinicSchedule.day_of_week == row["day_of_week"],
                    ClinicSchedule.start_time  == row["start_time"],
                )
                .first()
            )

            if existing:
                print(f"{label}  [SKIP] already exists (id={existing.id})")
                skipped += 1
            else:
                schedule = ClinicSchedule(
                    day_of_week = row["day_of_week"],
                    start_time  = row["start_time"],
                    end_time    = row["end_time"],
                    is_active   = row["is_active"],
                    created_at  = datetime.now(timezone.utc),
                )
                db.add(schedule)
                print(f"{label}  [INSERT]")
                inserted += 1

        if not dry_run:
            db.commit()

        print()
        print(f"  Done: inserted={inserted}  skipped={skipped}  deleted={deleted}")
        total = db.query(ClinicSchedule).count()
        print(f"  Total rows in clinic_schedules: {total}")
        active = db.query(ClinicSchedule).filter(ClinicSchedule.is_active == 1).count()
        print(f"  Active rows : {active}")

    except Exception as exc:
        db.rollback()
        print(f"  ERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed clinic_schedules table.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be inserted without writing to DB.")
    parser.add_argument("--reset", action="store_true",
                        help="Delete ALL existing rows before inserting.")
    args = parser.parse_args()

    print()
    print("=" * 56)
    print("  seed_clinic_schedules.py")
    if args.dry_run:
        print("  Mode: DRY-RUN (no DB changes)")
    elif args.reset:
        print("  Mode: RESET + seed")
    else:
        print("  Mode: idempotent seed")
    print("=" * 56)
    print()

    seed(dry_run=args.dry_run, reset=args.reset)
    print()
