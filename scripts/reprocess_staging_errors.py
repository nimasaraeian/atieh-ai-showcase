#!/usr/bin/env python3
"""
Reprocess staging rows where parse_status IN ('error', 'pending').

Uses normalize-and-scan key lookup so Arabic/Persian variants and wrapping
quotes in column names are handled transparently.

Patient schema used for upserts:
- Patient columns: id, name, phone, national_id, first_visit_date, created_at, updated_at, payment_type, lifetime_value_score
- NO 'family' field
- NO 'mobile' field
- phone is stored in 'phone' column
"""

import sys
import sqlite3
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from collections import Counter

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.importers.common.normalize import normalize_text, extract_digits_only
from app.importers.common.shamsi import shamsi_to_gregorian_datetime
from app.importers.common.hashing import row_hash
from app.utils.patient_helpers import build_patient_from_dict
from app.utils.normalize import normalize_payment_type

DB_PATH = Path(__file__).parent.parent / "atieh_clinic.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_phone_number(phone_str: Optional[str]) -> Optional[str]:
    """
    Normalize phone number from row_json.

    Strategy for semicolon-delimited fields (e.g. '0;09141631556',
    'ژ;09055932754', '1;09141409645'):
    1. Split on ';', strip each token, remove all non-digit characters.
    2. Prefer Iranian mobile format: 11 digits starting with '09'.
    3. Fall back to any digit sequence with length >= 10.
    4. Fall back to any digit sequence with length >= 7.
    5. If nothing qualifies, return None.
    """
    if not phone_str:
        return None
    s = str(phone_str).strip()
    if s.lower() in ("nan", "none", ""):
        return None

    # Split and extract pure-digit tokens
    raw_tokens = s.split(";") if ";" in s else [s]
    digit_tokens = []
    for t in raw_tokens:
        clean = "".join(c for c in t if c.isdigit())
        if clean:
            digit_tokens.append(clean)

    if not digit_tokens:
        return None

    # Pass 1: Iranian mobile (09XXXXXXXXX, exactly 11 digits)
    for dt in digit_tokens:
        if len(dt) == 11 and dt.startswith("09"):
            return dt

    # Pass 2: any digit sequence >= 10 digits
    for dt in digit_tokens:
        if len(dt) >= 10:
            return dt

    # Pass 3: any digit sequence >= 7 digits
    for dt in digit_tokens:
        if len(dt) >= 7:
            return dt

    return None


# ---------------------------------------------------------------------------
# Normalize-and-scan helpers
# ---------------------------------------------------------------------------

def _norm_key(s: str) -> str:
    """
    Normalize a dictionary key for comparison:
    - Strip surrounding whitespace
    - Strip a single layer of wrapping quote characters (' or ")
    - Normalize Arabic yeh/kaf to Persian equivalents
    - Collapse ZWNJ and non-breaking space to regular space
    - Collapse runs of whitespace
    """
    if s is None:
        return ""
    s = str(s).strip()
    if len(s) >= 2 and ((s[0] == s[-1] == "'") or (s[0] == s[-1] == '"')):
        s = s[1:-1].strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("\u200c", " ").replace("\u00a0", " ")
    s = " ".join(s.split())
    return s


def _clean_val(v) -> Optional[str]:
    """Return None for empty / nan / None values, otherwise a stripped string."""
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() in ("none", "nan"):
        return None
    return s


def find_in_dict(d: dict, candidates: list) -> Optional[str]:
    """
    Scan *d* for the first candidate whose normalized form matches a
    normalized key in *d*.  Returns the raw (un-normalized) value or None.
    """
    if not isinstance(d, dict):
        return None
    norm_map = {_norm_key(k): v for k, v in d.items()}
    for candidate in candidates:
        v = norm_map.get(_norm_key(candidate))
        v = _clean_val(v)
        if v is not None:
            return v
    return None


