#!/usr/bin/env python3
"""
Backfill patient priority scores for all appointments.

Computes a patient_priority_score (0-100) based on:
- Insurance value (0-25 points)
- Treatment value (0-35 points)
- Patient tenure (0-25 points)
- Appointment frequency (0-15 points)
"""

import sqlite3
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
from typing import Dict, Tuple


DB_PATH = Path(__file__).parent.parent / "atieh_clinic.db"


# ============================================================================
# CONFIGURATION - All scoring weights and mappings
# ============================================================================
CONFIG = {
    # Insurance scoring (0-25 points)
    "insurance_scores": {
        "CASH": 25,
        "INSURANCE_1": 22,
        "INSURANCE_2": 20,
        "INSURANCE_3": 23,
        "INSURANCE_4": 18,
        "INSURANCE_5": 15,
        "INSURANCE_6": 16,
        "INSURANCE_7": 19,
        "INSURANCE_8": 17,
        "INSURANCE_9": 14,
        "INSURANCE_10": 16,
        "INSURANCE_11": 15,
        "INSURANCE_12": 18,
        "INSURANCE_13": 17,
        "INSURANCE_14": 20,
        "INSURANCE_15": 16,
        "INSURANCE_16": 19,
        "INSURANCE_17": 21,
        "INSURANCE_18": 24,
        "INSURANCE_19": 15,
        "INSURANCE_20": 14,
        "default": 10,  # Unknown insurance
    },
    
    # Treatment scoring (0-35 points)
    "treatment_scores": {
        "endo": 35,
        "crown_prosthetic": 32,
        "surgery": 30,
        "restoration": 24,
        "extraction": 22,
        "scaling": 18,
        "consultation": 10,
        "dental_care": 12,
        "default": 12,  # Unknown treatment
    },
    
    # Tenure scoring parameters
    "tenure": {
        "max_points": 25,
        "years_for_max": 1.0,  # 1 year = max points
    },
    
    # Frequency scoring parameters
    "frequency": {
        "max_points": 15,
        "points_per_appointment": 1.5,
    },
}


# ============================================================================
# Scoring Functions
# ============================================================================

def get_insurance_score(payment_type: str) -> float:
    """Calculate insurance score (0-25) based on payment type."""
    if not payment_type:
        return CONFIG["insurance_scores"]["default"]
    
    payment_type_upper = payment_type.upper()
    return CONFIG["insurance_scores"].get(
        payment_type_upper,
        CONFIG["insurance_scores"]["default"]
    )


def get_treatment_score(treatment_type: str) -> float:
    """Calculate treatment score (0-35) based on treatment type."""
    if not treatment_type:
        return CONFIG["treatment_scores"]["default"]
    
    treatment_type_lower = treatment_type.lower()
    
    # Handle TREATMENT_* codes as default
    if treatment_type_lower.startswith("treatment_"):
        return CONFIG["treatment_scores"]["default"]
    
    return CONFIG["treatment_scores"].get(
        treatment_type_lower,
        CONFIG["treatment_scores"]["default"]
    )


def calculate_tenure_score(first_appt_date: date, appt_date: date) -> float:
    """
    Calculate tenure score (0-25) based on days since first appointment.
    
    tenure_days = (appt_date - first_appt_date).days
    tenure_score = min(max_points, (tenure_days / 365) * max_points)
    """
    if not first_appt_date or not appt_date:
        return 0.0
    
    tenure_days = (appt_date - first_appt_date).days
    if tenure_days < 0:
        return 0.0
    
    max_points = CONFIG["tenure"]["max_points"]
    years_for_max = CONFIG["tenure"]["years_for_max"]
    
    tenure_years = tenure_days / 365.0
    score = (tenure_years / years_for_max) * max_points
    
    return min(max_points, score)


def calculate_frequency_score(appointment_count: int) -> float:
    """
    Calculate frequency bonus (0-15) based on total appointments.
    
    frequency_score = min(max_points, appointments_count * points_per_appointment)
    """
    max_points = CONFIG["frequency"]["max_points"]
    points_per_appt = CONFIG["frequency"]["points_per_appointment"]
    
    score = appointment_count * points_per_appt
    return min(max_points, score)


def calculate_patient_priority_score(
    insurance_score: float,
    treatment_score: float,
    tenure_score: float,
    frequency_score: float
) -> float:
    """
    Calculate final patient priority score (0-100).
    
    Sums all component scores and clamps to [0, 100].
    """
    total = insurance_score + treatment_score + tenure_score + frequency_score
    return max(0.0, min(100.0, total))


# ============================================================================
# Data Loading and Processing
# ============================================================================

