# scripts/recovery_v2/phase_09b_unrecovered_identity_diagnostics.py

import sqlite3
import re
import json
from collections import defaultdict

DB_PATH = r"C:\Users\USER\Documents\GitHub\atieh\atieh_clinic_recovery81_test.db"


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = s.replace("ÙŠ", "ÛŒ").replace("Ùƒ", "Ú©")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def canonicalize_name(name: str) -> str:
    name = normalize_text(name)
    tokens = [t for t in re.split(r"[ \-_]+", name) if t]
    tokens = sorted(tokens)
    return " ".join(tokens)


def reordered_name_variants(name: str):
    name = normalize_text(name)
    tokens = [t for t in re.split(r"[ \-_]+", name) if t]
    variants = set()
    if not tokens:
        return variants
    variants.add(" ".join(tokens))
    variants.add(" ".join(sorted(tokens)))
    if len(tokens) == 2:
        variants.add(tokens[1] + " " + tokens[0])
    return variants


def extract_recordnos(text: str):
    if not text:
        return []
    vals = re.findall(r"\b\d{4,10}\b", text)
    return list(dict.fromkeys(vals))


def json_dump_list(values):
    return json.dumps(sorted(list(values)), ensure_ascii=False)


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


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # -------------------------------
    # Resolve schema dynamically
    # -------------------------------
    patient_cols = table_columns(conn, "patients")
    lookup_cols = table_columns(conn, "patient_lookup_norm")
    pay_cols = table_columns(conn, "payments_lookup_norm")
    bridge_cols = table_columns(conn, "appointment_recordno_bridge")

    patients_id_col = pick_col(patient_cols, ["id", "patient_id"])
    patients_name_col = pick_col(patient_cols, ["name", "patient_name", "full_name"], required=False)

    lookup_pid_col = pick_col(lookup_cols, ["patient_id", "id"])
    lookup_name_col = pick_col(lookup_cols, ["name", "patient_name", "full_name"], required=False)
    lookup_canon_col = pick_col(lookup_cols, ["canonical_name", "name_canonical", "patient_name_canonical"], required=False)
    lookup_name_norm_col = pick_col(lookup_cols, ["name_norm", "patient_name_norm", "full_name_norm"], required=False)

    pay_name_col = pick_col(pay_cols, ["payment_name_norm", "name_norm", "payer_name_norm", "full_name_norm"], required=False)
    pay_phone_col = pick_col(pay_cols, ["phone_norm", "mobile_norm", "phone"], required=False)
    pay_recordno_col = pick_col(pay_cols, ["record_no", "recordno"], required=False)

    bridge_name_col = pick_col(bridge_cols, ["appointment_name_norm", "name_norm", "patient_name_norm"], required=False)
    bridge_phone_col = pick_col(bridge_cols, ["phone_norm", "mobile_norm", "phone"], required=False)
    bridge_recordno_col = pick_col(bridge_cols, ["record_no", "recordno"], required=False)

    # -------------------------------
    # Build diagnostic table
    # -------------------------------
    cur.executescript("""
    DROP TABLE IF EXISTS unrecovered_identity_diagnostics;

    CREATE TABLE unrecovered_identity_diagnostics (
        patient_id INTEGER PRIMARY KEY,
        name TEXT,
        canonical_name TEXT,
        appointment_name_candidates TEXT,
        payment_name_candidates TEXT,
        recordno_candidates TEXT,
        phone_candidates TEXT,
        evidence_score REAL DEFAULT 0,
        appointment_match_count INTEGER DEFAULT 0,
        payment_match_count INTEGER DEFAULT 0,
        recordno_match_count INTEGER DEFAULT 0,
        phone_match_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # -------------------------------
    # Load unrecovered patients
    # -------------------------------
        
    def qcol(alias, col):
        return f"{alias}.{col}" if col else "NULL"

    p_name_expr = qcol("p", patients_name_col)
    pl_name_expr = qcol("pl", lookup_name_col)
    pl_canon_expr = qcol("pl", lookup_canon_col)
    pl_name_norm_expr = qcol("pl", lookup_name_norm_col)

    unrecovered_sql = f"""
    SELECT
        p.{patients_id_col} AS patient_id,
        COALESCE({pl_name_expr}, {p_name_expr}, '') AS patient_name,
        COALESCE({pl_canon_expr}, {pl_name_norm_expr}, {pl_name_expr}, {p_name_expr}, '') AS canonical_name
    FROM patients p
    LEFT JOIN patient_lookup_norm pl
        ON pl.{lookup_pid_col} = p.{patients_id_col}
    LEFT JOIN patient_phone_recovered_v2 r
        ON r.patient_id = p.{patients_id_col}
    WHERE r.patient_id IS NULL
    """
    unrecovered = conn.execute(unrecovered_sql).fetchall()

    # -------------------------------
    # Preload appointment rows
    # -------------------------------
    appt_rows = []
    if bridge_name_col or bridge_phone_col or bridge_recordno_col:
        fields = []
        if bridge_name_col:
            fields.append(f"{bridge_name_col} AS appt_name")
        else:
            fields.append("NULL AS appt_name")
        if bridge_phone_col:
            fields.append(f"{bridge_phone_col} AS appt_phone")
        else:
            fields.append("NULL AS appt_phone")
        if bridge_recordno_col:
            fields.append(f"{bridge_recordno_col} AS appt_recordno")
        else:
            fields.append("NULL AS appt_recordno")

        appt_rows = conn.execute(f"SELECT {', '.join(fields)} FROM appointment_recordno_bridge").fetchall()

    # -------------------------------
    # Preload payment rows
    # -------------------------------
    pay_rows = []
    if pay_name_col or pay_phone_col or pay_recordno_col:
        fields = []
        if pay_name_col:
            fields.append(f"{pay_name_col} AS pay_name")
        else:
            fields.append("NULL AS pay_name")
        if pay_phone_col:
            fields.append(f"{pay_phone_col} AS pay_phone")
        else:
            fields.append("NULL AS pay_phone")
        if pay_recordno_col:
            fields.append(f"{pay_recordno_col} AS pay_recordno")
        else:
            fields.append("NULL AS pay_recordno")

        pay_rows = conn.execute(f"SELECT {', '.join(fields)} FROM payments_lookup_norm").fetchall()

    # -------------------------------
    # Diagnostics loop
    # -------------------------------
    insert_sql = """
    INSERT INTO unrecovered_identity_diagnostics (
        patient_id,
        name,
        canonical_name,
        appointment_name_candidates,
        payment_name_candidates,
        recordno_candidates,
        phone_candidates,
        evidence_score,
        appointment_match_count,
        payment_match_count,
        recordno_match_count,
        phone_match_count
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for i, row in enumerate(unrecovered, start=1):
        patient_id = row["patient_id"]
        patient_name = normalize_text(row["patient_name"] or "")
        canonical_name = canonicalize_name(row["canonical_name"] or patient_name)

        name_variants = reordered_name_variants(patient_name)
        name_variants.add(canonical_name)

        appointment_name_candidates = set()
        payment_name_candidates = set()
        recordno_candidates = set()
        phone_candidates = set()

        appointment_match_count = 0
        payment_match_count = 0
        recordno_match_count = 0
        phone_match_count = 0

        # ---- appointment side
        for a in appt_rows:
            appt_name = normalize_text(a["appt_name"] or "")
            appt_phone = normalize_text(a["appt_phone"] or "")
            appt_recordno = normalize_text(a["appt_recordno"] or "")

            appt_canon = canonicalize_name(appt_name) if appt_name else ""

            matched = False
            if appt_name and appt_name in name_variants:
                matched = True
            elif appt_canon and appt_canon == canonical_name:
                matched = True
            elif appt_name and canonical_name and len(set(appt_name.split()) & set(canonical_name.split())) >= 2:
                matched = True

            if matched:
                appointment_match_count += 1
                if appt_name:
                    appointment_name_candidates.add(appt_name)
                if appt_phone:
                    phone_candidates.add(appt_phone)
                    phone_match_count += 1
                if appt_recordno:
                    recordno_candidates.add(appt_recordno)
                    recordno_match_count += 1

        # ---- payment side
        for p in pay_rows:
            pay_name = normalize_text(p["pay_name"] or "")
            pay_phone = normalize_text(p["pay_phone"] or "")
            pay_recordno = normalize_text(p["pay_recordno"] or "")

            extracted_recordnos = extract_recordnos(pay_name)

            matched = False
            pay_canon = canonicalize_name(pay_name) if pay_name else ""

            if pay_name and patient_name and patient_name in pay_name:
                matched = True
            elif pay_canon and canonical_name and canonical_name and len(set(pay_canon.split()) & set(canonical_name.split())) >= 2:
                matched = True

            if matched:
                payment_match_count += 1
                if pay_name:
                    payment_name_candidates.add(pay_name)
                if pay_phone:
                    phone_candidates.add(pay_phone)
                    phone_match_count += 1
                if pay_recordno:
                    recordno_candidates.add(pay_recordno)
                    recordno_match_count += 1
                for rec in extracted_recordnos:
                    recordno_candidates.add(rec)
                    recordno_match_count += 1

        # ---- evidence scoring
        evidence_score = 0.0
        evidence_score += min(appointment_match_count, 5) * 1.5
        evidence_score += min(payment_match_count, 5) * 1.2
        evidence_score += min(recordno_match_count, 5) * 2.0
        evidence_score += min(phone_match_count, 5) * 1.8

        if appointment_match_count > 0 and payment_match_count > 0:
            evidence_score += 3.0
        if recordno_match_count > 0 and phone_match_count > 0:
            evidence_score += 3.0

        cur.execute(
            insert_sql,
            (
                patient_id,
                patient_name,
                canonical_name,
                json_dump_list(appointment_name_candidates),
                json_dump_list(payment_name_candidates),
                json_dump_list(recordno_candidates),
                json_dump_list(phone_candidates),
                round(evidence_score, 2),
                appointment_match_count,
                payment_match_count,
                recordno_match_count,
                phone_match_count,
            ),
        )

        if i % 1000 == 0:
            conn.commit()
            print(f"processed: {i:,}")

    conn.commit()

    # summary
    summary = conn.execute("""
    SELECT
        COUNT(*) AS total_unrecovered,
        SUM(CASE WHEN appointment_match_count > 0 THEN 1 ELSE 0 END) AS with_appointment_signal,
        SUM(CASE WHEN payment_match_count > 0 THEN 1 ELSE 0 END) AS with_payment_signal,
        SUM(CASE WHEN recordno_match_count > 0 THEN 1 ELSE 0 END) AS with_recordno_signal,
        SUM(CASE WHEN phone_match_count > 0 THEN 1 ELSE 0 END) AS with_phone_signal,
        SUM(CASE WHEN evidence_score >= 5 THEN 1 ELSE 0 END) AS evidence_5_plus,
        SUM(CASE WHEN evidence_score >= 8 THEN 1 ELSE 0 END) AS evidence_8_plus
    FROM unrecovered_identity_diagnostics
    """).fetchone()

    print("\n=== Phase 09B - Unrecovered Identity Diagnostics ===")
    for k in summary.keys():
        print(f"{k:24}: {summary[k]}")

    conn.close()


if __name__ == "__main__":
    main()

