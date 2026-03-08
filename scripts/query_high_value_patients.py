#!/usr/bin/env python3
"""
Query high-value patients and appointments based on priority scores.

Usage examples:
    python scripts/query_high_value_patients.py --top 20
    python scripts/query_high_value_patients.py --min-score 80
    python scripts/query_high_value_patients.py --treatment endo
"""

import sqlite3
import argparse
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent.parent / "atieh_clinic.db"


def query_top_patients(conn, limit: int = 10):
    """Query top patients by lifetime value score."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.id,
            p.name,
            p.phone,
            p.lifetime_value_score,
            COUNT(a.id) as total_appointments,
            AVG(a.patient_priority_score) as avg_appt_score,
            MAX(a.patient_priority_score) as max_appt_score,
            SUM(CASE WHEN a.final_amount_paid IS NOT NULL THEN a.final_amount_paid ELSE 0 END) as total_revenue
        FROM patients p
        JOIN appointments a ON p.id = a.patient_id
        WHERE p.lifetime_value_score IS NOT NULL
        GROUP BY p.id, p.name, p.phone, p.lifetime_value_score
        ORDER BY p.lifetime_value_score DESC
        LIMIT ?
    """, (limit,))
    
    print("\n" + "="*100)
    print(f"TOP {limit} HIGHEST VALUE PATIENTS")
    print("="*100)
    print(f"{'Rank':<6} {'ID':<8} {'Name':<25} {'Phone':<15} {'Lifetime':<10} {'Appts':<8} {'Avg':<8} {'Revenue':<12}")
    print("-"*100)
    
    for rank, (pid, name, phone, lifetime, appts, avg_score, max_score, revenue) in enumerate(cursor.fetchall(), 1):
        name_safe = (name[:23] if name else "").ljust(25)
        phone_safe = (phone if phone else "").ljust(15)
        try:
            print(f"{rank:<6} {pid:<8} {name_safe} {phone_safe} {lifetime:>8.1f}  {appts:>6}  {avg_score:>6.1f}  {revenue:>10.0f}")
        except UnicodeEncodeError:
            name_ascii = name_safe.encode('ascii', 'ignore').decode('ascii').ljust(25)
            print(f"{rank:<6} {pid:<8} {name_ascii} {phone_safe} {lifetime:>8.1f}  {appts:>6}  {avg_score:>6.1f}  {revenue:>10.0f}")
    
    print("="*100 + "\n")


def query_appointments_by_score(conn, min_score: float, limit: int = 50):
    """Query appointments with priority score above threshold."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            a.id,
            a.patient_id,
            p.name,
            a.appointment_date,
            a.treatment_type,
            a.payment_type,
            a.patient_priority_score,
            a.insurance_score,
            a.treatment_score,
            a.tenure_score,
            a.frequency_score
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.patient_priority_score >= ?
        ORDER BY a.patient_priority_score DESC
        LIMIT ?
    """, (min_score, limit))
    
    print("\n" + "="*120)
    print(f"APPOINTMENTS WITH PRIORITY SCORE >= {min_score}")
    print("="*120)
    print(f"{'Appt':<8} {'Patient':<8} {'Name':<20} {'Date':<12} {'Treatment':<18} {'Score':<8} {'Breakdown (I/T/Ten/F)'}")
    print("-"*120)
    
    for row in cursor.fetchall():
        appt_id, patient_id, name, date, treatment, payment, score, ins, treat, ten, freq = row
        name_safe = (name[:18] if name else "").ljust(20)
        date_str = date[:10] if date else ""
        treatment_safe = (treatment if treatment else "")[:17].ljust(18)
        breakdown = f"{ins:.0f}/{treat:.0f}/{ten:.0f}/{freq:.0f}"
        
        try:
            print(f"{appt_id:<8} {patient_id:<8} {name_safe} {date_str:<12} {treatment_safe} {score:>6.1f}  {breakdown}")
        except UnicodeEncodeError:
            name_ascii = name_safe.encode('ascii', 'ignore').decode('ascii').ljust(20)
            print(f"{appt_id:<8} {patient_id:<8} {name_ascii} {date_str:<12} {treatment_safe} {score:>6.1f}  {breakdown}")
    
    print("="*120 + "\n")


def query_by_treatment(conn, treatment_type: str, limit: int = 30):
    """Query top appointments for a specific treatment type."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            a.id,
            a.patient_id,
            p.name,
            a.appointment_date,
            a.payment_type,
            a.patient_priority_score,
            a.insurance_score,
            a.treatment_score
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE LOWER(a.treatment_type) = LOWER(?)
        ORDER BY a.patient_priority_score DESC
        LIMIT ?
    """, (treatment_type, limit))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"\nNo appointments found for treatment type: {treatment_type}\n")
        return
    
    print("\n" + "="*100)
    print(f"TOP {limit} APPOINTMENTS - Treatment: {treatment_type.upper()}")
    print("="*100)
    print(f"{'Appt':<8} {'Patient':<8} {'Name':<25} {'Date':<12} {'Payment':<18} {'Score':<8}")
    print("-"*100)
    
    for row in results:
        appt_id, patient_id, name, date, payment, score, ins_score, treat_score = row
        name_safe = (name[:23] if name else "").ljust(25)
        date_str = date[:10] if date else ""
        payment_safe = (payment if payment else "")[:17].ljust(18)
        
        try:
            print(f"{appt_id:<8} {patient_id:<8} {name_safe} {date_str:<12} {payment_safe} {score:>6.1f}")
        except UnicodeEncodeError:
            name_ascii = name_safe.encode('ascii', 'ignore').decode('ascii').ljust(25)
            print(f"{appt_id:<8} {patient_id:<8} {name_ascii} {date_str:<12} {payment_safe} {score:>6.1f}")
    
    # Show statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as count,
            AVG(patient_priority_score) as avg_score,
            MIN(patient_priority_score) as min_score,
            MAX(patient_priority_score) as max_score
        FROM appointments
        WHERE LOWER(treatment_type) = LOWER(?)
    """, (treatment_type,))
    
    count, avg, min_s, max_s = cursor.fetchone()
    print("-"*100)
    print(f"Statistics: {count} total appointments | Avg: {avg:.1f} | Range: {min_s:.1f} - {max_s:.1f}")
    print("="*100 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Query high-value patients and appointments based on priority scores"
    )
    
    parser.add_argument(
        "--top",
        type=int,
        help="Show top N patients by lifetime value (default: 10)"
    )
    
    parser.add_argument(
        "--min-score",
        type=float,
        help="Show appointments with priority score >= threshold"
    )
    
    parser.add_argument(
        "--treatment",
        type=str,
        help="Show top appointments for specific treatment type (e.g., endo, restoration)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Limit number of results (default: 30)"
    )
    
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return 1
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # If no arguments, show default report
        if not any([args.top, args.min_score, args.treatment]):
            query_top_patients(conn, limit=10)
            query_appointments_by_score(conn, min_score=80.0, limit=20)
        else:
            if args.top:
                query_top_patients(conn, limit=args.top)
            
            if args.min_score:
                query_appointments_by_score(conn, min_score=args.min_score, limit=args.limit)
            
            if args.treatment:
                query_by_treatment(conn, treatment_type=args.treatment, limit=args.limit)
        
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())
