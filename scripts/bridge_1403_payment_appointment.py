# -*- coding: utf-8 -*-
"""
1403-specific bridge pipeline: link payments to appointments by date + name + phone.

Bridges:
- payments_1403_full.xlsx (ØªØ§Ø±ÙŠØ® Ù¾Ø°ÙŠØ±Ø´, Ø´Ù…Ø§Ø±Ù‡ Ù¾Ø±ÙˆÙ†Ø¯Ù‡, Ù†Ø§Ù… Ø¨ÛŒÙ…Ø§Ø±, Ù…ÙˆØ¨Ø§ÛŒÙ„)
- appointments in data/inputs/history/1403/*.xlsx (ØªØ§Ø±ÙŠØ® Ù†ÙˆØ¨Øª, Ù†Ø§Ù… Ø¨ÛŒÙ…Ø§Ø±, Ù…ÙˆØ¨Ø§ÛŒÙ„/ØªÙ„ÙÙ†)

Does NOT use Ø´Ù…Ø§Ø±Ù‡ Ù†ÙˆØ¨Øª (unusable: mostly 0/null).

PowerShell commands to run:
  cd C:\\Users\\USER\\Documents\\GitHub\\atieh
  python scripts/bridge_1403_payment_appointment.py

Or from any directory:
  python "<repo_path>/scripts/bridge_1403_payment_appointment.py"
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import pandas as pd

# Column candidates
PAYMENT_DATE_HEADERS = ["تاریخ پذیرش", "تاريخ پذيرش", "تاریخ", "تاريخ"]
PAYMENT_NAME_HEADERS = ["نام بیمار", "نام بيمار", "نام بیمار(تشکیل پرونده شده)"]
PAYMENT_PHONE_HEADERS = ["موبایل", "موبايل", "تلفن", "شماره تماس"]
PAYMENT_RECORDNO_HEADERS = ["شماره پرونده", "کد پرونده", "record_no", "پرونده"]

APPT_DATE_HEADERS = ["تاریخ نوبت", "تاريخ نوبت", "تاریخ", "تاريخ"]
APPT_NAME_HEADERS = [
    "نام بیمار(تشکیل پرونده شده)",
    "نام بيمار(تشكيل پرونده شده)",
    "نام و نام خانوادگی",
    "نام بیمار",
    "نام بيمار",
]
APPT_PHONE_HEADERS = ["موبایل", "موبايل", "تلفن", "شماره تماس", "تلفن همراه"]


def _norm_header(s) -> str:
    if s is None:
        return ""
    t = str(s).strip()
    if len(t) >= 2 and t[0] == "'" and t[-1] == "'":
        t = t[1:-1].strip()
    t = t.replace("|", " ").replace("ÙŠ", "ÛŒ").replace("Ùƒ", "Ú©").replace("\u200c", " ")
    return " ".join(t.split())


def _find_col(col_index: dict, candidates: list) -> str | None:
    for cand in candidates:
        n = _norm_header(cand)
        if n in col_index:
            return col_index[n]
    for cand in candidates:
        n = _norm_header(cand)
        for k in col_index:
            if len(k) >= 8 and (n in k or k in n):
                return col_index[k]
    return None


def normalize_name(s) -> str:
    """Strip trailing (record_no), unify ÙŠ/ÛŒ and Ùƒ/Ú©, collapse spaces."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip()
    if t in ("", "nan", "None"):
        return ""
    t = re.sub(r"\s*\(\d+\)\s*$", "", t)
    t = re.sub(r"\s*\(ØªØ´Ú©ÛŒÙ„ Ù¾Ø±ÙˆÙ†Ø¯Ù‡ Ø´Ø¯Ù‡\)\s*$", "", t, flags=re.IGNORECASE)
    t = t.replace("ÙŠ", "ÛŒ").replace("Ùƒ", "Ú©").strip()
    t = " ".join(t.split())
    return t


def _normalize_digits(s: str) -> str:
    """Convert Persian/Arabic digits to English."""
    persian = "Û°Û±Û²Û³Û´ÛµÛ¶Û·Û¸Û¹"
    arabic = "Ù Ù¡Ù¢Ù£Ù¤Ù¥Ù¦Ù§Ù¨Ù©"
    for i, p in enumerate(persian):
        s = s.replace(p, str(i))
    for i, a in enumerate(arabic):
        s = s.replace(a, str(i))
    return s


