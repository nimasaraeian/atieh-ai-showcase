#!/usr/bin/env python3
"""
Validate Patient Scoring System integrity and correctness.

Runs various checks to ensure scoring data is accurate and consistent.
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "atieh_clinic.db"


def check_schema(conn):
    """Verify all required columns exist."""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("SCHEMA VALIDATION")
    print("="*70)
    
    # Check appointments columns
    cursor.execute("PRAGMA table_info(appointments)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required_appt_cols = [
        'patient_priority_score',
        'insurance_score',
        'treatment_score',
        'tenure_score',
        'frequency_score'
    ]
    
    missing_appt = [col for col in required_appt_cols if col not in columns]
    
    if missing_appt:
        print(f"[FAIL] Missing columns in appointments: {missing_appt}")
        return False
    else:
        print("[OK] All required columns exist in appointments table")
    
    # Check patients column
    cursor.execute("PRAGMA table_info(patients)")
    columns = {row[1] for row in cursor.fetchall()}
    
    if 'lifetime_value_score' not in columns:
        print("[FAIL] Missing lifetime_value_score column in patients table")
        return False
    else:
        print("[OK] lifetime_value_score column exists in patients table")
    
    return True


def check_data_coverage(conn):
    """Check what percentage of appointments have been scored."""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("DATA COVERAGE")
    print("="*70)
    
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE patient_priority_score IS NOT NULL")
    scored_appts = cursor.fetchone()[0]
    
    # Only count patients who have appointments
    cursor.execute("""
        SELECT COUNT(DISTINCT patient_id) 
        FROM appointments
    """)
    patients_with_appts = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM patients p
        WHERE p.lifetime_value_score IS NOT NULL
    """)
    scored_patients = cursor.fetchone()[0]
    
    coverage_appts = (scored_appts / total_appts * 100) if total_appts > 0 else 0
    coverage_patients = (scored_patients / patients_with_appts * 100) if patients_with_appts > 0 else 0
    
    print(f"Appointments: {scored_appts:,} / {total_appts:,} scored ({coverage_appts:.1f}%)")
    print(f"Patients (with appointments): {scored_patients:,} / {patients_with_appts:,} scored ({coverage_patients:.1f}%)")
    
    if coverage_appts >= 99 and coverage_patients >= 99:
        print("[OK] Excellent data coverage")
        return True
    elif coverage_appts >= 90 and coverage_patients >= 90:
        print("[WARNING] Good coverage but some records missing")
        return True
    else:
        print("[FAIL] Poor data coverage - run backfill script")
        return False


def check_score_ranges(conn):
    """Verify all scores are within expected ranges."""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("SCORE RANGE VALIDATION")
    print("="*70)
    
    checks = {
        'patient_priority_score': (0, 100),
        'insurance_score': (0, 25),
        'treatment_score': (0, 35),
        'tenure_score': (0, 25),
        'frequency_score': (0, 15),
    }
    
    all_valid = True
    
    for col, (min_val, max_val) in checks.items():
        cursor.execute(f"""
            SELECT 
                MIN({col}) as min_score,
                MAX({col}) as max_score,
                COUNT(*) as out_of_range
            FROM appointments
            WHERE {col} IS NOT NULL 
              AND ({col} < ? OR {col} > ?)
        """, (min_val, max_val))
        
        min_score, max_score, out_of_range = cursor.fetchone()
        
        if out_of_range > 0:
            print(f"[FAIL] {col}: {out_of_range} values out of range [{min_val}-{max_val}]")
            print(f"       Found range: {min_score:.2f} - {max_score:.2f}")
            all_valid = False
        else:
            cursor.execute(f"SELECT MIN({col}), MAX({col}) FROM appointments WHERE {col} IS NOT NULL")
            actual_min, actual_max = cursor.fetchone()
            print(f"[OK] {col:25s} range: {actual_min:6.2f} - {actual_max:6.2f}")
    
    return all_valid


