# -*- coding: utf-8 -*-
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DB_PATH = Path(r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic.db")

def normalize_text(s: str | None) -> str:
    if s is None:
        return ""
    t = str(s).strip()
    if not t or t.lower() == "none":
        return ""
    t = re.sub(r"\s*\(\d+\)\s*$", "", t)
    t = t.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    t = " ".join(t.split())
    return t

def normalize_digits(s: str) -> str:
    if not s:
        return ""
    persian = "۰۱۲۳۴۵۶۷۸۹"
    arabic = "٠١٢٣٤٥٦٧٨٩"
    for i, ch in enumerate(persian):
        s = s.replace(ch, str(i))
    for i, ch in enumerate(arabic):
        s = s.replace(ch, str(i))
    return s

def normalize_phone(raw: str | None) -> set[str]:
    out = set()
    if raw is None:
        return out
    s = normalize_digits(str(raw).strip())
    if not s:
        return out

    parts = re.split(r"[;,/|\s]+", s)
    for token in parts:
        token = token.strip()
        if not token:
            continue
        digits = "".join(c for c in token if c.isdigit())
        if not digits:
            continue

        if digits.startswith("98") and len(digits) >= 12:
            digits = "0" + digits[2:]

        if len(digits) == 10 and digits.startswith("9"):
            digits = "0" + digits

        if len(digits) == 11 and digits.startswith("09"):
            out.add(digits)

    return out

def pick_patient_name_column(cur) -> str:
    cols = [r[1] for r in cur.execute("PRAGMA table_info(patients)").fetchall()]
    for cand in ("full_name", "name", "patient_name"):
        if cand in cols:
            return cand
    raise RuntimeError(f"Could not find patient name column in patients table. Columns={cols}")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    patient_name_col = pick_patient_name_column(cur)

    cur.executescript("""
    DROP TABLE IF EXISTS bridge_tier_d_candidates;
    CREATE TABLE bridge_tier_d_candidates (
        record_no TEXT NOT NULL,
        patient_id INTEGER NOT NULL,
        payment_name_clean TEXT,
        patient_name_clean TEXT,
        matched_phone TEXT,
        candidate_patient_count INTEGER,
        payment_row_count INTEGER,
        confidence REAL NOT NULL,
        match_rule TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # Unbridged financial record_nos
    unbridged = set(
        r[0] for r in cur.execute("""
            SELECT record_no
            FROM patient_unbridged_financial
            WHERE record_no IS NOT NULL
        """).fetchall()
    )

    print(f"Unbridged record_no count: {len(unbridged):,}")

    # Build payment-side identity per record_no
    pay_rows = cur.execute("""
        SELECT record_no, patient_name_raw, phone_raw
        FROM payments_clean
        WHERE record_no IS NOT NULL
    """).fetchall()

    payment_identity = {}
    name_counter = defaultdict(Counter)
    phone_sets = defaultdict(set)
    row_count = defaultdict(int)

    for record_no, patient_name_raw, phone_raw in pay_rows:
        if record_no not in unbridged:
            continue
        row_count[record_no] += 1

        nm = normalize_text(patient_name_raw)
        if nm:
            name_counter[record_no][nm] += 1

        phs = normalize_phone(phone_raw)
        if phs:
            phone_sets[record_no].update(phs)

    for record_no in unbridged:
        name_clean = ""
        if name_counter[record_no]:
            name_clean = name_counter[record_no].most_common(1)[0][0]

        payment_identity[record_no] = {
            "name_clean": name_clean,
            "phones": phone_sets[record_no],
            "payment_row_count": row_count[record_no],
        }

    usable_payment = sum(
        1 for v in payment_identity.values()
        if v["name_clean"] and v["phones"]
    )
    print(f"Usable unbridged payment identities (name+phone): {usable_payment:,}")

    # Build patient-side identity index
    query = f"""
        SELECT p.id, p.{patient_name_col}, p.phone
        FROM patients p
        WHERE p.id IS NOT NULL
    """
    patient_rows = cur.execute(query).fetchall()

    patient_index = defaultdict(list)
    valid_patient_rows = 0

    for patient_id, patient_name, patient_phone in patient_rows:
        nm = normalize_text(patient_name)
        phs = normalize_phone(patient_phone)
        if not nm or not phs:
            continue
        valid_patient_rows += 1
        for ph in phs:
            patient_index[(nm, ph)].append((patient_id, nm, ph))

    print(f"Usable patient identities (name+phone): {valid_patient_rows:,}")

    inserts = []
    multi_candidate = 0
    zero_candidate = 0
    single_candidate = 0

    for record_no, info in payment_identity.items():
        nm = info["name_clean"]
        phs = info["phones"]
        if not nm or not phs:
            continue

        matches = []
        seen_patient_ids = set()

        for ph in phs:
            for patient_id, patient_name_clean, matched_phone in patient_index.get((nm, ph), []):
                if patient_id not in seen_patient_ids:
                    seen_patient_ids.add(patient_id)
                    matches.append((patient_id, patient_name_clean, matched_phone))

        if not matches:
            zero_candidate += 1
            continue

        if len(matches) == 1:
            single_candidate += 1
            patient_id, patient_name_clean, matched_phone = matches[0]
            inserts.append((
                record_no,
                patient_id,
                nm,
                patient_name_clean,
                matched_phone,
                1,
                info["payment_row_count"],
                0.65,
                "D_name_phone_exact"
            ))
        else:
            multi_candidate += 1

    cur.executemany("""
        INSERT INTO bridge_tier_d_candidates (
            record_no,
            patient_id,
            payment_name_clean,
            patient_name_clean,
            matched_phone,
            candidate_patient_count,
            payment_row_count,
            confidence,
            match_rule
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, inserts)

    conn.commit()

    total_candidates = cur.execute("SELECT COUNT(*) FROM bridge_tier_d_candidates").fetchone()[0]
    distinct_record_no = cur.execute("SELECT COUNT(DISTINCT record_no) FROM bridge_tier_d_candidates").fetchone()[0]

    print("=" * 80)
    print("TIER D CANDIDATE BUILD COMPLETE")
    print("=" * 80)
    print(f"Inserted candidate rows: {total_candidates:,}")
    print(f"Distinct record_no matched: {distinct_record_no:,}")
    print(f"Single-candidate matches: {single_candidate:,}")
    print(f"Multi-candidate skipped: {multi_candidate:,}")
    print(f"Zero-candidate: {zero_candidate:,}")

    print("\nSample candidates:")
    for row in cur.execute("""
        SELECT record_no, patient_id, payment_name_clean, patient_name_clean, matched_phone, confidence
        FROM bridge_tier_d_candidates
        LIMIT 10
    """).fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    main()