def normalize_phones(raw: str | None) -> set[str]:
    """
    Split phone-like cells into a clean set of valid Iranian mobile numbers.

    Keep only:
    - 11 digits
    - starts with 09

    Supports common variants:
    - +98xxxxxxxxxx
    - 98xxxxxxxxxx
    - 9xxxxxxxxx
    - 09xxxxxxxxx

    Drops junk like:
    - 0 / 1
    - short numbers
    - treatment text
    - mixed notes
    """
    out = set()
    if not raw or (isinstance(raw, float) and pd.isna(raw)):
        return out

    s = str(raw).strip()
    if not s:
        return out

    s = _normalize_digits(s)

    # split on common separators
    parts = re.split(r"[;ØŒ,/|\s]+", s)

    for p in parts:
        token = str(p).strip()
        if not token:
            continue

        digits = "".join(c for c in token if c.isdigit())
        if not digits:
            continue

        # convert +98 / 98 prefix to local mobile format
        if digits.startswith("98") and len(digits) >= 12:
            digits = "0" + digits[2:]

        # convert 9xxxxxxxxx to 09xxxxxxxxx
        if len(digits) == 10 and digits.startswith("9"):
            digits = "0" + digits

        # keep ONLY strict valid mobile numbers
        if len(digits) == 11 and digits.startswith("09"):
            out.add(digits)

    return out