def load_patient_data(conn) -> Dict[int, Tuple[date, int]]:
    """
    Load patient metadata: first appointment date and total appointment count.
    
    Returns: {patient_id: (first_appt_date, total_appointments)}
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            patient_id,
            MIN(DATE(appointment_date)) as first_appt_date,
            COUNT(*) as appointment_count
        FROM appointments
        GROUP BY patient_id
    """)
    
    patient_data = {}
    for patient_id, first_appt_str, appt_count in cursor.fetchall():
        first_appt_date = datetime.strptime(first_appt_str, "%Y-%m-%d").date()
        patient_data[patient_id] = (first_appt_date, appt_count)
    
    return patient_data


def backfill_appointment_scores(conn, patient_data: Dict[int, Tuple[date, int]]):
    """
    Calculate and update scores for all appointments.
    
    Returns statistics about the scoring.
    """
    cursor = conn.cursor()
    
    # Fetch all appointments
    cursor.execute("""
        SELECT 
            id,
            patient_id,
            DATE(appointment_date) as appt_date,
            payment_type,
            treatment_type
        FROM appointments
        ORDER BY patient_id, appointment_date
    """)
    
    appointments = cursor.fetchall()
    
    print(f"Processing {len(appointments)} appointments...")
    
    updates = []
    score_breakdown_samples = []  # Store top samples for logging
    
    for appt_id, patient_id, appt_date_str, payment_type, treatment_type in appointments:
        appt_date = datetime.strptime(appt_date_str, "%Y-%m-%d").date()
        
        # Get patient metadata
        if patient_id not in patient_data:
            continue
        
        first_appt_date, total_appts = patient_data[patient_id]
        
        # Calculate component scores
        insurance_score = get_insurance_score(payment_type)
        treatment_score = get_treatment_score(treatment_type)
        tenure_score = calculate_tenure_score(first_appt_date, appt_date)
        frequency_score = calculate_frequency_score(total_appts)
        
        # Calculate final score
        priority_score = calculate_patient_priority_score(
            insurance_score, treatment_score, tenure_score, frequency_score
        )
        
        # Store for batch update
        updates.append((
            priority_score,
            insurance_score,
            treatment_score,
            tenure_score,
            frequency_score,
            appt_id
        ))
        
        # Keep sample for logging
        if len(score_breakdown_samples) < 20:
            score_breakdown_samples.append({
                "appt_id": appt_id,
                "patient_id": patient_id,
                "appt_date": appt_date_str,
                "payment_type": payment_type,
                "treatment_type": treatment_type,
                "insurance_score": insurance_score,
                "treatment_score": treatment_score,
                "tenure_score": tenure_score,
                "frequency_score": frequency_score,
                "priority_score": priority_score,
            })
    
    # Batch update
    print(f"Updating {len(updates)} appointment scores...")
    cursor.executemany("""
        UPDATE appointments
        SET 
            patient_priority_score = ?,
            insurance_score = ?,
            treatment_score = ?,
            tenure_score = ?,
            frequency_score = ?
        WHERE id = ?
    """, updates)
    
    return score_breakdown_samples


def update_patient_lifetime_scores(conn):
    """
    Calculate and update lifetime_value_score for each patient.
    
    Uses average of their appointment priority scores.
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            patient_id,
            AVG(patient_priority_score) as avg_score,
            MAX(patient_priority_score) as max_score,
            COUNT(*) as appt_count
        FROM appointments
        WHERE patient_priority_score IS NOT NULL
        GROUP BY patient_id
    """)
    
    updates = []
    for patient_id, avg_score, max_score, appt_count in cursor.fetchall():
        # Lifetime value = weighted average favoring max score
        lifetime_score = (avg_score * 0.7) + (max_score * 0.3)
        updates.append((lifetime_score, patient_id))
    
    print(f"Updating {len(updates)} patient lifetime scores...")
    cursor.executemany("""
        UPDATE patients
        SET lifetime_value_score = ?
        WHERE id = ?
    """, updates)


# ============================================================================
# Reporting
# ============================================================================

def print_score_breakdown_samples(samples):
    """Print detailed breakdown for sample appointments."""
    print("\n" + "="*80)
    print("SCORE BREAKDOWN - Sample Appointments (First 20)")
    print("="*80)
    
    for i, sample in enumerate(samples[:20], 1):
        print(f"\n#{i} Appointment ID: {sample['appt_id']} | Patient: {sample['patient_id']}")
        print(f"   Date: {sample['appt_date']}")
        print(f"   Payment: {sample['payment_type']:20s} -> Insurance Score: {sample['insurance_score']:5.1f}")
        print(f"   Treatment: {sample['treatment_type']:20s} -> Treatment Score: {sample['treatment_score']:5.1f}")
        print(f"   Tenure Score: {sample['tenure_score']:5.1f}")
        print(f"   Frequency Score: {sample['frequency_score']:5.1f}")
        print(f"   ---------------------------------------------------------")
        print(f"   TOTAL PRIORITY SCORE: {sample['priority_score']:.1f}/100")


