#!/usr/bin/env python3
"""
Fill appointments.raw_text_service and normalize appointments.treatment_type
using staging row_json data with Persian keys.
"""

import sqlite3
import json
from collections import Counter, defaultdict
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "atieh_clinic.db"


def normalize_treatment_type(desc: str) -> str:
    """
    Determine treatment_type based on Persian keywords in description.
    Returns treatment type code, defaults to 'dental_care'.
    """
    if not desc:
        return "dental_care"
    
    desc_lower = desc.lower()
    
    # Check keywords in priority order
    if "اندو" in desc_lower or "ریشه" in desc_lower:
        return "endo"
    elif "ترميم" in desc_lower or "پرکردن" in desc_lower:
        return "restoration"
    elif "روکش" in desc_lower or "پروتز" in desc_lower:
        return "crown_prosthetic"
    elif "جرم" in desc_lower:
        return "scaling"
    elif "جراحي" in desc_lower:
        return "surgery"
    elif "وقت" in desc_lower:
        return "consultation"
    elif "کشيدن" in desc_lower or "کشیدن" in desc_lower:
        return "extraction"
    else:
        return "dental_care"


def build_service_mapping(conn):
    """
    Build mapping from (doctor, insurance) -> most_common_desc
    by parsing row_json from stg_appointments.
    """
    cursor = conn.cursor()
    
    # Read all staging rows with row_json
    cursor.execute("""
        SELECT row_json 
        FROM stg_appointments 
        WHERE row_json IS NOT NULL
    """)
    
    # Track frequency of descriptions per (doctor, insurance) pair
    pair_descriptions = defaultdict(list)
    
    for (row_json_str,) in cursor.fetchall():
        try:
            d = json.loads(row_json_str)
            
            # Extract fields with Persian keys, convert to string to handle floats/NaN
            doctor_raw = d.get("'نام پزشک'")
            insurance_raw = d.get("'سازمان بيمه گر'")
            desc_raw = d.get("'توضيحات'")
            
            # Convert to string and normalize
            doctor = str(doctor_raw).strip() if doctor_raw is not None and str(doctor_raw) != 'nan' else ""
            insurance = str(insurance_raw).strip() if insurance_raw is not None and str(insurance_raw) != 'nan' else ""
            desc = str(desc_raw).strip() if desc_raw is not None and str(desc_raw) != 'nan' else ""
            
            # Skip if description is empty
            if not desc:
                continue
            
            # Add to list for this (doctor, insurance) pair
            key = (doctor, insurance)
            pair_descriptions[key].append(desc)
            
        except (json.JSONDecodeError, KeyError) as e:
            # Skip malformed JSON
            continue
    
    # Build final mapping with most common description per pair
    mapping = {}
    for key, desc_list in pair_descriptions.items():
        if desc_list:
            # Get most common description
            counter = Counter(desc_list)
            most_common_desc = counter.most_common(1)[0][0]
            mapping[key] = most_common_desc
    
    return mapping


def update_appointments(conn, mapping):
    """
    Update appointments table:
    - Fill raw_text_service where null/empty
    - Normalize treatment_type based on service description
    """
    cursor = conn.cursor()
    
    # Find appointments that need updating
    cursor.execute("""
        SELECT 
            id,
            raw_text_doctor,
            raw_text_insurance,
            treatment_type
        FROM appointments
        WHERE (raw_text_service IS NULL OR raw_text_service = '')
          AND raw_text_doctor IS NOT NULL
          AND raw_text_insurance IS NOT NULL
    """)
    
    rows_to_update = cursor.fetchall()
    
    service_filled_count = 0
    treatment_changed_count = 0
    
    for appt_id, doctor, insurance, current_treatment in rows_to_update:
        # Normalize and look up in mapping
        key = (doctor.strip(), insurance.strip())
        
        if key in mapping:
            desc = mapping[key]
            
            # Update raw_text_service
            cursor.execute("""
                UPDATE appointments
                SET raw_text_service = ?
                WHERE id = ?
            """, (desc, appt_id))
            service_filled_count += 1
            
            # Update treatment_type if it's generic or placeholder
            should_update_treatment = (
                current_treatment == "dental_care" or
                (current_treatment and current_treatment.startswith("TREATMENT_"))
            )
            
            if should_update_treatment:
                new_treatment = normalize_treatment_type(desc)
                
                if new_treatment != current_treatment:
                    cursor.execute("""
                        UPDATE appointments
                        SET treatment_type = ?
                        WHERE id = ?
                    """, (new_treatment, appt_id))
                    treatment_changed_count += 1
    
    return service_filled_count, treatment_changed_count


def print_summary(conn, mapping_count, service_filled, treatment_changed):
    """Print summary statistics after update."""
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("PATCH SUMMARY")
    print("="*60)
    print(f"Mapping pairs built: {mapping_count}")
    print(f"Appointments with raw_text_service filled: {service_filled}")
    print(f"Appointments with treatment_type changed: {treatment_changed}")
    
    # Get treatment type distribution
    cursor.execute("""
        SELECT treatment_type, COUNT(*) as cnt
        FROM appointments
        GROUP BY treatment_type
        ORDER BY cnt DESC
        LIMIT 10
    """)
    
    print("\nTop 10 treatment types (after update):")
    print("-" * 60)
    for treatment_type, count in cursor.fetchall():
        print(f"  {treatment_type:30s} : {count:6d}")
    print("="*60 + "\n")


def main():
    """Main execution function."""
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return 1
    
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    
    try:
        print("Building service mapping from staging data...")
        mapping = build_service_mapping(conn)
        print(f"Built mapping with {len(mapping)} (doctor, insurance) pairs")
        
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        print("Updating appointments...")
        service_filled, treatment_changed = update_appointments(conn, mapping)
        
        # Commit transaction
        conn.commit()
        print("[OK] Transaction committed successfully")
        
        # Print summary
        print_summary(conn, len(mapping), service_filled, treatment_changed)
        
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        print("[FAIL] Transaction rolled back")
        return 1
        
    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())
