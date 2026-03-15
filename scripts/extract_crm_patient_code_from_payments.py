# -*- coding: utf-8 -*-
import re
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("atieh_clinic_recovery81_test.db")
XLSX_PATH = Path(r"data/inputs/payments/payments_1403_full.xlsx")

CRM_PATTERN = re.compile(r"\((\d+)\)")

def extract_code(name):
    if not isinstance(name, str):
        return None
    m = CRM_PATTERN.search(name)
    return m.group(1) if m else None

def clean_name(name):
    if not isinstance(name, str):
        return None
    return re.sub(r"\(\d+\)", "", name).strip()

def normalize_text(s):
    if s is None:
        return ""
    return str(s).strip().replace("ي","ی").replace("ك","ک")

def find_name_column(df):
    cols = list(df.columns)
    normalized = {c: normalize_text(c) for c in cols}

    preferred = [
        "نام بیمار",
        "نام بيمار",
        "بيمار",
        "بیمار"
    ]
    for c, nc in normalized.items():
        if nc in preferred:
            return c

    for c, nc in normalized.items():
        if "نام" in nc and "بیمار" in nc:
            return c

    for c, nc in normalized.items():
        if "نام" in nc and "بيمار" in nc:
            return c

    raise Exception("Patient name column not found. Available columns: " + " | ".join(map(str, cols)))

def main():
    print("Loading Excel...")
    df = pd.read_excel(XLSX_PATH)

    name_col = find_name_column(df)
    print("Using column:", repr(name_col))

    df["crm_patient_code"] = df[name_col].apply(extract_code)
    df["patient_name_clean"] = df[name_col].apply(clean_name)

    df = df[df["crm_patient_code"].notnull()].copy()

    print("Extracted rows:", len(df))

    conn = sqlite3.connect(DB_PATH)

    conn.execute("DROP TABLE IF EXISTS payments_crm_code_extracted")
    conn.execute("""
    CREATE TABLE payments_crm_code_extracted (
        id INTEGER PRIMARY KEY,
        crm_patient_code TEXT,
        patient_name_clean TEXT,
        raw_name TEXT
    );
    """)

    rows = [
        (
            str(r["crm_patient_code"]) if r["crm_patient_code"] is not None else None,
            r["patient_name_clean"],
            r[name_col]
        )
        for _, r in df.iterrows()
    ]

    conn.executemany(
        """
        INSERT INTO payments_crm_code_extracted
        (crm_patient_code, patient_name_clean, raw_name)
        VALUES (?, ?, ?)
        """,
        rows
    )

    conn.commit()
    conn.close()

    print("Done.")

if __name__ == "__main__":
    main()