def print_statistics(conn):
    """Print summary statistics about the scoring."""
    cursor = conn.cursor()
    
    # Appointment score stats
    cursor.execute("""
        SELECT 
            MIN(patient_priority_score) as min_score,
            AVG(patient_priority_score) as avg_score,
            MAX(patient_priority_score) as max_score,
            COUNT(*) as total_scored
        FROM appointments
        WHERE patient_priority_score IS NOT NULL
    """)
    
    min_score, avg_score, max_score, total_scored = cursor.fetchone()
    
    print("\n" + "="*80)
    print("SCORING STATISTICS")
    print("="*80)
    print(f"Total appointments scored: {total_scored:,}")
    print(f"Priority Score Range: {min_score:.1f} - {max_score:.1f}")
    print(f"Average Priority Score: {avg_score:.1f}")
    
    # Top 10 patients by lifetime value
    cursor.execute("""
        SELECT 
            p.id,
            p.name,
            p.lifetime_value_score,
            COUNT(a.id) as appt_count,
            AVG(a.patient_priority_score) as avg_appt_score,
            MAX(a.patient_priority_score) as max_appt_score
        FROM patients p
        JOIN appointments a ON p.id = a.patient_id
        WHERE p.lifetime_value_score IS NOT NULL
        GROUP BY p.id, p.name, p.lifetime_value_score
        ORDER BY p.lifetime_value_score DESC
        LIMIT 10
    """)
    
    print("\n" + "-"*80)
    print("TOP 10 HIGHEST VALUE PATIENTS")
    print("-"*80)
    print(f"{'Rank':<6} {'Patient ID':<12} {'Name':<25} {'Lifetime':<10} {'Avg':<8} {'Max':<8} {'Appts':<8}")
    print("-"*80)
    
    for rank, (pid, name, lifetime, appt_count, avg_score, max_score) in enumerate(cursor.fetchall(), 1):
        # Handle Persian/Unicode characters safely
        name_safe = name[:24] if name else ""
        try:
            print(f"{rank:<6} {pid:<12} {name_safe:<25} {lifetime:>8.1f}  {avg_score:>6.1f}  {max_score:>6.1f}  {appt_count:>6}")
        except UnicodeEncodeError:
            # Fallback for names with problematic characters
            name_ascii = name_safe.encode('ascii', 'ignore').decode('ascii')
            print(f"{rank:<6} {pid:<12} {name_ascii:<25} {lifetime:>8.1f}  {avg_score:>6.1f}  {max_score:>6.1f}  {appt_count:>6}")
    
    # Score distribution
    cursor.execute("""
        SELECT 
            CASE 
                WHEN patient_priority_score >= 80 THEN '80-100 (Excellent)'
                WHEN patient_priority_score >= 60 THEN '60-79 (High)'
                WHEN patient_priority_score >= 40 THEN '40-59 (Medium)'
                WHEN patient_priority_score >= 20 THEN '20-39 (Low)'
                ELSE '0-19 (Very Low)'
            END as score_range,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
        FROM appointments
        WHERE patient_priority_score IS NOT NULL
        GROUP BY score_range
        ORDER BY MIN(patient_priority_score) DESC
    """)
    
    print("\n" + "-"*80)
    print("SCORE DISTRIBUTION")
    print("-"*80)
    for score_range, count, pct in cursor.fetchall():
        bar = "#" * int(pct / 2)
        print(f"{score_range:<25} {count:>6} ({pct:>5.1f}%) {bar}")
    
    print("="*80 + "\n")


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main execution function."""
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return 1
    
    print(f"Connecting to database: {DB_PATH}")
    print("Starting patient priority scoring backfill...\n")
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Step 1: Load patient metadata
        print("Loading patient metadata...")
        patient_data = load_patient_data(conn)
        print(f"Loaded data for {len(patient_data)} patients")
        
        # Step 2: Calculate and update appointment scores
        print("\nCalculating appointment scores...")
        score_samples = backfill_appointment_scores(conn, patient_data)
        
        # Step 3: Calculate and update patient lifetime scores
        print("\nCalculating patient lifetime scores...")
        update_patient_lifetime_scores(conn)
        
        # Commit transaction
        conn.commit()
        print("\n[OK] Transaction committed successfully")
        
        # Print reports
        print_score_breakdown_samples(score_samples)
        print_statistics(conn)
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        print("[FAIL] Transaction rolled back")
        return 1
        
    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())
