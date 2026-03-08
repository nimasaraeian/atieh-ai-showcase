"""
Historical Excel file importer with Jalali date conversion.
Handles Persian filenames and column name variants.
"""
import pandas as pd
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.importers.common.normalize import normalize_text, extract_digits_only
from app.importers.common.shamsi import shamsi_to_gregorian_datetime, build_end_datetime
from app.importers.common.hashing import row_hash
from app.importers.common.paths import resolve_repo_path
from app.utils.patient_helpers import build_patient_from_dict
from app.utils.normalize import normalize_payment_type
from models import Patient, Appointment
from database import SessionLocal

logger = logging.getLogger(__name__)


def normalize_fa_key(s: str) -> str:
    """
    Robust Persian header normalization for Excel columns.
    - Remove wrapping quotes (single or double)
    - Normalize Arabic yeh/kaf to Persian: ي→ی, ك→ک
    - Replace ZWNJ with space
    - Collapse multiple spaces
    """
    if not s:
        return ""
    
    # Remove wrapping quotes
    s = s.strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1]
    
    # Normalize Arabic characters to Persian
    s = s.replace('ي', 'ی').replace('ك', 'ک')
    
    # Replace ZWNJ with space
    s = s.replace('\u200c', ' ')
    
    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s)
    
    return s.strip()


def normalize_phone_local(phone: Optional[str]) -> Optional[str]:
    """
    Clean and normalize phone number for matching/storage.
    - Convert to string, strip spaces
    - If contains ; or , pick first segment
    - Remove spaces and non-digit chars except leading +
    - Return None if empty or invalid length (<7)
    """
    if not phone or pd.isna(phone):
        return None
    
    phone_str = str(phone).strip()
    
    if not phone_str:
        return None
    
    # Handle multiple phones separated by ; or ,
    if ';' in phone_str:
        phone_str = phone_str.split(';')[0].strip()
    elif ',' in phone_str:
        phone_str = phone_str.split(',')[0].strip()
    
    # Remove all non-digit characters except leading +
    if phone_str.startswith('+'):
        phone_clean = '+' + ''.join(c for c in phone_str[1:] if c.isdigit())
    else:
        phone_clean = ''.join(c for c in phone_str if c.isdigit())
    
    # Validate length
    if not phone_clean or len(phone_clean) < 7:
        return None
    
    return phone_clean


# Column name mapping (multiple variants for each field)
COLUMN_MAPPINGS = {
    'patient_name': [
        'نام بیمار(تشکیل پرونده شده)', 
        'نام بيمار(تشكيل پرونده شده)',
        'نام و نام خانوادگی',
        'نام بیمار',
        'PatientName',
    ],
    'phone': [
        'موبایل', 
        'تلفن', 
        'شماره تماس', 
        'Phone', 
        'شماره موبایل', 
        'تلفن همراه'
    ],
    'national_id': ['کد ملی', 'NationalID', 'کدملی'],
    'date': [
        'تاریخ', 
        'تاریخ ویزیت', 
        'تاریخ نوبت',
        'تاريخ نوبت',
        'Date', 
        'تاریخ مراجعه'
    ],
    'time': [
        'ساعت', 
        'ساعت نوبت',
        'زمان', 
        'Time'
    ],
    'doctor': [
        'پزشک', 
        'دکتر', 
        'نام پزشک',
        'Doctor'
    ],
    'service': [
        'خدمات', 
        'درمان', 
        'Service', 
        'نوع خدمت', 
        'خدمت'
    ],
    'insurance': [
        'بیمه', 
        'سازمان بیمه گر',
        'سازمان بيمه گر',
        'Insurance', 
        'نوع بیمه'
    ],
    'status': ['وضعیت', 'Status'],
    'duration': ['مدت', 'Duration', 'مدت زمان'],
    'notes': [
        'یادداشت', 
        'توضیحات',
        'توضيحات',
        'Notes', 
        'ملاحظات'
    ],
    'appointment_type': ['نوع نوبت', 'نوع ویزیت'],
}


