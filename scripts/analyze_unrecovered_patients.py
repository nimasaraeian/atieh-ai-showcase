# -*- coding: utf-8 -*-
"""
ØªØ­Ù„ÛŒÙ„ Ø¨ÛŒÙ…Ø§Ø±Ø§Ù† unrecovered - ØªØ´Ø®ÛŒØµ Ø¯Ù‚ÛŒÙ‚ Ø¹Ù„Øª recover Ù†Ø´Ø¯Ù†.

Ø§ÛŒÙ† Ø§Ø³Ú©Ø±ÛŒÙ¾Øª Ø±ÙˆÛŒ Ø¨ÛŒÙ…Ø§Ø±Ø§Ù†ÛŒ Ú©Ø§Ø± Ù…ÛŒâ€ŒÚ©Ù†Ø¯ Ú©Ù‡ Ø¯Ø± patient_phone_recovered ÙˆØ¬ÙˆØ¯ Ù†Ø¯Ø§Ø±Ù†Ø¯
Ùˆ Ø¯Ø³ØªÙ‡â€ŒØ¨Ù†Ø¯ÛŒâ€ŒÙ‡Ø§ÛŒ Ù…Ø®ØªÙ„Ù Ø±Ø§ Ø¨Ø±Ø§ÛŒ ØªØ´Ø®ÛŒØµ Ø¹Ù„Øª Ú¯Ø²Ø§Ø±Ø´ Ù…ÛŒâ€ŒÚ©Ù†Ø¯.

Ø§Ø³ØªÙØ§Ø¯Ù‡:
  python scripts/analyze_unrecovered_patients.py

Ù†ÛŒØ§Ø²: Ù‚Ø¨Ù„ Ø§Ø² Ø§Ø¬Ø±Ø§ Ø¨Ø§ÛŒØ¯ pipeline Ú©Ø§Ù…Ù„ recovery Ø§Ø¬Ø±Ø§ Ø´Ø¯Ù‡ Ø¨Ø§Ø´Ø¯:
  python scripts/recover_patient_phones.py --phase all
"""

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.name_normalizer import normalize_persian_name


def get_db_path() -> Path:
    db_url = os.getenv("DATABASE_URL", "sqlite:///atieh_clinic.db")
    p = Path(db_url[len("sqlite:///") :] if db_url.startswith("sqlite:///") else db_url)
    return Path(__file__).resolve().parent.parent / p if not p.is_absolute() else p