def normalize_date_key(val) -> str | None:
    """Parse Shamsi date and return YYYY/MM/DD key for matching."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s:
        return None
    # Persian/Arabic digits -> English
    persian = "Û°Û±Û²Û³Û´ÛµÛ¶Û·Û¸Û¹"
    arabic = "Ù Ù¡Ù¢Ù£Ù¤Ù¥Ù¦Ù§Ù¨Ù©"
    for i, p in enumerate(persian):
        s = s.replace(p, str(i))
    for i, a in enumerate(arabic):
        s = s.replace(a, str(i))
    # Match YYYY/MM/DD or YYYY-MM-DD or YYYY.MM.DD
    m = re.search(r"(13\d{2}|14\d{2})[/\-.\s]+(\d{1,2})[/\-.\s]+(\d{1,2})", s)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y}/{mo}/{d}"
    return None


def extract_record_no(row: dict, col_recordno: str | None, col_name: str | None) -> str | None:
    """Get record_no from column or from Name(record_no) suffix."""
    if col_recordno and row.get(col_recordno):
        v = str(row[col_recordno]).strip()
        if v and v != "nan":
            return v
    if col_name:
        s = str(row.get(col_name, "") or "").strip()
        m = re.search(r"\((\d+)\)\s*$", s)
        if m:
            return m.group(1)
    return None


def load_payments(path: Path) -> tuple[pd.DataFrame, dict]:
    """Load payments Excel, return (df with normalized columns, col_map)."""
    sheet = "MSExcel"
    try:
        df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl", dtype=str)
    except Exception:
        df = pd.read_excel(path, sheet_name=0, engine="openpyxl", dtype=str)
        df.columns = [
            str(c).strip().strip("'").strip('"').replace("ي", "ی").replace("ك", "ک")
            for c in df.columns
        ]
    
    # CLEAN HEADER NAMES (remove quotes + normalize Persian letters)
    df.columns = [
        str(c)
        .replace("'", "")
        .replace('"', "")
        .strip()
        .replace("ي","ی")
        .replace("ك","ک")
        for c in df.columns
    ]

    col_index = {_norm_header(c): c for c in df.columns}

    c_date = _find_col(col_index, PAYMENT_DATE_HEADERS)
    c_name = _find_col(col_index, PAYMENT_NAME_HEADERS)

    # fallback: accept any column containing "نام بیمار"
    if not c_name:
        for c in df.columns:
            s = str(c).strip().replace("ي", "ی").replace("ك", "ک")
            if "نام بیمار" in s or "نام بيمار" in s:
                c_name = c
                break

    c_phone = _find_col(col_index, PAYMENT_PHONE_HEADERS)
    c_recordno = _find_col(col_index, PAYMENT_RECORDNO_HEADERS)
    if not c_name:
        raise ValueError(f"Payment file: name column not found. Columns: {list(df.columns)[:15]}")
    col_map = {"date": c_date, "name": c_name, "phone": c_phone, "recordno": c_recordno}
    return df, col_map


def load_appointments(path: Path) -> tuple[pd.DataFrame, dict]:
    """Load appointments Excel, return (df, col_map)."""
    df = pd.read_excel(path, sheet_name=0, engine="openpyxl", dtype=str)
    
    # CLEAN HEADER NAMES (remove quotes + normalize Persian letters)
    df.columns = [
        str(c)
        .replace("'", "")
        .replace('"', "")
        .strip()
        .replace("ي","ی")
        .replace("ك","ک")
        for c in df.columns
    ]

    col_index = {_norm_header(c): c for c in df.columns}

    c_date = _find_col(col_index, APPT_DATE_HEADERS)
    c_name = _find_col(col_index, APPT_NAME_HEADERS)

    # fallback for 1403 appointment files
    if not c_name:
        preferred = [
            "نام بیمار(تشکیل پرونده شده)",
            "نام بیمار (تشکیل پرونده شده)",
            "نام بیمار(تشکیل پرونده نشده)",
            "نام بیمار (تشکیل پرونده نشده)",
            "نام بیمار",
            "نام بيمار",
        ]
        cols_norm = {
            str(c).strip().replace("ي", "ی").replace("ك", "ک"): c
            for c in df.columns
        }

        for key in preferred:
            k = key.strip().replace("ي", "ی").replace("ك", "ک")
            if k in cols_norm:
                c_name = cols_norm[k]
                break

        if not c_name:
            for c in df.columns:
                s = str(c).strip().replace("ي", "ی").replace("ك", "ک")
                if "نام بیمار" in s or "نام بيمار" in s:
                    c_name = c
                    break

    c_phone = _find_col(col_index, APPT_PHONE_HEADERS)
    if not c_name:
        raise ValueError(f"Appointment file: name column not found. Columns: {list(df.columns)[:15]}")
    col_map = {"date": c_date, "name": c_name, "phone": c_phone}
    return df, col_map


@dataclass
class PayRow:
    row_idx: int
    date_key: str | None
    name_norm: str
    phones: set[str]
    record_no: str | None
    name_raw: str
    phone_raw: str


@dataclass
class ApptRow:
    row_idx: int
    date_key: str | None
    name_norm: str
    phones: set[str]
    name_raw: str
    phone_raw: str


def build_pay_rows(df: pd.DataFrame, col_map: dict) -> list[PayRow]:
    rows = []
    for idx, r in df.iterrows():
        row_idx = int(idx) + 2  # 1-indexed + header
        date_key = normalize_date_key(r.get(col_map["date"]) if col_map["date"] else None)
        name_raw = str(r.get(col_map["name"], "") or "")
        name_norm = normalize_name(name_raw)
        phone_raw = str(r.get(col_map["phone"], "") or "")
        phones = normalize_phones(phone_raw)
        record_no = extract_record_no(
            r.to_dict(), col_map.get("recordno"), col_map.get("name")
        )
        rows.append(PayRow(row_idx, date_key, name_norm, phones, record_no, name_raw, phone_raw))
    return rows


def build_appt_rows(df: pd.DataFrame, col_map: dict) -> list[ApptRow]:
    rows = []
    for idx, r in df.iterrows():
        row_idx = int(idx) + 2
        date_key = normalize_date_key(r.get(col_map["date"]) if col_map["date"] else None)
        name_raw = str(r.get(col_map["name"], "") or "")
        name_norm = normalize_name(name_raw)
        phone_raw = str(r.get(col_map["phone"], "") or "")
        phones = normalize_phones(phone_raw)
        rows.append(ApptRow(row_idx, date_key, name_norm, phones, name_raw, phone_raw))
    return rows


def run_bridge(
    pay_rows: list[PayRow],
    appt_rows: list[ApptRow],
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Build matches in tiers A, B, C.
    Returns (accepted_matches, review_rows, patient_recordno_map_rows).
    """
    # Index appointments: by (date_key, name_norm) -> list of ApptRow
    appt_by_date_name: dict[tuple[str | None, str], list[ApptRow]] = defaultdict(list)
    for a in appt_rows:
        key = (a.date_key, a.name_norm)
        appt_by_date_name[key].append(a)

    # For tier B: check uniqueness on both sides
    pay_by_date_name: dict[tuple[str | None, str], list[PayRow]] = defaultdict(list)
    for p in pay_rows:
        if p.name_norm:
            key = (p.date_key, p.name_norm)
            pay_by_date_name[key].append(p)

    appt_by_name: dict[str, list[ApptRow]] = defaultdict(list)
    for a in appt_rows:
        if a.name_norm:
            appt_by_name[a.name_norm].append(a)

    accepted: list[dict] = []
    review: list[dict] = []
    recordno_map: dict[str, dict] = {}
    matched_pay_keys: set[tuple[int, str | None, str]] = set()
    seen_bridge: set[tuple[str, int]] = set()  # (record_no, appointment_row_idx) for dedup

    def _add_match(m: dict, method: str, conf: float) -> None:
        rn = m["record_no"]
        appt_idx = m.get("appointment_row_idx")
        if appt_idx is not None and (rn, appt_idx) not in seen_bridge:
            seen_bridge.add((rn, appt_idx))
            m["match_method"] = method
            m["confidence"] = conf
            normalized_appt_phone = ";".join(sorted(normalize_phones(m.get("appointment_phone") or "")))
            first_phone = normalized_appt_phone.split(";")[0].strip() if normalized_appt_phone else ""
            m["appointment_phone"] = normalized_appt_phone
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}"
            accepted.append(m)
        if rn not in recordno_map:
            recordno_map[rn] = {
                "record_no": rn,
                "payment_name_norm": m.get("payment_name_norm"),
                "appointment_name": m.get("appointment_name"),
                "appointment_phone": m.get("appointment_phone"),
                "match_method": method,
                "confidence": conf,
            }

    # Tier A: exact date + exact name + phone overlap
    for p in pay_rows:
        if not p.name_norm or not p.record_no:
            continue
        key = (p.date_key, p.name_norm)
        candidates = appt_by_date_name.get(key, [])
        with_phone = [a for a in candidates if p.phones and a.phones and (p.phones & a.phones)]
        if len(with_phone) == 1:
            a = with_phone[0]
            m = {
                "record_no": p.record_no,
                "payment_name_norm": p.name_norm,
                "appointment_name": a.name_raw,
                "appointment_phone": ";".join(sorted(a.phones)),
                "appointment_date_key": a.date_key,
                "payment_row_idx": p.row_idx,
                "appointment_row_idx": a.row_idx,
            }
            _add_match(m, "A", 1.0)
            matched_pay_keys.add((p.row_idx, p.date_key, p.name_norm))

    # Tier B: exact date + exact name, unique on both sides, no phone required
    for p in pay_rows:
        if (p.row_idx, p.date_key, p.name_norm) in matched_pay_keys:
            continue
        if not p.name_norm or not p.record_no or not p.date_key:
            continue
        key = (p.date_key, p.name_norm)
        pay_same = pay_by_date_name.get(key, [])
        appt_same = appt_by_date_name.get(key, [])
        if len(pay_same) == 1 and len(appt_same) == 1:
            a = appt_same[0]
            m = {
                "record_no": p.record_no,
                "payment_name_norm": p.name_norm,
                "appointment_name": a.name_raw,
                "appointment_phone": ";".join(sorted(a.phones)),
                "appointment_date_key": a.date_key,
                "payment_row_idx": p.row_idx,
                "appointment_row_idx": a.row_idx,
            }
            _add_match(m, "B", 0.9)
            matched_pay_keys.add((p.row_idx, p.date_key, p.name_norm))

    # Tier C: exact name + phone overlap even if date missing/weak
    for p in pay_rows:
        if (p.row_idx, p.date_key, p.name_norm) in matched_pay_keys:
            continue
        if not p.name_norm or not p.record_no or not p.phones:
            continue
        candidates = appt_by_name.get(p.name_norm, [])
        with_phone = [a for a in candidates if a.phones and (p.phones & a.phones)]
        if len(with_phone) == 1:
            a = with_phone[0]
            m = {
                "record_no": p.record_no,
                "payment_name_norm": p.name_norm,
                "appointment_name": a.name_raw,
                "appointment_phone": ";".join(sorted(a.phones)),
                "appointment_date_key": a.date_key,
                "payment_row_idx": p.row_idx,
                "appointment_row_idx": a.row_idx,
            }
            _add_match(m, "C", 0.8)
            matched_pay_keys.add((p.row_idx, p.date_key, p.name_norm))
        elif len(with_phone) > 1:
            review.append({
                "record_no": p.record_no,
                "payment_name_norm": p.name_norm,
                "review_reason": "tier_C_ambiguous",
                "reason": "tier_C_ambiguous",
                "candidate_count": len(with_phone),
            })

    # Unresolved: payment rows with record_no and name but no match (dedupe by record_no)
    matched_record_nos = {m["record_no"] for m in accepted}
    seen_unresolved = set()
    for p in pay_rows:
        if p.record_no and p.name_norm and p.record_no not in matched_record_nos:
            if p.record_no not in seen_unresolved:
                seen_unresolved.add(p.record_no)
                review.append({
                    "record_no": p.record_no,
                    "payment_name_norm": p.name_norm,
                    "review_reason": "unresolved",
                    "reason": "unresolved",
                    "candidate_count": 0,
                })

    patient_map_list = list(recordno_map.values())
    return accepted, review, patient_map_list


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS bridge_1403_payment_appointment;
        CREATE TABLE bridge_1403_payment_appointment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_no TEXT NOT NULL,
            appointment_patient_key TEXT NOT NULL,
            payment_name_norm TEXT,
            appointment_name TEXT,
            appointment_phone TEXT,
            appointment_date_key TEXT,
            match_method TEXT NOT NULL,
            confidence REAL NOT NULL,
            payment_row_idx INTEGER,
            appointment_row_idx INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(record_no, appointment_patient_key)
        );
        CREATE INDEX IF NOT EXISTS idx_bridge_1403_record_no ON bridge_1403_payment_appointment(record_no);
        CREATE INDEX IF NOT EXISTS idx_bridge_1403_match_method ON bridge_1403_payment_appointment(match_method);
        CREATE INDEX IF NOT EXISTS idx_bridge_1403_appt_patient_key ON bridge_1403_payment_appointment(appointment_patient_key);

        DROP TABLE IF EXISTS bridge_1403_review;
        CREATE TABLE bridge_1403_review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_no TEXT,
            payment_name_norm TEXT,
            review_reason TEXT NOT NULL,
            reason TEXT,
            candidate_count INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_bridge_1403_review_record_no ON bridge_1403_review(record_no);

        DROP TABLE IF EXISTS patient_recordno_map_1403;
        CREATE TABLE patient_recordno_map_1403 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_no TEXT NOT NULL UNIQUE,
            payment_name_norm TEXT,
            appointment_name TEXT,
            appointment_phone TEXT,
            match_method TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_patient_recordno_map_1403_record_no ON patient_recordno_map_1403(record_no);
    """)
    conn.commit()


def save_to_sqlite(
    conn: sqlite3.Connection,
    accepted: list[dict],
    review: list[dict],
    patient_map: list[dict],
) -> None:
    ensure_schema(conn)
    cur = conn.cursor()
    for m in accepted:
        cur.execute("""
            INSERT OR IGNORE INTO bridge_1403_payment_appointment
            (record_no, appointment_patient_key, payment_name_norm, appointment_name, appointment_phone,
             appointment_date_key, match_method, confidence, payment_row_idx, appointment_row_idx)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            m["record_no"], m.get("appointment_patient_key", ""),
            m["payment_name_norm"], m["appointment_name"], m["appointment_phone"],
            m["appointment_date_key"], m["match_method"], m["confidence"],
            m.get("payment_row_idx"), m.get("appointment_row_idx"),
        ))
    for r in review:
        cur.execute("""
            INSERT INTO bridge_1403_review (record_no, payment_name_norm, review_reason, reason, candidate_count)
            VALUES (?,?,?,?,?)
        """, (r.get("record_no"), r.get("payment_name_norm"),
              r.get("review_reason") or r.get("reason", "unknown"), r.get("reason"),
              r.get("candidate_count", 0)))
    for pm in patient_map:
        cur.execute("""
            INSERT OR REPLACE INTO patient_recordno_map_1403
            (record_no, payment_name_norm, appointment_name, appointment_phone, match_method, confidence)
            VALUES (?,?,?,?,?,?)
        """, (
            pm["record_no"], pm["payment_name_norm"], pm["appointment_name"],
            pm["appointment_phone"], pm["match_method"], pm["confidence"],
        ))
    conn.commit()


