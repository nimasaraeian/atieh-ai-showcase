import sqlite3
import re
import json

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("‌", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def clean_payment_name(name: str) -> str:
    s = normalize_text(name)

    # remove numeric content inside parentheses: (101182)
    s = re.sub(r"\(\s*\d{3,12}\s*\)", " ", s)

    # remove standalone numeric tokens anywhere
    s = re.sub(r"\b\d{3,12}\b", " ", s)

    # normalize separators
    s = re.sub(r"[-_/\\]+", " ", s)

    # remove empty parentheses/brackets leftovers
    s = re.sub(r"[\(\)\[\]\{\}]+", " ", s)

    # collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonicalize_name(name: str) -> str:
    s = clean_payment_name(name)
    tokens = [t for t in re.split(r"[ \-_]+", s) if t]
    tokens = sorted(tokens)
    return " ".join(tokens)


def extract_numeric_tokens(text: str):
    if not text:
        return []
    vals = re.findall(r"\b\d{3,12}\b", str(text))
    out = []
    seen = set()
    for v in vals:
        if v not in seen:
            out.append(v)
            seen.add(v)
    return out


def normalize_mobile(phone: str) -> str:
    if phone is None:
        return ""
    digits = re.sub(r"\D", "", str(phone))

    if len(digits) == 10 and digits.startswith("9"):
        return "0" + digits

    if len(digits) == 11 and digits.startswith("09"):
        return digits

    return digits


def table_columns(conn, table_name):
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return [r[1] for r in cur.fetchall()]


def pick_col(cols, candidates, required=True):
    cols_lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    if required:
        raise RuntimeError(f"Missing expected column. Tried: {candidates}, found: {cols}")
    return None


def qcol(col):
    return col if col else None


def main():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("START PHASE 09C", flush=True)

    cols = table_columns(conn, "payments_lookup_norm")
    print("payments_lookup_norm columns:", cols, flush=True)

    name_col = "'نام بیمار'"

    phone_col = "'موبايل'"

    recordno_col = pick_col(cols, [
        "record_no",
        "recordno"
    ], required=False)

    if not name_col and not phone_col:
        raise RuntimeError("Could not detect usable name/phone columns in payments_lookup_norm")

    select_parts = ["rowid AS payment_rowid"]
    if name_col:
        select_parts.append(f"{name_col} AS payment_name_raw")
    else:
        select_parts.append("NULL AS payment_name_raw")

    if phone_col:
        select_parts.append(f"{phone_col} AS phone_raw")
    else:
        select_parts.append("NULL AS phone_raw")

    if recordno_col:
        select_parts.append(f"{recordno_col} AS record_no_raw")
    else:
        select_parts.append("NULL AS record_no_raw")

    sql = f"SELECT {', '.join(select_parts)} FROM payments_lookup_norm"
    rows = conn.execute(sql).fetchall()
    print(f"payments rows loaded: {len(rows):,}", flush=True)

    cur.executescript("""
    DROP TABLE IF EXISTS payments_identity_clean_v2;

    CREATE TABLE payments_identity_clean_v2 (
        payment_rowid INTEGER PRIMARY KEY,
        payment_name_raw TEXT,
        payment_name_clean TEXT,
        payment_name_canonical TEXT,
        numeric_tokens_json TEXT,
        possible_record_no TEXT,
        phone_raw TEXT,
        phone_norm TEXT,
        parse_flags TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_pay_clean_name
        ON payments_identity_clean_v2(payment_name_clean);

    CREATE INDEX IF NOT EXISTS idx_pay_clean_canonical
        ON payments_identity_clean_v2(payment_name_canonical);

    CREATE INDEX IF NOT EXISTS idx_pay_clean_phone
        ON payments_identity_clean_v2(phone_norm);

    CREATE INDEX IF NOT EXISTS idx_pay_clean_recordno
        ON payments_identity_clean_v2(possible_record_no);
    """)

    insert_sql = """
    INSERT INTO payments_identity_clean_v2 (
        payment_rowid,
        payment_name_raw,
        payment_name_clean,
        payment_name_canonical,
        numeric_tokens_json,
        possible_record_no,
        phone_raw,
        phone_norm,
        parse_flags
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for i, row in enumerate(rows, start=1):
        raw_name = row["payment_name_raw"] if "payment_name_raw" in row.keys() else None
        raw_phone = row["phone_raw"] if "phone_raw" in row.keys() else None
        raw_record = row["record_no_raw"] if "record_no_raw" in row.keys() else None

        clean_name = clean_payment_name(raw_name)
        canonical_name = canonicalize_name(raw_name)
        numeric_tokens = extract_numeric_tokens(raw_name)

        possible_record_no = ""
        if raw_record:
            possible_record_no = str(raw_record).strip()
        elif numeric_tokens:
            possible_record_no = numeric_tokens[0]

        phone_norm = normalize_mobile(raw_phone)

        flags = []
        if raw_name and clean_name != normalize_text(raw_name):
            flags.append("name_cleaned")
        if numeric_tokens:
            flags.append("numeric_tokens_found")
        if raw_phone and phone_norm and str(raw_phone).strip() != phone_norm:
            flags.append("phone_normalized")
        if possible_record_no:
            flags.append("possible_record_no")

        cur.execute(
            insert_sql,
            (
                row["payment_rowid"],
                raw_name,
                clean_name,
                canonical_name,
                json.dumps(numeric_tokens, ensure_ascii=False),
                possible_record_no,
                raw_phone,
                phone_norm,
                ",".join(flags)
            )
        )

        if i % 5000 == 0:
            conn.commit()
            print(f"processed: {i:,}", flush=True)

    conn.commit()

    summary = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        SUM(CASE WHEN payment_name_clean IS NOT NULL AND TRIM(payment_name_clean) <> '' THEN 1 ELSE 0 END) AS with_clean_name,
        SUM(CASE WHEN phone_norm IS NOT NULL AND TRIM(phone_norm) <> '' THEN 1 ELSE 0 END) AS with_phone_norm,
        SUM(CASE WHEN possible_record_no IS NOT NULL AND TRIM(possible_record_no) <> '' THEN 1 ELSE 0 END) AS with_possible_record_no,
        SUM(CASE WHEN parse_flags LIKE '%name_cleaned%' THEN 1 ELSE 0 END) AS rows_name_cleaned,
        SUM(CASE WHEN parse_flags LIKE '%phone_normalized%' THEN 1 ELSE 0 END) AS rows_phone_normalized
    FROM payments_identity_clean_v2
    """).fetchone()

    print("\n=== PHASE 09C SUMMARY ===", flush=True)
    for k in summary.keys():
        print(f"{k:24}: {summary[k]}", flush=True)

    conn.close()


if __name__ == "__main__":
    main()


