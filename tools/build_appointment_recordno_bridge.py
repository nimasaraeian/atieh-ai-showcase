#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2: Build appointment_recordno_bridge from scheduling Excel files.
Extracts record_no (from column or from "Name(record_no)" in name), normalizes name/phone/date.
Idempotent: truncates bridge table then repopulates.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

DB_PATH = REPO / "atieh_clinic.db"

# Same file list as import_history_batch (relative to REPO)
HISTORY_FILES = [
    ("data/inputs/history/1395/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1395.xlsx", 1395),
    ("data/inputs/history/1396/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1396.xlsx", 1396),
    ("data/inputs/history/1398/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1398.xlsx", 1398),
    ("data/inputs/history/1399/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1399.xlsx", 1399),
    ("data/inputs/history/1400/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1400.xlsx", 1400),
    ("data/inputs/history/1401/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1401.xlsx", 1401),
    ("data/inputs/history/1402/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1402.xlsx", 1402),
    ("data/inputs/history/1403/نوبت_دهی_بیمارانی_که_حضور_پیدا_کردند_1403.xlsx", 1403),
    ("data/inputs/history/1404/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx", 1404),
]

RECORD_NO_HEADERS = [
    "پرونده", "شماره پرونده", "کد پرونده", "record_no", "record no",
    "شماره پرونده", "file number", "کد بیمار",
]
NAME_HEADERS = [
    "نام بیمار", "نام بيمار", "نام و نام خانوادگی", "نام بیمار(تشکیل پرونده شده)",
    "نام بيمار(تشكيل پرونده شده)",
]
PHONE_HEADERS = ["موبایل", "موبايل", "تلفن", "شماره تماس", "تلفن همراه", "شماره موبایل"]
DATE_HEADERS = ["تاریخ", "تاريخ", "تاریخ نوبت", "تاریخ ویزیت", "تاریخ مراجعه"]


def _norm_header(s) -> str:
    if s is None:
        return ""
    t = str(s).strip().replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return " ".join(t.split())


def _find_col(raw_columns: list, candidates: list) -> str | None:
    col_norm = {c: _norm_header(c) for c in raw_columns}
    for col in raw_columns:
        n = col_norm[col]
        for cand in candidates:
            if _norm_header(cand) in n or n in _norm_header(cand):
                return col
    return None


def _norm_name(s) -> str:
    if s is None or (isinstance(s, float) and str(s) == "nan"):
        return ""
    t = str(s).strip().replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    t = re.sub(r"\s*\(\d+\)\s*$", "", t)  # strip trailing (record_no) for matching to patients
    return " ".join(t.split())


def _norm_phone(s) -> str | None:
    if s is None or (isinstance(s, float) and str(s) == "nan"):
        return None
    digits = "".join(c for c in str(s) if c.isdigit())
    if not digits:
        return None
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    if len(digits) > 11:
        digits = digits[-11:]
    if len(digits) < 10:
        return None
    return digits


def _extract_record_no_from_name(val) -> str | None:
    if val is None or (isinstance(val, float) and str(val) == "nan"):
        return None
    s = str(val).strip()
    m = re.search(r"\((\d+)\)\s*$", s)
    return m.group(1) if m else None


def _extract_year_from_date(val) -> int | None:
    if not val:
        return None
    s = str(val).strip()
    m = re.search(r"13\d{2}", s)
    if m:
        return int(m.group(0))
    m = re.search(r"14\d{2}", s)
    if m:
        return int(m.group(0))
    return None