def print_stats(
    pay_rows: list[PayRow],
    appt_rows: list[ApptRow],
    accepted: list[dict],
    review: list[dict],
    patient_map: list[dict],
) -> None:
    total_pay = len(pay_rows)
    total_appt = len(appt_rows)
    by_tier = defaultdict(int)
    for m in accepted:
        by_tier[m["match_method"]] += 1
    distinct_record_no = len({m["record_no"] for m in accepted})
    distinct_patients = len(patient_map)

    # Unresolved payment names (have record_no and name but no match)
    matched_record_nos = {m["record_no"] for m in accepted}
    unresolved_names = set()
    for p in pay_rows:
        if p.record_no and p.name_norm and p.record_no not in matched_record_nos:
            unresolved_names.add(p.name_norm)

    # Top ambiguous (tier_C_ambiguous or similar)
    ambiguous = [r for r in review if r.get("review_reason") == "tier_C_ambiguous" and r.get("candidate_count", 0) > 1]
    ambiguous = sorted(ambiguous, key=lambda x: -x.get("candidate_count", 0))[:10]

    print()
    print("=" * 70)
    print("1403 BRIDGE PIPELINE RESULTS")
    print("=" * 70)
    print(f"Total payment rows:        {total_pay:,}")
    print(f"Total appointment rows:    {total_appt:,}")
    print()
    print("Accepted matches by tier:")
    print(f"  Tier A (date+name+phone):  {by_tier['A']:,}")
    print(f"  Tier B (date+name unique): {by_tier['B']:,}")
    print(f"  Tier C (name+phone):       {by_tier['C']:,}")
    print(f"  Total accepted:            {len(accepted):,}")
    print()
    print(f"Distinct matched record_no: {distinct_record_no:,}")
    print(f"Distinct matched patients:  {distinct_patients:,}")
    print()
    print(f"Unresolved payment names:   {len(unresolved_names):,}")
    if unresolved_names and len(unresolved_names) <= 30:
        for n in sorted(unresolved_names)[:30]:
            print(f"  - {n}")
    elif unresolved_names:
        for n in sorted(unresolved_names)[:15]:
            print(f"  - {n}")
        print(f"  ... and {len(unresolved_names) - 15} more")
    print()
    print("Top ambiguous cases (tier C):")
    for a in ambiguous[:10]:
        print(f"  record_no={a.get('record_no')} name={a.get('payment_name_norm')} candidates={a.get('candidate_count')}")
    # Duplicate record_no diagnostics
    from collections import Counter
    rn_counts = Counter(m["record_no"] for m in accepted)
    dupes = [(rn, cnt) for rn, cnt in rn_counts.most_common(25) if cnt > 1]
    print()
    print("Top 20 record_no with highest duplicate accepted rows:")
    for rn, cnt in dupes[:20]:
        print(f"  record_no={rn} count={cnt}")
    if not dupes:
        print("  (none - all record_no have at most 1 accepted row)")
    print("=" * 70)
    print()
    print("PowerShell commands to run this script:")
    print("  cd " + str(REPO))
    print("  python scripts/bridge_1403_payment_appointment.py")
    print()
    print("Or from any directory:")
    print(f'  python "{REPO / "scripts" / "bridge_1403_payment_appointment.py"}"')
    print()