# Candidate lists – ordered most-specific first
DATE_CANDIDATES = [
    "تاریخ نوبت", "تاريخ نوبت",
    "تاریخ", "تاریخ مراجعه", "تاریخ ویزیت",
    "Date",
]
TIME_CANDIDATES = [
    "ساعت نوبت",
    "ساعت", "زمان",
    "Time",
]
PATIENT_CANDIDATES = [
    "نام بیمار(تشکیل پرونده شده)", "نام بيمار(تشكيل پرونده شده)",
    "نام و نام خانوادگی", "نام بیمار", "نام",
    "Patient", "PatientName",
]
PHONE_CANDIDATES = [
    "تلفن", "شماره تماس", "شماره موبایل",
    "موبایل", "موبايل", "تلفن همراه",
    "Mobile", "Phone",
]
DOCTOR_CANDIDATES = [
    "نام پزشک", "پزشک", "دکتر",
    "Doctor",
]
SERVICE_CANDIDATES = [
    "توضیحات", "توضيحات",
    "خدمات", "درمان", "نوع خدمت", "خدمت",
    "Service",
]
INSURANCE_CANDIDATES = [
    "سازمان بیمه گر", "سازمان بيمه گر",
    "بیمه", "نوع بیمه",
    "Insurance",
]

# ---------------------------------------------------------------------------