def find_column(df: pd.DataFrame, field_name: str) -> Optional[str]:
    """
    Find actual column name in DataFrame that matches field.
    Prefers exact match. For partial match (candidate in col), requires
    candidate length >= 12 to avoid e.g. 'نام' matching 'نام سامانه'.
    """
    if field_name not in COLUMN_MAPPINGS:
        return None
    
    candidates = COLUMN_MAPPINGS[field_name]
    cols_normalized = {col: normalize_text(str(col)) for col in df.columns}
    
    # First pass: exact match
    for col, col_n in cols_normalized.items():
        for candidate in candidates:
            cand_n = normalize_text(candidate)
            if col_n == cand_n:
                return col
    
    # Second pass: partial match only for long candidates (avoid 'نام' -> 'نام سامانه')
    for col, col_n in cols_normalized.items():
        for candidate in candidates:
            cand_n = normalize_text(candidate)
            if len(cand_n) >= 12 and cand_n in col_n:
                return col
    
    return None


def safe_get_value(row: pd.Series, column: Optional[str]) -> Optional[str]:
    """
    Safely get value from row, handling NaN and empty strings.
    """
    if column is None or column not in row.index:
        return None
    
    value = row[column]
    
    if pd.isna(value):
        return None
    
    value_str = str(value).strip()
    return value_str if value_str else None


# Names that indicate wrong/missing data from old import - should be overwritten
_BAD_NAMES = frozenset({'دندانپزشکی', 'نامشخص', 'nan', ''})


def _should_update_name(current: Optional[str], new: Optional[str]) -> bool:
    """Update name if current is empty or a known bad value, and new is valid."""
    if not new or not new.strip():
        return False
    if not current:
        return True
    curr = str(current).strip()
    return curr in _BAD_NAMES or curr.lower() == 'nan' or curr.startswith('UNKNOWN_')


def upsert_patient(
    db: Session,
    name: Optional[str],
    phone: Optional[str],
    national_id: Optional[str]
) -> Optional[Patient]:
    """
    Find or create patient with deduplication logic.
    
    Priority:
    1. Match by national_id if available
    2. Match by normalized phone if available
    3. Match by normalized phone + name if both available
    4. Create new patient (requires at least phone or name)
    
    Note: Patient model columns are: id, name, phone, national_id, payment_type, first_visit_date, created_at, updated_at
    """
    phone_norm = normalize_phone_local(phone) if phone else None
    name_norm = normalize_text(name) if name else None
    national_id_clean = extract_digits_only(national_id) if national_id else None
    
    # Require at least phone or name
    if not phone_norm and not name_norm:
        logger.warning("Cannot create patient without phone or name")
        return None
    
    # Try match by national_id first
    if national_id_clean and len(national_id_clean) == 10:
        patient = db.query(Patient).filter(
            Patient.national_id == national_id_clean
        ).first()
        
        if patient:
            # Update phone/name if they were empty or wrong
            updated = False
            if phone_norm and not patient.phone:
                patient.phone = phone_norm
                updated = True
            if name_norm and _should_update_name(patient.name, name_norm):
                patient.name = name_norm
                updated = True
            if updated:
                db.commit()
            return patient
    
    # Try match by phone
    if phone_norm:
        patient = db.query(Patient).filter(Patient.phone == phone_norm).first()
        
        if patient:
            # Update national_id/name if they were empty or wrong
            updated = False
            if national_id_clean and not patient.national_id:
                patient.national_id = national_id_clean
                updated = True
            if name_norm and _should_update_name(patient.name, name_norm):
                patient.name = name_norm
                updated = True
            if updated:
                db.commit()
            return patient
    
    # Create new patient
    # Patient requires: name (NOT NULL), phone (NOT NULL, UNIQUE)
    # We must have at least one of them
    if not phone_norm:
        import uuid
        phone_norm = f"UNKNOWN_{uuid.uuid4().hex}"
    
    # Use build_patient_from_dict to ensure field sanitization
    patient_data = {
        'name': name_norm or "نامشخص",
        'phone': phone_norm,
        'national_id': national_id_clean if national_id_clean and len(national_id_clean) == 10 else None,
        'first_visit_date': datetime.now()
    }
    
    patient = build_patient_from_dict(patient_data)
    
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    return patient


