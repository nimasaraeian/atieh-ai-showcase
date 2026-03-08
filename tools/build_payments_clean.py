import sqlite3
import re
import hashlib
from typing import Optional, Tuple, Dict, List

DB_PATH = "atieh_clinic.db"

RECNO_RE = re.compile(r"\((\d+)\)\s*$")


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def norm_phone(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None

    # normalize Iranian formats a bit:
    # 98912xxxxxxx / 0912xxxxxxx / 912xxxxxxx
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits

    # keep only plausible mobile-like numbers (optional rule)
    if len(digits) < 10:
        return None
    return digits


def norm_persian(s: str) -> str:
    # Normalize Arabic/Persian variants + whitespace
    s = (s or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("\u200c", " ")  # ZWNJ to space
    # collapse spaces
    s = " ".join(s.split())
    return s


def split_name_and_record_no(patient_name_raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not patient_name_raw:
        return None, None
    s = norm_persian(patient_name_raw)
    m = RECNO_RE.search(s)
    record_no = m.group(1) if m else None
    name = s
    if record_no:
        name = RECNO_RE.sub("", s).strip()
    return (name if name else None), record_no


def to_float(x: Optional[str]) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() == "nan":
        return None
    # remove commas and spaces
    s = s.replace(",", "").replace(" ", "")
    # handle parentheses negatives: (123) -> -123
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except Exception:
        return None


def ensure_patient_identifiers_base(cur: sqlite3.Cursor):
    """
    Seed patient_identifiers from patients table: phone + national_id.
    Uses UNIQUE(id_type,id_value) so it's safe/idempotent.
    """
    # phone identifiers
    cur.execute("""
        INSERT OR IGNORE INTO patient_identifiers (patient_id, id_type, id_value, confidence, source)
        SELECT id, 'phone', phone, 1.0, 'patients'
        FROM patients
        WHERE phone IS NOT NULL AND TRIM(phone) <> ''
    """)
    # national_id identifiers
    cur.execute("""
        INSERT OR IGNORE INTO patient_identifiers (patient_id, id_type, id_value, confidence, source)
        SELECT id, 'national_id', national_id, 1.0, 'patients'
        FROM patients
        WHERE national_id IS NOT NULL AND TRIM(national_id) <> ''
    """)


def load_patient_maps(cur: sqlite3.Cursor) -> Tuple[Dict[str, int], Dict[str, List[int]]]:
    """
    Build lookup maps:
      phone_map: normalized phone -> patient_id
      name_map: normalized name -> list[patient_id] (for ambiguity detection)
    """
    phone_map: Dict[str, int] = {}
    name_map: Dict[str, List[int]] = {}

    rows = cur.execute("SELECT id, name, phone FROM patients").fetchall()
    for pid, name, phone in rows:
        nname = norm_persian(name or "")
        if nname:
            name_map.setdefault(nname, []).append(pid)
        nphone = norm_phone(phone)
        if nphone:
            # if duplicates exist, keep first; ambiguity handled by name fallback
            phone_map.setdefault(nphone, pid)

    return phone_map, name_map


def build_payments_clean(batch_size: int = 5000):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")
    cur = conn.cursor()

    # 1) base identifiers
    ensure_patient_identifiers_base(cur)
    conn.commit()

    phone_map, name_map = load_patient_maps(cur)

    # 2) iterate stg_payments in batches
    total = cur.execute("SELECT COUNT(*) FROM stg_payments").fetchone()[0]
    print(f"stg_payments total: {total}")

    offset = 0
    inserted = 0
    matched = 0
    unmatched = 0
    ambiguous = 0

    while True:
        rows = cur.execute("""
            SELECT
              id, import_run_id, file_name, sheet_name, row_number, loaded_at, parse_status, parse_error,
              patient_name_raw, phone_raw, insurer_raw, insurer_name_norm, payer_source_norm,
              appointment_date_raw,
              amount_patient_raw, amount_insurer_raw, net_received_raw,
              patient_share_pct, pct_detected
            FROM stg_payments
            ORDER BY id
            LIMIT ? OFFSET ?
        """, (batch_size, offset)).fetchall()

        if not rows:
            break

        for r in rows:
            (stg_id, import_run_id, file_name, sheet_name, row_number, loaded_at, parse_status, parse_error,
             patient_name_raw, phone_raw, insurer_raw, insurer_name_norm, payer_source_norm,
             appointment_date_raw,
             amount_patient_raw, amount_insurer_raw, net_received_raw,
             patient_share_pct, pct_detected) = r

            name_clean, record_no = split_name_and_record_no(patient_name_raw)
            pnorm = norm_phone(phone_raw)
            nname = norm_persian(name_clean or "")

            # resolve patient_id
            patient_id = None
            join_conf = 0.0

            # 1) phone match
            if pnorm and pnorm in phone_map:
                patient_id = phone_map[pnorm]
                join_conf = 1.0

            # 2) name match (exact normalized) if phone missing/unmatched
            if patient_id is None and nname:
                candidates = name_map.get(nname, [])
                if len(candidates) == 1:
                    patient_id = candidates[0]
                    join_conf = 0.90
                elif len(candidates) > 1:
                    ambiguous += 1
                    # enterprise choice: do not guess; keep unmatched but record ambiguity
                    patient_id = None
                    join_conf = 0.0

            if patient_id is None:
                unmatched += 1
            else:
                matched += 1
                # attach record_no to this patient (identity enrichment)
                if record_no:
                    cur.execute("""
                        INSERT OR IGNORE INTO patient_identifiers (patient_id, id_type, id_value, confidence, source)
                        VALUES (?, 'record_no', ?, ?, 'stg_payments')
                    """, (patient_id, record_no, join_conf))

            # deterministic payment_id
            # import_run_id + file_name + sheet_name + row_number is usually stable and unique
            payment_id = sha1(f"{import_run_id}|{file_name}|{sheet_name}|{row_number}")

            amount_patient = to_float(amount_patient_raw)
            amount_insurer = to_float(amount_insurer_raw)
            net_received = to_float(net_received_raw)

            cur.execute("""
                INSERT OR REPLACE INTO payments_clean (
                  payment_id, stg_payment_id, import_run_id, file_name, sheet_name, row_number, loaded_at,
                  record_no, patient_id, join_confidence,
                  patient_name_raw, phone_raw,
                  appointment_date_raw, appointment_date_iso,
                  payer_source_norm, insurer_raw, insurer_name_norm, patient_share_pct, pct_detected,
                  amount_patient, amount_insurer, net_received,
                  parse_status, parse_error,
                  updated_at
                ) VALUES (
                  ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?,
                  ?, ?,
                  ?, NULL,
                  ?, ?, ?, ?, ?,
                  ?, ?, ?,
                  ?, ?,
                  datetime('now')
                )
            """, (
                payment_id, stg_id, import_run_id, file_name, sheet_name, row_number, loaded_at,
                record_no, patient_id, join_conf,
                patient_name_raw, phone_raw,
                appointment_date_raw,
                payer_source_norm, insurer_raw, insurer_name_norm, patient_share_pct, pct_detected,
                amount_patient, amount_insurer, net_received,
                parse_status, parse_error
            ))
            inserted += 1

        conn.commit()
        offset += batch_size
        print(f"processed {min(offset, total)}/{total} | inserted {inserted} | matched {matched} | unmatched {unmatched} | ambiguous_names {ambiguous}")

    conn.close()
    print("DONE.")


if __name__ == "__main__":
    build_payments_clean()