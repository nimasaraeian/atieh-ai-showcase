# -*- coding: utf-8 -*-
"""
Populate insurance_priority_rank from Excel reference:
  data/inputs/reference/تاریخ پرداختی بیمه ها.xlsx

Columns: نام بیمه, یک ماه, دو ماه, سه ماه, چهار ماه, بیشتر از 5 ماه
The column containing "*" defines the payment speed group.

Payment groups → priority_score:
  one_month    → 90
  two_month    → 75
  three_month  → 60
  four_month   → 45
  more_than_5  → 25

Run: python scripts/populate_insurance_priority_from_excel.py
"""
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
EXCEL_PATH = REPO / "data" / "inputs" / "reference" / "تاریخ پرداختی بیمه ها.xlsx"

# Map Excel column headers (Persian) to payment_speed_group
COL_TO_GROUP = {
    "یک ماه": "one_month",
    "دو ماه": "two_month",
    "سه ماه": "three_month",
    "چهار ماه": "four_month",
    "بیشتر از 5 ماه": "more_than_5",
    "بیشتر از ۵ ماه": "more_than_5",
}

GROUP_TO_SCORE = {
    "one_month": 90,
    "two_month": 75,
    "three_month": 60,
    "four_month": 45,
    "more_than_5": 25,
}

NAME_COL = "نام بیمه"
STAR = "*"


def get_db_path() -> str:
    db_url = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    if db_url.startswith("sqlite:///"):
        return db_url[len("sqlite:///"):]
    return db_url


def load_from_excel() -> list[tuple[str, str, int]]:
    """Load (insurance_name, payment_speed_group, priority_score) from Excel."""
    if not EXCEL_PATH.exists():
        print(f"[ERROR] Excel file not found: {EXCEL_PATH}")
        return []

    df = pd.read_excel(EXCEL_PATH, sheet_name=0, engine="openpyxl", dtype=str)

    # Normalize column names (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]

    if NAME_COL not in df.columns:
        # Try first column as name
        name_col = df.columns[0]
        df = df.rename(columns={name_col: NAME_COL})
    else:
        name_col = NAME_COL

    rows = []
    for _, row in df.iterrows():
        name_raw = row.get(name_col)
        if pd.isna(name_raw) or not str(name_raw).strip():
            continue

        insurance_name = str(name_raw).strip()

        # Find column with "*"
        payment_speed_group = None
        for col in df.columns:
            if col == name_col:
                continue
            val = row.get(col)
            if pd.isna(val):
                continue
            if STAR in str(val):
                # Map column to group
                payment_speed_group = COL_TO_GROUP.get(col)
                if not payment_speed_group and col in COL_TO_GROUP:
                    payment_speed_group = COL_TO_GROUP[col]
                break

        if not payment_speed_group:
            payment_speed_group = "more_than_5"  # default
        priority_score = GROUP_TO_SCORE.get(payment_speed_group, 25)
        rows.append((insurance_name, payment_speed_group, priority_score))

    return rows


def populate_table(rows: list[tuple[str, str, int]]) -> int:
    db_path = get_db_path()
    if not Path(db_path).exists():
        print(f"[ERROR] Database not found: {db_path}")
        return 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Ensure table exists (migration may have created it)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS insurance_priority_rank (
          insurance_name      TEXT PRIMARY KEY,
          payment_speed_group TEXT,
          priority_score      INTEGER
        )
    """)

    cur.execute("DELETE FROM insurance_priority_rank")
    for insurance_name, payment_speed_group, priority_score in rows:
        cur.execute(
            "INSERT OR REPLACE INTO insurance_priority_rank (insurance_name, payment_speed_group, priority_score) VALUES (?, ?, ?)",
            (insurance_name, payment_speed_group, priority_score),
        )
    conn.commit()
    count = cur.rowcount if hasattr(cur, "rowcount") else len(rows)
    conn.close()
    return len(rows)


def main():
    rows = load_from_excel()
    if not rows:
        print("[WARN] No rows loaded from Excel. Ensure file exists and has correct columns.")
        sys.exit(1)

    n = populate_table(rows)
    print(f"[OK] Populated insurance_priority_rank with {n} rows.")


if __name__ == "__main__":
    main()