def import_history_excel(
    file_path: str,
    import_run_id: int,
    sheet_name: Any = 0,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Import historical Excel file into staging and final tables.
    
    Args:
        file_path: Relative path to Excel file
        import_run_id: ID of import_runs record
        sheet_name: Sheet name or index (default: 0 for first sheet)
        db: Database session (creates new if None)
    
    Returns:
        Stats dictionary with counts
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    try:
        # Resolve path
        resolved_path = resolve_repo_path(file_path)
        logger.info(f"Importing file: {resolved_path}")
        
        # Read Excel with openpyxl engine
        df = pd.read_excel(resolved_path, sheet_name=sheet_name, engine='openpyxl')
        
        # Normalize column headers
        df.columns = [normalize_fa_key(c) for c in df.columns]
        
        logger.info(f"Loaded {len(df)} rows from sheet '{sheet_name}'")
        logger.info(f"Normalized columns: {list(df.columns)}")
        
        # Find column mappings
        col_map = {}
        for field in COLUMN_MAPPINGS.keys():
            col_map[field] = find_column(df, field)
        
        logger.info(f"Column mappings: {col_map}")
        
        stats = {
            'total_rows': len(df),
            'processed': 0,
            'success': 0,
            'errors': 0,
            'patients_created': 0,
            'patients_updated': 0,
            'appointments_created': 0,
            'appointments_skipped': 0,
        }
        
        # Track patient IDs to count creates vs updates
        patient_ids_seen = set()
        
        # Process each row
        for idx, row in df.iterrows():
            row_number = idx + 2  # Excel row (1-indexed + header)
            stg_id = None
            
            try:
                # Insert into staging table first
                row_json = json.dumps(
                    row.to_dict(),
                    ensure_ascii=False,
                    default=str
                )
                
                # Execute raw SQL for staging (since we don't have ORM models for these tables yet)
                db.execute(
                    text("""
                    INSERT INTO stg_appointments 
                    (import_run_id, file_name, sheet_name, row_number, row_json, loaded_at, parse_status)
                    VALUES (:import_run_id, :file_name, :sheet_name, :row_number, :row_json, :loaded_at, 'pending')
                    """),
                    {
                        "import_run_id": import_run_id,
                        "file_name": Path(file_path).name,
                        "sheet_name": str(sheet_name),
                        "row_number": row_number,
                        "row_json": row_json,
                        "loaded_at": datetime.now().isoformat()
                    }
                )
                stg_id = db.execute(text("SELECT last_insert_rowid()")).scalar()
                
                # Extract values
                patient_name = safe_get_value(row, col_map['patient_name'])
                phone = safe_get_value(row, col_map['phone'])
                national_id = safe_get_value(row, col_map['national_id'])
                date_str = safe_get_value(row, col_map['date'])
                time_str = safe_get_value(row, col_map['time'])
                doctor_raw = safe_get_value(row, col_map['doctor'])
                service_raw = safe_get_value(row, col_map['service'])
                insurance_raw = safe_get_value(row, col_map['insurance'])
                status_raw = safe_get_value(row, col_map['status'])
                duration_str = safe_get_value(row, col_map['duration'])
                notes_raw = safe_get_value(row, col_map['notes'])
                
                # Validate: need at least patient_name or phone
                if not patient_name and not phone:
                    raise ValueError("Row missing both patient_name and phone - cannot create patient")
                
                # Convert date/time
                start_at = shamsi_to_gregorian_datetime(date_str, time_str)
                
                if not start_at:
                    raise ValueError(f"Could not parse date: {date_str} {time_str}")
                
                # Parse duration
                duration_min = 30  # default
                if duration_str:
                    try:
                        duration_min = int(extract_digits_only(duration_str))
                    except:
                        pass
                
                end_at = build_end_datetime(start_at, duration_min)
                
                # Upsert patient
                patient = upsert_patient(db, patient_name, phone, national_id)
                
                if not patient:
                    raise ValueError("Failed to create/find patient")
                
                # Track patient creates vs updates
                if patient.id not in patient_ids_seen:
                    patient_ids_seen.add(patient.id)
                    # Check if patient was just created (first_visit_date is recent)
                    if patient.first_visit_date and (datetime.now() - patient.first_visit_date).total_seconds() < 10:
                        stats['patients_created'] += 1
                    else:
                        stats['patients_updated'] += 1
                
                # Generate source hash for deduplication
                phone_norm = normalize_phone_local(phone) if phone else ""
                source_hash = row_hash(
                    normalize_text(patient_name),
                    phone_norm,
                    extract_digits_only(national_id) if national_id else "",
                    start_at.isoformat() if start_at else "",
                    normalize_text(doctor_raw),
                    normalize_text(service_raw),
                    normalize_text(status_raw)
                )
                
                # Check if appointment already exists
                existing = db.execute(
                    text("SELECT id FROM appointments WHERE source_row_hash = :hash"),
                    {"hash": source_hash}
                ).fetchone()
                
                if existing:
                    stats['appointments_skipped'] += 1
                    logger.debug(f"Row {row_number}: Appointment already exists (hash: {source_hash[:16]}...)")
                    appointment_id = existing[0]
                else:
                    # Create appointment
                    # Determine payment type: when an insurance org is present the
                    # raw value is the org name and the norm is always 'insurance'.
                    # Otherwise fall back to 'CASH' → normalized to 'cash'.
                    insurance_clean = normalize_text(insurance_raw) if insurance_raw else None
                    if insurance_clean:
                        payment_type_raw_val = insurance_raw          # e.g. 'تامین اجتماعی'
                        payment_type_norm_val = "insurance"
                    else:
                        payment_type_raw_val = "CASH"
                        payment_type_norm_val = normalize_payment_type("CASH")   # → 'cash'

                    db.execute(
                        text("""
                        INSERT INTO appointments 
                        (patient_id, appointment_date,
                         payment_type, payment_type_raw, payment_type_norm,
                         treatment_type, priority_score, 
                         status, notes, created_at, 
                         source_row_hash, raw_text_doctor, raw_text_service, raw_text_insurance, import_run_id)
                        VALUES (:patient_id, :appointment_date,
                                :payment_type, :payment_type_raw, :payment_type_norm,
                                :treatment_type, :priority_score,
                                :status, :notes, :created_at, 
                                :source_row_hash, :raw_text_doctor, :raw_text_service, :raw_text_insurance, :import_run_id)
                        """),
                        {
                            "patient_id": patient.id,
                            "appointment_date": start_at.isoformat(),
                            "payment_type": payment_type_norm_val,      # legacy → canonical
                            "payment_type_raw": payment_type_raw_val,
                            "payment_type_norm": payment_type_norm_val,
                            "treatment_type": "dental_care",
                            "priority_score": 0.5,
                            "status": normalize_text(status_raw) if status_raw else 'completed',
                            "notes": normalize_text(notes_raw),
                            "created_at": datetime.now().isoformat(),
                            "source_row_hash": source_hash,
                            "raw_text_doctor": normalize_text(doctor_raw),
                            "raw_text_service": normalize_text(service_raw),
                            "raw_text_insurance": normalize_text(insurance_raw),
                            "import_run_id": import_run_id
                        }
                    )
                    appointment_id = db.execute(text("SELECT last_insert_rowid()")).scalar()
                    stats['appointments_created'] += 1
                
                # Update staging status
                db.execute(
                    text("UPDATE stg_appointments SET parse_status = 'ok', patient_id = :patient_id, appointment_id = :appointment_id WHERE id = :id"),
                    {"patient_id": patient.id, "appointment_id": appointment_id, "id": stg_id}
                )
                
                stats['success'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                error_msg = str(e)
                logger.error(f"Row {row_number} error: {error_msg}")
                db.rollback()  # Allow processing to continue after IntegrityError etc.
                
                # Update staging with error (only if stg_id was created)
                if stg_id:
                    try:
                        db.execute(
                            text("UPDATE stg_appointments SET parse_status = 'error', parse_error = :error WHERE id = :id"),
                            {"error": error_msg[:500], "id": stg_id}
                        )
                    except:
                        pass  # Don't fail on staging update failure
            
            stats['processed'] += 1
            
            # Commit every 2000 rows to prevent long-running transactions and reduce lock contention
            if stats['processed'] % 2000 == 0:
                db.commit()
                logger.info(f"Processed {stats['processed']}/{stats['total_rows']} rows (committed batch)...")
        
        # Final commit
        db.commit()
        
        logger.info(f"Import complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if close_db and db:
            db.close()


if __name__ == "__main__":
    """Quick schema check - print Patient columns without running import"""
    print("Patient model columns:")
    print("  - id")
    print("  - name")
    print("  - phone")
    print("  - national_id")
    print("  - payment_type")
    print("  - first_visit_date")
    print("  - created_at")
    print("  - updated_at")
    print("\nNote: 'mobile' and 'family' are NOT valid Patient columns!")