def main() -> int:
    payments_path = REPO / "data" / "inputs" / "payments" / "payments_1403_full.xlsx"
    appt_path = REPO / "data" / "inputs" / "history" / "1403" / "REAL_FILE_NAME.xlsx"

    # Try common appointment filenames
    appt_dir = REPO / "data" / "inputs" / "history" / "1403"
    if not appt_path.exists() and appt_dir.exists():
        xlsx = list(appt_dir.glob("*.xlsx"))
        if xlsx:
            appt_path = sorted(xlsx)[0]

    if not payments_path.exists():
        print(f"ERROR: Payments file not found: {payments_path}")
        return 1
    if not appt_path.exists():
        print(f"ERROR: Appointment file not found: {appt_path}")
        return 1

    print("Loading payments...")
    df_pay, col_pay = load_payments(payments_path)
    pay_rows = build_pay_rows(df_pay, col_pay)
    print(f"  Loaded {len(pay_rows):,} payment rows")

    print("Loading appointments...")
    df_appt, col_appt = load_appointments(appt_path)
    appt_rows = build_appt_rows(df_appt, col_appt)
    print(f"  Loaded {len(appt_rows):,} appointment rows")

    print("Building bridge (tiers A/B/C)...")
    accepted, review, patient_map = run_bridge(pay_rows, appt_rows)

    db_path = REPO / "atieh_clinic.db"
    print(f"Saving to {db_path}...")
    conn = sqlite3.connect(db_path)
    try:
        save_to_sqlite(conn, accepted, review, patient_map)
    finally:
        conn.close()

    print_stats(pay_rows, appt_rows, accepted, review, patient_map)
    return 0


if __name__ == "__main__":
    sys.exit(main())





