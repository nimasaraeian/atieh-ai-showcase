#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1: Discover record_no (file/chart number) in appointment/scheduling Excel files.
Scans history, reference, and appointment directories; reports columns and sample rows.
Does NOT modify source files.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Repo root
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Column header keywords that suggest record_no / file number / chart number
# NOTE: "شماره نوبت" = appointment number (per-day slot), NOT patient file number - exclude it
RECORD_NO_CANDIDATES = [
    "record_no", "record no", "recordno",
    "پرونده", "شماره پرونده", "کد پرونده",
    "file number", "fileno", "file_no", "chart", "chart number",
    "patient code", "کد بیمار", "شماره بیمار",
    "كد پرونده", "شماره پرونده",
]
# Explicitly NOT record_no (appointment/slot number):
NOT_RECORD_NO = ["شماره نوبت", "شماره نوبت"]

PATIENT_NAME_CANDIDATES = [
    "نام بیمار", "نام بيمار", "نام و نام خانوادگی", "patient", "name",
    "نام بیمار(تشکیل پرونده شده)", "نام بيمار(تشكيل پرونده شده)",
]

PHONE_CANDIDATES = [
    "موبایل", "موبايل", "تلفن", "شماره تماس", "phone", "تلفن همراه", "شماره موبایل",
]

DATE_CANDIDATES = [
    "تاریخ", "تاريخ", "تاریخ نوبت", "تاریخ ویزیت", "date", "تاریخ مراجعه",
]


def _norm_header(s: str) -> str:
    if s is None:
        return ""
    t = str(s).strip().replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return " ".join(t.split()).lower()


def _header_matches(header: str, candidates: list[str], exclude: list[str] | None = None) -> bool:
    n = _norm_header(header)
    for ex in (exclude or []):
        if _norm_header(ex) in n or n in _norm_header(ex):
            return False
    for c in candidates:
        if _norm_header(c) in n or n in _norm_header(c):
            return True
    return False


def _find_column(raw_columns: list[str], candidates: list[str]) -> str | None:
    for col in raw_columns:
        if _header_matches(col, candidates):
            return col
    return None


def _extract_record_no_from_name(val) -> str | None:
    """Extract (digits) from end of patient name, e.g. 'احمد محمدی(100001)' -> '100001'."""
    if val is None or (hasattr(val, "__float__") and str(val) == "nan"):
        return None
    s = str(val).strip()
    m = re.search(r"\((\d+)\)\s*$", s)
    return m.group(1) if m else None


def discover_file(excel_path: Path) -> dict:
    import pandas as pd

    out = {
        "path": str(excel_path),
        "exists": excel_path.exists(),
        "sheets": [],
        "probable_record_no_column": None,
        "probable_patient_name_column": None,
        "probable_phone_column": None,
        "probable_date_column": None,
        "all_columns_by_sheet": {},
        "sample_rows": [],
        "record_no_from_name": None,
    }
    if not excel_path.exists():
        return out

    try:
        xl = pd.ExcelFile(excel_path, engine="openpyxl")
        out["sheets"] = xl.sheet_names
    except Exception as e:
        out["error"] = str(e)
        return out

    for sheet_name in xl.sheet_names:
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0, engine="openpyxl", dtype=str)
        except Exception as e:
            out.setdefault("sheet_errors", {})[sheet_name] = str(e)
            continue

        raw_columns = list(df.columns)
        out["all_columns_by_sheet"][sheet_name] = raw_columns

        if not out["probable_record_no_column"]:
            for col in raw_columns:
                if _header_matches(col, RECORD_NO_CANDIDATES, exclude=NOT_RECORD_NO):
                    out["probable_record_no_column"] = (sheet_name, col)
                    break
        if not out["probable_patient_name_column"]:
            name_col = _find_column(raw_columns, PATIENT_NAME_CANDIDATES)
            if name_col:
                out["probable_patient_name_column"] = (sheet_name, name_col)
        if not out["probable_phone_column"]:
            phone_col = _find_column(raw_columns, PHONE_CANDIDATES)
            if phone_col:
                out["probable_phone_column"] = (sheet_name, phone_col)
        if not out["probable_date_column"]:
            date_col = _find_column(raw_columns, DATE_CANDIDATES)
            if date_col:
                out["probable_date_column"] = (sheet_name, date_col)

        # Sample: check if record_no can be parsed from name
        name_col = _find_column(raw_columns, PATIENT_NAME_CANDIDATES)
        if name_col and sheet_name == xl.sheet_names[0]:
            sample = df.head(10)
            out["sample_rows"] = []
            for _, row in sample.iterrows():
                r = {}
                for c in raw_columns[:15]:  # first 15 cols
                    v = row.get(c)
                    if v is not None and str(v).strip():
                        r[str(c)] = str(v)[:80]
                out["sample_rows"].append(r)
            # Check first non-empty name for (number)
            for _, row in df.iterrows():
                val = row.get(name_col) if name_col else None
                rn = _extract_record_no_from_name(val)
                if rn:
                    out["record_no_from_name"] = "yes"
                    break
            if out["record_no_from_name"] is None:
                out["record_no_from_name"] = "no"
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    dirs_to_scan = [
        REPO / "data" / "inputs" / "history",
        REPO / "data" / "inputs" / "reference",
        REPO / "data" / "inputs" / "appointments",
    ]

    all_files: list[Path] = []
    for d in dirs_to_scan:
        if d.exists():
            all_files.extend(d.rglob("*.xlsx"))

    all_files = sorted(set(all_files))
    print("=" * 70)
    print("PHASE 1 — RECORD_NO DISCOVERY IN APPOINTMENT/SCHEDULING FILES")
    print("=" * 70)
    print(f"Directories scanned: {[str(d) for d in dirs_to_scan]}")
    print(f"Excel files found: {len(all_files)}\n")

    for fp in all_files:
        rep = discover_file(fp)
        print("-" * 70)
        print(f"FILE: {rep['path']}")
        print(f"EXISTS: {rep['exists']}")
        if rep.get("error"):
            print(f"ERROR: {rep['error']}")
            continue
        print(f"SHEETS: {rep['sheets']}")
        for sh, cols in rep.get("all_columns_by_sheet", {}).items():
            print(f"  Sheet '{sh}' columns: {cols[:20]}{'...' if len(cols) > 20 else ''}")
        print(f"PROBABLE RECORD_NO COLUMN: {rep.get('probable_record_no_column')}")
        print(f"PROBABLE PATIENT NAME COLUMN: {rep.get('probable_patient_name_column')}")
        print(f"PROBABLE PHONE COLUMN: {rep.get('probable_phone_column')}")
        print(f"PROBABLE DATE COLUMN: {rep.get('probable_date_column')}")
        print(f"RECORD_NO PARSABLE FROM NAME (e.g. 'Name(12345)'): {rep.get('record_no_from_name')}")
        if rep.get("sample_rows"):
            print("SAMPLE ROWS (first 10, first 15 cols):")
            for i, row in enumerate(rep["sample_rows"][:10]):
                print(f"  Row {i+1}: {row}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