def check_score_consistency(conn):
    """Verify total score equals sum of components."""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("SCORE CONSISTENCY CHECK")
    print("="*70)
    
    cursor.execute("""
        SELECT 
            id,
            patient_priority_score,
            insurance_score + treatment_score + tenure_score + frequency_score as calculated_total,
            ABS(patient_priority_score - (insurance_score + treatment_score + tenure_score + frequency_score)) as diff
        FROM appointments
        WHERE patient_priority_score IS NOT NULL
          AND ABS(patient_priority_score - (insurance_score + treatment_score + tenure_score + frequency_score)) > 0.1
        LIMIT 10
    """)
    
    inconsistent = cursor.fetchall()
    
    if inconsistent:
        print(f"[WARNING] Found {len(inconsistent)} appointments with inconsistent scores")
        print("Sample inconsistencies:")
        for appt_id, total, calc, diff in inconsistent[:5]:
            print(f"  Appointment {appt_id}: stored={total:.2f}, calculated={calc:.2f}, diff={diff:.2f}")
        return False
    else:
        print("[OK] All appointment scores are consistent (total = sum of components)")
        return True


def check_patient_lifetime_scores(conn):
    """Verify patient lifetime scores are reasonable."""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("PATIENT LIFETIME SCORE VALIDATION")
    print("="*70)
    
    cursor.execute("""
        SELECT 
            p.id,
            p.lifetime_value_score,
            AVG(a.patient_priority_score) as avg_appt_score,
            MAX(a.patient_priority_score) as max_appt_score,
            COUNT(a.id) as appt_count
        FROM patients p
        JOIN appointments a ON p.id = a.patient_id
        WHERE p.lifetime_value_score IS NOT NULL
          AND a.patient_priority_score IS NOT NULL
        GROUP BY p.id
        LIMIT 5
    """)
    
    print("Sample patient score calculations:")
    all_valid = True
    
    for pid, lifetime, avg, max_score, count in cursor.fetchall():
        expected = (avg * 0.7) + (max_score * 0.3)
        diff = abs(lifetime - expected)
        
        status = "[OK]" if diff < 0.1 else "[FAIL]"
        if diff >= 0.1:
            all_valid = False
        
        print(f"{status} Patient {pid}: lifetime={lifetime:.1f}, expected={expected:.1f} (avg={avg:.1f}, max={max_score:.1f})")
    
    return all_valid


def print_summary_stats(conn):
    """Print overall summary statistics."""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            AVG(patient_priority_score) as avg_score,
            MIN(patient_priority_score) as min_score,
            MAX(patient_priority_score) as max_score,
            COUNT(CASE WHEN patient_priority_score >= 80 THEN 1 END) as excellent,
            COUNT(CASE WHEN patient_priority_score >= 60 AND patient_priority_score < 80 THEN 1 END) as high,
            COUNT(CASE WHEN patient_priority_score >= 40 AND patient_priority_score < 60 THEN 1 END) as medium
        FROM appointments
        WHERE patient_priority_score IS NOT NULL
    """)
    
    total, avg, min_s, max_s, excellent, high, medium = cursor.fetchone()
    
    print(f"Total scored appointments: {total:,}")
    print(f"Average score: {avg:.2f}")
    print(f"Score range: {min_s:.2f} - {max_s:.2f}")
    print(f"\nDistribution:")
    print(f"  Excellent (80+): {excellent:,} ({excellent/total*100:.1f}%)")
    print(f"  High (60-79): {high:,} ({high/total*100:.1f}%)")
    print(f"  Medium (40-59): {medium:,} ({medium/total*100:.1f}%)")


def main():
    """Run all validation checks."""
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return 1
    
    print(f"Validating Patient Scoring System")
    print(f"Database: {DB_PATH}\n")
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        checks = [
            ("Schema", check_schema),
            ("Data Coverage", check_data_coverage),
            ("Score Ranges", check_score_ranges),
            ("Score Consistency", check_score_consistency),
            ("Patient Lifetime Scores", check_patient_lifetime_scores),
        ]
        
        results = {}
        for check_name, check_func in checks:
            try:
                results[check_name] = check_func(conn)
            except Exception as e:
                print(f"\n[ERROR] {check_name} check failed: {e}")
                results[check_name] = False
        
        # Print summary
        print_summary_stats(conn)
        
        # Final verdict
        print("\n" + "="*70)
        print("VALIDATION RESULTS")
        print("="*70)
        
        for check_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {check_name}")
        
        all_passed = all(results.values())
        
        if all_passed:
            print("\n[SUCCESS] All validation checks passed!")
            return 0
        else:
            print("\n[WARNING] Some validation checks failed - review output above")
            return 1
        
    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())