def normalize_phone_canonical(raw: str) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    s = str(raw).strip()
    for ch in " \t\n\r-/.()\uff08\uff09+":
        s = s.replace(ch, "")
    digits = "".join(c for c in s if c.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("98") and len(digits) >= 10:
        digits = digits[2:]
    return digits


def phone_to_last8(digits: str) -> str:
    return digits[-8:] if len(digits) >= 8 else ""


def is_phone_valid(digits: str) -> bool:
    """Ø´Ù…Ø§Ø±Ù‡ Ù…ÙˆØ¨Ø§ÛŒÙ„ Ø§ÛŒØ±Ø§Ù†: Û±Û± Ø±Ù‚Ù…ÛŒ 0xxxxxxxxxx ÛŒØ§ Û±Û° Ø±Ù‚Ù…ÛŒ 9xxxxxxxxx."""
    if not digits:
        return False
    d = "".join(c for c in str(digits) if c.isdigit())
    if len(d) >= 11 and (d.startswith("0") or d.startswith("98")):
        return True
    if len(d) >= 10 and d.startswith("9"):
        return True
    return False


def repair_phone_variants(digits: str) -> list:
    if not digits or not isinstance(digits, str):
        return []
    d = "".join(c for c in str(digits) if c.isdigit())
    out = [d]
    if len(d) == 10 and d.startswith("9"):
        v = "0" + d
        if v not in out:
            out.append(v)
    return out


def _require_table(conn: sqlite3.Connection, name: str) -> None:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    if not cur.fetchone():
        raise RuntimeError(
            "Ø¬Ø¯ÙˆÙ„ %s ÛŒØ§ÙØª Ù†Ø´Ø¯. Ù„Ø·ÙØ§Ù‹ Ø§Ø¨ØªØ¯Ø§ pipeline recovery Ø±Ø§ Ø§Ø¬Ø±Ø§ Ú©Ù†ÛŒØ¯: "
            "python scripts/recover_patient_phones.py --phase all" % name
        )


def run(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA busy_timeout=60000")
    _require_table(conn, "patient_phone_recovered")
    _require_table(conn, "patients")
    _require_table(conn, "patient_lookup_norm")
    _require_table(conn, "arb_name_norm")
    _require_table(conn, "appointment_phone_helper")
    _require_table(conn, "payments_lookup_norm")

    # Unrecovered = patients not in patient_phone_recovered
    unrecovered = conn.execute(
        """
        SELECT p.id, p.name,
               pln.patient_name_norm, pln.patient_phone_norm, pln.patient_phone_last8
        FROM patients p
        LEFT JOIN patient_lookup_norm pln ON pln.patient_id = p.id
        WHERE p.id NOT IN (SELECT patient_id FROM patient_phone_recovered)
        """
    ).fetchall()

    # Build lookup sets from appointments and payments
    appt_names = set(
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT patient_name_norm FROM arb_name_norm WHERE patient_name_norm IS NOT NULL AND TRIM(patient_name_norm) != ''"
        ).fetchall()
    )
    appt_phones = set()
    appt_last8 = set()
    for r in conn.execute(
        "SELECT appointment_phone_norm, appointment_phone_last8 FROM appointment_phone_helper"
    ).fetchall():
        raw, last8 = r[0], r[1]
        if raw:
            appt_phones.add(normalize_phone_canonical(raw))
            for v in repair_phone_variants(normalize_phone_canonical(raw)):
                appt_phones.add(v)
        if last8 and len(str(last8).strip()) == 8:
            appt_last8.add(str(last8).strip())

    pay_names = set()
    pay_phones = set()
    pay_last8 = set()
    for r in conn.execute(
        "SELECT payment_name_norm, payment_phone_norm, payment_phone_last8 FROM payments_lookup_norm"
    ).fetchall():
        n, raw, last8 = r[0], r[1], r[2]
        if n and str(n).strip():
            pay_names.add(str(n).strip())
        if raw:
            digits = normalize_phone_canonical(raw)
            pay_phones.add(digits)
            for v in repair_phone_variants(digits):
                pay_phones.add(v)
        if last8 and len(str(last8).strip()) == 8:
            pay_last8.add(str(last8).strip())

    total_unrecovered = len(unrecovered)

    # Categories
    B_no_phone = 0
    C_invalid_phone = 0
    D_name_in_appointments = 0
    E_phone_in_appointments = 0
    F_last8_in_appointments = 0
    G_name_in_payments = 0
    H_phone_in_payments = 0
    I_last8_in_payments = 0
    J_only_name_overlap = 0
    K_only_last8_overlap = 0
    L_no_overlap = 0

    diagnostics = []

    for row in unrecovered:
        pid, pname, name_norm, phone_raw, last8_from_lookup = (
            row[0],
            row[1] or "",
            (row[2] or "").strip(),
            (row[3] or "").strip() if row[3] else "",
            (row[4] or "").strip() if row[4] else "",
        )

        digits = normalize_phone_canonical(phone_raw)
        last8 = last8_from_lookup or phone_to_last8(digits)
        has_phone = bool(phone_raw and phone_raw.strip())
        phone_valid = is_phone_valid(digits)
        name_in_appt = name_norm in appt_names
        phone_in_appt = bool(digits and (digits in appt_phones or any(v in appt_phones for v in repair_phone_variants(digits))))
        last8_in_appt = bool(last8 and last8 in appt_last8)
        name_in_pay = name_norm in pay_names
        phone_in_pay = bool(digits and (digits in pay_phones or any(v in pay_phones for v in repair_phone_variants(digits))))
        last8_in_pay = bool(last8 and last8 in pay_last8)

        if not has_phone:
            B_no_phone += 1
        if has_phone and (not phone_valid or len(digits) < 10):
            C_invalid_phone += 1
        if name_in_appt:
            D_name_in_appointments += 1
        if phone_in_appt:
            E_phone_in_appointments += 1
        if last8_in_appt:
            F_last8_in_appointments += 1
        if name_in_pay:
            G_name_in_payments += 1
        if phone_in_pay:
            H_phone_in_payments += 1
        if last8_in_pay:
            I_last8_in_payments += 1

        # Overlap categories
        has_name_any = name_in_appt or name_in_pay
        has_phone_any = phone_in_appt or phone_in_pay
        has_last8_any = last8_in_appt or last8_in_pay

        only_name = has_name_any and not has_phone_any and not has_last8_any
        only_last8 = has_last8_any and not has_phone_any and not has_name_any
        no_overlap = not has_name_any and not has_phone_any and not has_last8_any

        if only_name:
            J_only_name_overlap += 1
        if only_last8:
            K_only_last8_overlap += 1
        if no_overlap:
            L_no_overlap += 1

        # likely_reason
        if not has_phone:
            likely = "no_phone"
        elif not phone_valid or len(digits) < 10:
            likely = "invalid_phone"
        elif no_overlap:
            likely = "no_source_overlap"
        elif only_name:
            likely = "only_name_overlap"
        elif only_last8:
            likely = "only_last8_overlap"
        elif has_phone_any and has_name_any:
            likely = "exact_overlap_but_not_selected"
        elif (has_last8_any or has_phone_any) and not has_name_any:
            likely = "ambiguous_match"
        elif has_name_any and not has_phone_any:
            likely = "appointment_gap"
        else:
            likely = "payments_gap"

        diagnostics.append(
            (
                pid,
                pname,
                phone_raw or None,
                digits or None,
                last8 or None,
                1 if has_phone else 0,
                1 if phone_valid else 0,
                1 if name_in_appt else 0,
                1 if phone_in_appt else 0,
                1 if last8_in_appt else 0,
                1 if name_in_pay else 0,
                1 if phone_in_pay else 0,
                1 if last8_in_pay else 0,
                likely,
            )
        )

    # Create diagnostic table
    conn.execute("DROP TABLE IF EXISTS unrecovered_patient_diagnostics")
    conn.execute(
        """
        CREATE TABLE unrecovered_patient_diagnostics (
            patient_id INTEGER PRIMARY KEY,
            patient_name TEXT,
            patient_phone_raw TEXT,
            patient_phone_norm TEXT,
            patient_phone_last8 TEXT,
            has_phone INTEGER,
            phone_valid INTEGER,
            name_in_appointments INTEGER,
            phone_in_appointments INTEGER,
            last8_in_appointments INTEGER,
            name_in_payments INTEGER,
            phone_in_payments INTEGER,
            last8_in_payments INTEGER,
            likely_reason TEXT
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO unrecovered_patient_diagnostics
        (patient_id, patient_name, patient_phone_raw, patient_phone_norm, patient_phone_last8,
         has_phone, phone_valid, name_in_appointments, phone_in_appointments, last8_in_appointments,
         name_in_payments, phone_in_payments, last8_in_payments, likely_reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        diagnostics,
    )
    conn.commit()

    # Count by likely_reason
    reason_counts = {}
    for r in conn.execute(
        "SELECT likely_reason, COUNT(*) FROM unrecovered_patient_diagnostics GROUP BY likely_reason ORDER BY COUNT(*) DESC"
    ).fetchall():
        reason_counts[r[0]] = r[1]

    # --- Report ---
    total_patients = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    recovered = conn.execute("SELECT COUNT(*) FROM patient_phone_recovered").fetchone()[0]
    coverage = (recovered * 100.0 / total_patients) if total_patients else 0.0

    print("=" * 60)
    print("Ú¯Ø²Ø§Ø±Ø´ ØªØ­Ù„ÛŒÙ„ Ø¨ÛŒÙ…Ø§Ø±Ø§Ù† Unrecovered")
    print("=" * 60)
    print()
    print("Ú©Ù„ Ø¨ÛŒÙ…Ø§Ø±Ø§Ù†: %d" % total_patients)
    print("Recovered: %d (%.2f%%)" % (recovered, coverage))
    print("Total unrecovered: %d (%.2f%%)" % (total_unrecovered, 100.0 - coverage))
    print()

    print("--- Ø¯Ø³ØªÙ‡â€ŒØ¨Ù†Ø¯ÛŒâ€ŒÙ‡Ø§ ---")
    print("A) total_unrecovered: %d" % total_unrecovered)
    print("B) unrecovered_no_phone_in_patients: %d" % B_no_phone)
    print("C) unrecovered_invalid_or_too_short_phone: %d" % C_invalid_phone)
    print("D) unrecovered_name_exists_in_appointments: %d" % D_name_in_appointments)
    print("E) unrecovered_phone_exists_in_appointments: %d" % E_phone_in_appointments)
    print("F) unrecovered_last8_exists_in_appointments: %d" % F_last8_in_appointments)
    print("G) unrecovered_name_exists_in_payments: %d" % G_name_in_payments)
    print("H) unrecovered_phone_exists_in_payments: %d" % H_phone_in_payments)
    print("I) unrecovered_last8_exists_in_payments: %d" % I_last8_in_payments)
    print("J) unrecovered_has_only_name_overlap: %d" % J_only_name_overlap)
    print("K) unrecovered_has_only_last8_overlap: %d" % K_only_last8_overlap)
    print("L) unrecovered_has_no_overlap_any_source: %d" % L_no_overlap)
    print()

    print("--- Top likely_reason values ---")
    for reason, cnt in list(reason_counts.items())[:10]:
        pct = 100.0 * cnt / total_unrecovered if total_unrecovered else 0
        print("  %s: %d (%.1f%%)" % (reason, cnt, pct))
    print()

    # 20 samples from biggest categories
    print("--- 20 Ù†Ù…ÙˆÙ†Ù‡ Ø§Ø² Ø¨Ø²Ø±Ú¯â€ŒØªØ±ÛŒÙ† Ø¯Ø³ØªÙ‡â€ŒÙ‡Ø§ ---")
    for reason, _ in list(reason_counts.items())[:3]:
        rows = conn.execute(
            """
            SELECT patient_id, patient_name, patient_phone_raw, patient_phone_norm, likely_reason
            FROM unrecovered_patient_diagnostics
            WHERE likely_reason = ?
            LIMIT 20
            """,
            (reason,),
        ).fetchall()
        print()
        print("  [%s] (%d Ù†Ù…ÙˆÙ†Ù‡)" % (reason, len(rows)))
        for r in rows:
            print(
                "    id=%s name=%s phone_raw=%s phone_norm=%s reason=%s"
                % (r[0], (r[1] or "")[:30], r[2] or "", r[3] or "", r[4])
            )
    print()

    # Ø¬Ù…Ø¹â€ŒØ¨Ù†Ø¯ÛŒ
    print("--- Ø¬Ù…Ø¹â€ŒØ¨Ù†Ø¯ÛŒ Ù…Ø³ÛŒØ± ÙˆØ§Ù‚Ø¹â€ŒØ¨ÛŒÙ†Ø§Ù†Ù‡ Ø¨Ø±Ø§ÛŒ Ø±Ø³ÛŒØ¯Ù† Ø¨Ù‡ 90%% ---")
    gap_to_90 = max(0, int(0.90 * total_patients) - recovered)
    print("Ø¨Ø±Ø§ÛŒ Ø±Ø³ÛŒØ¯Ù† Ø¨Ù‡ 90%% coverage: %d Ø¨ÛŒÙ…Ø§Ø± Ø§Ø¶Ø§ÙÛŒ Ù†ÛŒØ§Ø² Ø§Ø³Øª." % gap_to_90)
    print()
    if B_no_phone > 0:
        print("- no_phone (%d): Ø¨Ø¯ÙˆÙ† Ø´Ù…Ø§Ø±Ù‡ Ø¯Ø± patients - Ù‚Ø§Ø¨Ù„ recover Ø§Ø² Ù…Ù†Ø§Ø¨Ø¹ Ø¯ÛŒÚ¯Ø± Ù†ÛŒØ³Øª Ù…Ú¯Ø± ÙˆØ±ÙˆØ¯ Ø¯Ø³ØªÛŒ." % B_no_phone)
    if C_invalid_phone > 0:
        print("- invalid_phone (%d): Ø´Ù…Ø§Ø±Ù‡ Ù†Ø§Ù…Ø¹ØªØ¨Ø±/Ú©ÙˆØªØ§Ù‡ - Ù†ÛŒØ§Ø² Ø¨Ù‡ Ø§ØµÙ„Ø§Ø­ Ø¯Ø³ØªÛŒ ÛŒØ§ Ù…Ù†Ø¨Ø¹ Ø¬Ø§ÛŒÚ¯Ø²ÛŒÙ†." % C_invalid_phone)
    if L_no_overlap > 0:
        print("- no_source_overlap (%d): Ù‡ÛŒÚ† overlap Ø¯Ø± appointments/payments Ù†Ø¯Ø§Ø±Ù†Ø¯ - Ø§Ø­ØªÙ…Ø§Ù„Ø§Ù‹ Ø¨ÛŒÙ…Ø§Ø±Ø§Ù† Ù‚Ø¯ÛŒÙ…ÛŒ ÛŒØ§ Ø¨Ø§ Ù…Ù†Ø¨Ø¹ Ù…ØªÙØ§ÙˆØª." % L_no_overlap)
    if J_only_name_overlap > 0:
        print("- only_name_overlap (%d): ÙÙ‚Ø· Ù†Ø§Ù… overlap Ø¯Ø§Ø±Ø¯ØŒ ÙÙˆÙ† Ùˆ last8 Ø®ÛŒØ± - Ù…Ù…Ú©Ù† Ø§Ø³Øª Ø¨Ø§ fuzzy match ÛŒØ§ name+record_no Ù‚Ø§Ø¨Ù„ Ø¨Ù‡Ø¨ÙˆØ¯ Ø¨Ø§Ø´Ø¯." % J_only_name_overlap)
    if K_only_last8_overlap > 0:
        print("- only_last8_overlap (%d): ÙÙ‚Ø· last8 overlap Ø¯Ø§Ø±Ø¯ - threshold last8_safe Ù…Ø­Ø¯ÙˆØ¯ Ø§Ø³ØªØ› Ø§ÙØ²Ø§ÛŒØ´ threshold Ø±ÛŒØ³Ú© collision Ø¯Ø§Ø±Ø¯." % K_only_last8_overlap)
    if "exact_overlap_but_not_selected" in reason_counts:
        n = reason_counts["exact_overlap_but_not_selected"]
        print("- exact_overlap_but_not_selected (%d): overlap Ø¯Ù‚ÛŒÙ‚ ÙˆØ¬ÙˆØ¯ Ø¯Ø§Ø±Ø¯ Ø§Ù…Ø§ Ø§Ù†ØªØ®Ø§Ø¨ Ù†Ø´Ø¯Ù‡ - Ø¨Ø±Ø±Ø³ÛŒ Ù…Ù†Ø·Ù‚ tie-break Ùˆ ranking." % n)
    if "ambiguous_match" in reason_counts:
        n = reason_counts["ambiguous_match"]
        print("- ambiguous_match (%d): match Ù…Ø¨Ù‡Ù… - Ø§Ø­ØªÙ…Ø§Ù„Ø§Ù‹ Ú†Ù†Ø¯ candidateØ› Ù†ÛŒØ§Ø² Ø¨Ù‡ rule ÛŒØ§ manual review." % n)
    print()
    print("Ø¬Ø¯ÙˆÙ„ unrecovered_patient_diagnostics Ø§ÛŒØ¬Ø§Ø¯ Ø´Ø¯ Ø¨Ø±Ø§ÛŒ query Ø¯Ø³ØªÛŒ.")


def main() -> None:
    db_path = get_db_path()
    if not db_path.exists():
        print("Ø®Ø·Ø§: Ø¯ÛŒØªØ§Ø¨ÛŒØ³ ÛŒØ§ÙØª Ù†Ø´Ø¯: %s" % db_path)
        sys.exit(1)
    conn = sqlite3.connect(str(db_path), timeout=180)
    try:
        run(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

