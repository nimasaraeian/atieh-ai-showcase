# -*- coding: utf-8 -*-
import re
import sqlite3
from collections import Counter, defaultdict
from difflib import SequenceMatcher
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
    t = re.sub(r"[^\w\s]", " ", t)
    t = " ".join(t.split())
    return t

def token_sort_name(s: str) -> str:
    parts = [p for p in s.split() if p]
    parts = sorted(parts)
    return " ".join(parts)

def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    s1 = SequenceMatcher(None, a, b).ratio()
    s2 = SequenceMatcher(None, token_sort_name(a), token_sort_name(b)).ratio()
    return max(s1, s2)

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
    DROP TABLE IF EXISTS bridge_tier_e_candidates;
    CREATE TABLE bridge_tier_e_candidates (
        record_no TEXT NOT NULL,
        patient_id INTEGER NOT NULL,
        payment_name_clean TEXT,
        patient_name_clean TEXT,
        matched_phone TEXT,
        name_similarity REAL NOT NULL,
        candidate_patient_count INTEGER,
        payment_row_count INTEGER,
        confidence REAL NOT NULL,
        match_rule TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # Tier D record_nos را حذف می‌کنیم تا تکراری نشود
    tier_d_record_nos = set(
        r[0] for r in cur.execute("""
            SELECT DISTINCT record_no
            FROM bridge_tier_d_candidates
        """).fetchall()
    )

    unbridged = set(
        r[0] for r in cur.execute("""
            SELECT record_no
            FROM patient_unbridged_financial
            WHERE record_no IS NOT NULL
        """).fetchall()
    )

    target_record_nos = unbridged - tier_d_record_nos
    print(f"Target unbridged record_no count for Tier E: {len(target_record_nos):,}")

    # payment identity
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
        if record_no not in target_record_nos:
            continue

        row_count[record_no] += 1

        nm = normalize_text(patient_name_raw)
        if nm:
            name_counter[record_no][nm] += 1

        phs = normalize_phone(phone_raw)
        if phs:
            phone_sets[record_no].update(phs)

    for record_no in target_record_nos:
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
    print(f"Usable Tier E payment identities (name+phone): {usable_payment:,}")

    # patient-side by phone
    query = f"""
        SELECT p.id, p.{patient_name_col}, p.phone
        FROM patients p
        WHERE p.id IS NOT NULL
    """
    patient_rows = cur.execute(query).fetchall()

    patients_by_phone = defaultdict(list)
    valid_patient_rows = 0

    for patient_id, patient_name, patient_phone in patient_rows:
        nm = normalize_text(patient_name)
        phs = normalize_phone(patient_phone)
        if not nm or not phs:
            continue
        valid_patient_rows += 1
        for ph in phs:
            patients_by_phone[ph].append((patient_id, nm, ph))

    print(f"Usable patient identities by phone: {valid_patient_rows:,}")

    inserts = []
    zero_candidate = 0
    multi_candidate = 0
    single_candidate = 0

    # thresholds
    STRONG_SIM = 0.92
    OK_SIM = 0.88

    for record_no, info in payment_identity.items():
        pay_name = info["name_clean"]
        pay_phones = info["phones"]

        if not pay_name or not pay_phones:
            continue

        candidates = []
        seen = set()

        for ph in pay_phones:
            for patient_id, patient_name_clean, matched_phone in patients_by_phone.get(ph, []):
                key = (patient_id, matched_phone)
                if key in seen:
                    continue
                seen.add(key)

                sim = similarity(pay_name, patient_name_clean)

                # شرط امن:
                # خیلی قوی، یا قابل قبول + حداقل یک توکن مشترک مهم
                shared_tokens = set(pay_name.split()) & set(patient_name_clean.split())
                if sim >= STRONG_SIM or (sim >= OK_SIM and len(shared_tokens) >= 2):
                    candidates.append((patient_id, patient_name_clean, matched_phone, sim))

        if not candidates:
            zero_candidate += 1
            continue

        # فقط بهترین‌ها را نگه می‌داریم
        candidates = sorted(candidates, key=lambda x: (-x[3], x[0]))
        best_sim = candidates[0][3]
        best = [c for c in candidates if abs(c[3] - best_sim) < 1e-9]

        unique_patient_ids = sorted({c[0] for c in best})

        if len(unique_patient_ids) == 1:
            single_candidate += 1
            patient_id, patient_name_clean, matched_phone, sim = best[0]
            confidence = round(min(0.79, max(0.66, sim)), 4)

            inserts.append((
                record_no,
                patient_id,
                pay_name,
                patient_name_clean,
                matched_phone,
                round(sim, 4),
                1,
                info["payment_row_count"],
                confidence,
                "E_phone_exact_name_fuzzy"
            ))
        else:
            multi_candidate += 1

    cur.executemany("""
        INSERT INTO bridge_tier_e_candidates (
            record_no,
            patient_id,
            payment_name_clean,
            patient_name_clean,
            matched_phone,
            name_similarity,
            candidate_patient_count,
            payment_row_count,
            confidence,
            match_rule
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, inserts)

    conn.commit()

    total_rows = cur.execute("SELECT COUNT(*) FROM bridge_tier_e_candidates").fetchone()[0]
    distinct_record_no = cur.execute("SELECT COUNT(DISTINCT record_no) FROM bridge_tier_e_candidates").fetchone()[0]

    print("=" * 80)
    print("TIER E CANDIDATE BUILD COMPLETE")
    print("=" * 80)
    print(f"Inserted candidate rows: {total_rows:,}")
    print(f"Distinct record_no matched: {distinct_record_no:,}")
    print(f"Single-candidate matches: {single_candidate:,}")
    print(f"Multi-candidate skipped: {multi_candidate:,}")
    print(f"Zero-candidate: {zero_candidate:,}")

    print("\nSample candidates:")
    for row in cur.execute("""
        SELECT record_no, patient_id, payment_name_clean, patient_name_clean, matched_phone, name_similarity, confidence
        FROM bridge_tier_e_candidates
        LIMIT 10
    """).fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    main()