def ensure_schema(conn):
    mig = REPO / "app" / "db" / "migrations" / "013_appointment_recordno_bridge.sql"
    if mig.exists():
        with open(mig, encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    import sqlite3
    import pandas as pd

    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    cur = conn.cursor()

    cur.execute("DELETE FROM appointment_recordno_bridge")
    conn.commit()

    total_inserted = 0
    # 1) From appointment/scheduling Excel files (if they contain record_no in name or column)
    for rel_path, year_hint in HISTORY_FILES:
        path = REPO / rel_path
        if not path.exists():
            print(f"SKIP (not found): {rel_path}")
            continue
        fname = path.name
        try:
            df = pd.read_excel(path, sheet_name=0, header=0, engine="openpyxl", dtype=str)
        except Exception as e:
            print(f"ERROR reading {rel_path}: {e}")
            continue

        raw_columns = list(df.columns)
        col_record = _find_col(raw_columns, RECORD_NO_HEADERS)
        col_name = _find_col(raw_columns, NAME_HEADERS)
        col_phone = _find_col(raw_columns, PHONE_HEADERS)
        col_date = _find_col(raw_columns, DATE_HEADERS)

        if not col_name:
            print(f"SKIP {rel_path}: no patient name column")
            continue

        sheet_name = "Sheet0"  # first sheet
        for idx, row in df.iterrows():
            source_row = idx + 2
            record_no = None
            if col_record:
                v = row.get(col_record)
                if v is not None and str(v).strip():
                    record_no = str(v).strip()
            if not record_no and col_name:
                record_no = _extract_record_no_from_name(row.get(col_name))
            if not record_no:
                continue
            name_raw = str(row.get(col_name, "") or "").strip()
            name_norm = _norm_name(name_raw) if name_raw else ""
            phone_raw = str(row.get(col_phone, "") or "").strip() if col_phone else ""
            phone_norm = _norm_phone(phone_raw) if phone_raw else None
            date_raw = str(row.get(col_date, "") or "").strip() if col_date else ""
            year = _extract_year_from_date(date_raw) or year_hint

            if not name_norm and not phone_norm:
                continue

            try:
                cur.execute("""
                    INSERT OR IGNORE INTO appointment_recordno_bridge
                    (source_file, source_sheet, source_row, record_no,
                     patient_name_raw, patient_name_norm, phone_raw, phone_norm,
                     appointment_date_raw, appointment_year, evidence_type)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    fname, sheet_name, source_row, record_no,
                    name_raw or None, name_norm or None, phone_raw or None, phone_norm,
                    date_raw or None, year, "appointment_file_record_no"
                ))
                if cur.rowcount:
                    total_inserted += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        print(f"Processed {rel_path}: rows with record_no -> bridge")

    # 2) Seed from payments_clean (financial data has record_no in 100% of rows)
    try:
        pay_rows = cur.execute("""
            SELECT record_no, patient_name_raw, phone_raw, appointment_date_raw
            FROM payments_clean
            WHERE record_no IS NOT NULL AND TRIM(record_no) <> ''
            GROUP BY record_no
        """).fetchall()
        for i, (record_no, name_raw, phone_raw, date_raw) in enumerate(pay_rows):
            name_norm = _norm_name(name_raw) if name_raw else ""
            phone_norm = _norm_phone(phone_raw) if phone_raw else None
            year = _extract_year_from_date(date_raw)
            if not name_norm and not phone_norm:
                continue
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO appointment_recordno_bridge
                    (source_file, source_sheet, source_row, record_no,
                     patient_name_raw, patient_name_norm, phone_raw, phone_norm,
                     appointment_date_raw, appointment_year, evidence_type)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    "payments_clean", "n/a", i + 1, record_no,
                    name_raw or None, name_norm or None, phone_raw or None, phone_norm,
                    date_raw or None, year, "financial_record_no"
                ))
                if cur.rowcount:
                    total_inserted += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        print(f"Seeded from payments_clean: {len(pay_rows)} distinct record_no (inserted where not already in bridge)")
    except sqlite3.OperationalError as e:
        print(f"payments_clean not available: {e}")

    distinct_rec = cur.execute("SELECT COUNT(DISTINCT record_no) FROM appointment_recordno_bridge").fetchone()[0]
    total_rows = cur.execute("SELECT COUNT(*) FROM appointment_recordno_bridge").fetchone()[0]
    print(f"\nBridge built: {total_rows} rows, {distinct_rec} distinct record_no")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