def extract_from_row_json(row_json_str: str) -> Dict[str, Any]:
    """
    Extract appointment fields from a stored row_json string.

    Uses normalize-and-scan so that:
    - wrapping quote characters in key names are ignored
    - Arabic ي / ك variants match Persian ی / ک equivalents
    - ZWNJ / non-breaking spaces are treated as regular spaces
    """
    try:
        d = json.loads(row_json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    raw_phone = find_in_dict(d, PHONE_CANDIDATES)

    return {
        "date":         find_in_dict(d, DATE_CANDIDATES),
        "time":         find_in_dict(d, TIME_CANDIDATES),
        "patient_name": find_in_dict(d, PATIENT_CANDIDATES),
        "phone":        normalize_phone_number(raw_phone) if raw_phone else None,
        "doctor":       find_in_dict(d, DOCTOR_CANDIDATES),
        "service":      find_in_dict(d, SERVICE_CANDIDATES),
        "insurance":    find_in_dict(d, INSURANCE_CANDIDATES),
    }


def upsert_patient_from_json(conn, extracted: Dict[str, Any], appt_date: datetime) -> Optional[int]:
    """
    Find or create patient using extracted data.
    
    Uses build_patient_from_dict to ensure proper field sanitization.
    Patient schema: id, name, phone, national_id, first_visit_date, created_at, updated_at, payment_type, lifetime_value_score
    """
    name = extracted.get('patient_name')
    phone = extracted.get('phone')
    
    # Must have at least name or phone
    if not name and not phone:
        raise ValueError("Cannot create patient without name or phone")
    
    # Normalize
    name_norm = normalize_text(name) if name else None
    phone_norm = phone if phone else None
    
    cursor = conn.cursor()
    
    # Try to find existing patient by phone
    if phone_norm:
        cursor.execute(
            "SELECT id, name, phone, first_visit_date FROM patients WHERE phone = ?",
            (phone_norm,)
        )
        existing = cursor.fetchone()
        
        if existing:
            patient_id, existing_name, existing_phone, first_visit = existing
            
            # Update name if it was empty
            if name_norm and not existing_name:
                cursor.execute(
                    "UPDATE patients SET name = ? WHERE id = ?",
                    (name_norm, patient_id)
                )
                conn.commit()
            
            return patient_id
    
    # Create new patient using helper to ensure field sanitization
    if not phone_norm:
        # Generate placeholder phone
        phone_norm = f"UNKNOWN_{int(datetime.now().timestamp() * 1000)}"
    
    if not name_norm:
        name_norm = "نامشخص"
    
    # Use appointment date as first_visit_date
    first_visit_date = appt_date.isoformat() if appt_date else datetime.now().isoformat()
    
    # Build patient using helper function (ensures no family/mobile fields)
    patient_data = {
        'name': name_norm,
        'phone': phone_norm,
        'first_visit_date': first_visit_date,
        'created_at': datetime.now().isoformat()
    }
    
    # Use the helper to create Patient with sanitization
    patient = build_patient_from_dict(patient_data)
    
    # Insert into database manually (we're using raw SQL connection, not ORM session)
    cursor.execute(
        """
        INSERT INTO patients (name, phone, first_visit_date, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (patient.name, patient.phone, first_visit_date, datetime.now().isoformat())
    )
    conn.commit()
    
    patient_id = cursor.lastrowid
    return patient_id


def determine_payment_type(insurance: Optional[str]) -> str:
    """
    Return the *normalized* payment_type string (NEVER NULL).

    When an insurance organisation is present the payment is 'insurance'.
    Otherwise fall back to 'cash'.  The raw org name is preserved separately
    in payment_type_raw.
    """
    if not insurance or not str(insurance).strip() or str(insurance).strip().lower() in ("nan", "none", ""):
        return normalize_payment_type("CASH")   # → 'cash'
    # The insurance column holds the org name; any non-empty value means insurance.
    return "insurance"


def reprocess_staging_row(conn, stg_id: int, row_json_str: str, import_run_id: int) -> Dict[str, Any]:
    """
    Reprocess a single staging row.
    
    Returns: dict with status='ok' or status='error' and error message
    """
    cursor = conn.cursor()
    
    try:
        # Extract fields from row_json
        extracted = extract_from_row_json(row_json_str)

        # Missing-identity guard: cannot create a patient without name or phone
        if not extracted.get('patient_name') and not extracted.get('phone'):
            cursor.execute(
                "UPDATE stg_appointments SET parse_status='skipped', parse_error='missing_identity' WHERE id=?",
                (stg_id,)
            )
            conn.commit()
            return {'status': 'skipped', 'error': 'missing_identity'}

        # Parse date/time
        date_str = extracted.get('date')
        time_str = extracted.get('time')
        
        appt_datetime = shamsi_to_gregorian_datetime(date_str, time_str)
        
        if not appt_datetime:
            raise ValueError(f"Could not parse date/time: {date_str} {time_str}")
        
        # Upsert patient
        patient_id = upsert_patient_from_json(conn, extracted, appt_datetime)
        
        if not patient_id:
            raise ValueError("Failed to create/find patient")
        
        # Generate source hash for deduplication
        phone_norm = extracted.get('phone') or ""
        name_norm = normalize_text(extracted.get('patient_name')) if extracted.get('patient_name') else ""
        
        source_hash = row_hash(
            name_norm,
            phone_norm,
            "",  # national_id not in row_json
            appt_datetime.isoformat(),
            normalize_text(extracted.get('doctor')),
            normalize_text(extracted.get('service')),
            ""  # status not in row_json
        )
        
        # Check if appointment already exists
        cursor.execute(
            "SELECT id FROM appointments WHERE source_row_hash = ?",
            (source_hash,)
        )
        existing_appt = cursor.fetchone()
        
        if existing_appt:
            appointment_id = existing_appt[0]
        else:
            insurance_val = extracted.get('insurance')
            insurance_clean = normalize_text(insurance_val) if insurance_val else None

            # Raw: preserve the original insurance org name when present, else 'CASH'
            pt_raw  = insurance_val if insurance_clean else "CASH"
            pt_norm = determine_payment_type(insurance_val)   # 'insurance' or 'cash'

            cursor.execute(
                """
                INSERT INTO appointments
                (patient_id, appointment_date,
                 payment_type, payment_type_raw, payment_type_norm,
                 treatment_type, priority_score,
                 status, created_at, source_row_hash,
                 raw_text_doctor, raw_text_service, raw_text_insurance, import_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    appt_datetime.isoformat(),
                    pt_norm,          # legacy → canonical
                    pt_raw,
                    pt_norm,
                    "dental_care",
                    0.5,
                    "completed",
                    datetime.now().isoformat(),
                    source_hash,
                    normalize_text(extracted.get("doctor")),
                    normalize_text(extracted.get("service")),
                    normalize_text(insurance_val),
                    import_run_id,
                )
            )
            conn.commit()
            appointment_id = cursor.lastrowid
        
        # Update staging row to success
        cursor.execute(
            """
            UPDATE stg_appointments 
            SET parse_status = 'ok', parse_error = NULL, patient_id = ?, appointment_id = ?
            WHERE id = ?
            """,
            (patient_id, appointment_id, stg_id)
        )
        conn.commit()
        
        return {'status': 'ok', 'patient_id': patient_id, 'appointment_id': appointment_id}
        
    except Exception as e:
        error_msg = str(e)[:500]
        
        # Update staging row with error
        cursor.execute(
            "UPDATE stg_appointments SET parse_error = ? WHERE id = ?",
            (error_msg, stg_id)
        )
        conn.commit()
        
        return {'status': 'error', 'error': error_msg}


def reprocess_errors(import_run_id: Optional[int] = None, limit: Optional[int] = None):
    """
    Reprocess error rows from staging table.
    
    Args:
        import_run_id: If specified, only reprocess errors from this run
        limit: Maximum number of rows to reprocess (None = all)
    """
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return
    
    # Connect with WAL mode and busy_timeout
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    
    cursor = conn.cursor()
    
    try:
        # Get count of rows to reprocess (both 'error' and 'pending')
        where_clause = "WHERE parse_status IN ('error', 'pending')"
        params = []

        if import_run_id is not None:
            where_clause += " AND import_run_id = ?"
            params.append(import_run_id)

        cursor.execute(f"SELECT COUNT(*) FROM stg_appointments {where_clause}", params)
        total_rows = cursor.fetchone()[0]

        logger.info(f"Found {total_rows:,} rows to reprocess (error + pending)")

        if total_rows == 0:
            logger.info("No rows to reprocess")
            return

        # Fetch all target rows
        limit_clause = f"LIMIT {limit}" if limit else ""
        cursor.execute(
            f"SELECT id, row_json, import_run_id FROM stg_appointments {where_clause} {limit_clause}",
            params
        )

        target_rows = cursor.fetchall()

        logger.info(f"Reprocessing {len(target_rows)} rows...")

        # Track statistics
        stats = {
            'processed': 0,
            'success': 0,
            'skipped': 0,
            'still_error': 0,
            'new_errors': Counter()
        }

        # Process each row
        for stg_id, row_json_str, run_id in target_rows:
            result = reprocess_staging_row(conn, stg_id, row_json_str, run_id)

            stats['processed'] += 1

            if result['status'] == 'ok':
                stats['success'] += 1
            elif result['status'] == 'skipped':
                stats['skipped'] += 1
            else:
                stats['still_error'] += 1
                stats['new_errors'][result['error'][:100]] += 1

            # Log progress every 100 rows
            if stats['processed'] % 100 == 0:
                logger.info(f"Processed {stats['processed']}/{len(target_rows)} rows...")

        # Print summary
        print("\n" + "="*70)
        print("REPROCESSING SUMMARY")
        print("="*70)
        print(f"Total processed: {stats['processed']:,}")
        print(f"Successful:      {stats['success']:,} ({stats['success']/stats['processed']*100:.1f}%)")
        print(f"Skipped:         {stats['skipped']:,} ({stats['skipped']/stats['processed']*100:.1f}%)")
        print(f"Still errors:    {stats['still_error']:,} ({stats['still_error']/stats['processed']*100:.1f}%)")

        if stats['new_errors']:
            print("\nTop remaining errors:")
            for error, count in stats['new_errors'].most_common(10):
                print(f"  {count:5,}x: {error}")
        
        # Show updated parse_status counts
        print("\n" + "="*70)
        print("PARSE STATUS COUNTS (AFTER REPROCESSING)")
        print("="*70)
        
        cursor.execute("""
            SELECT parse_status, COUNT(*) as count
            FROM stg_appointments
            GROUP BY parse_status
            ORDER BY count DESC
        """)
        
        for status, count in cursor.fetchall():
            print(f"  {status:10s}: {count:8,}")
        
        print("="*70 + "\n")
        
    finally:
        conn.close()


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reprocess staging errors with correct Patient schema"
    )
    parser.add_argument(
        "--import-run-id",
        type=int,
        help="Only reprocess errors from this import run ID"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of rows to reprocess (default: all)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("REPROCESS STAGING ERRORS")
    print("="*70)
    print(f"Database: {DB_PATH}")
    
    if args.import_run_id:
        print(f"Import run ID: {args.import_run_id}")
    else:
        print("Import run ID: ALL")
    
    if args.limit:
        print(f"Limit: {args.limit} rows")
    else:
        print("Limit: None (process all errors)")
    
    print("="*70 + "\n")
    
    reprocess_errors(
        import_run_id=args.import_run_id,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
