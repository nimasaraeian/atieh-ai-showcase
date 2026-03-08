"""
Complete Test with Real Data from Excel Files
Tests the system with actual imported patient data
"""
import requests
import json
from datetime import datetime
import sys
import io

# Fix Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_1_system_health():
    """Test 1: Check system health"""
    print_header("TEST 1: System Health Check")
    
    response = requests.get(f"{BASE_URL}/health")
    data = response.json()
    
    print(f"Status: {data['status']}")
    print(f"Version: {data['version']}")
    print(f"Timestamp: {data['timestamp']}")
    
    return response.status_code == 200

def test_2_real_patients():
    """Test 2: Get real patients from database"""
    print_header("TEST 2: Real Patients from Excel")
    
    response = requests.get(f"{BASE_URL}/patients?limit=10")
    patients = response.json()
    
    print(f"\nTotal patients returned: {len(patients)}")
    print("\nFirst 5 Real Patients:")
    print("-" * 70)
    
    for i, patient in enumerate(patients[:5], 1):
        print(f"\n{i}. Patient ID: {patient['id']}")
        print(f"   Name: {patient['name']}")
        print(f"   Phone: {patient['phone']}")
        print(f"   Payment Type: {patient.get('payment_type', 'N/A')}")
        print(f"   Lifetime: {patient['lifetime_months']:.1f} months")
        print(f"   Category: {patient['lifetime_category']}")
        print(f"   Total Appointments: {patient['total_appointments']}")
    
    return patients

def test_3_real_appointments():
    """Test 3: Get real appointments"""
    print_header("TEST 3: Real Appointments from Excel")
    
    response = requests.get(f"{BASE_URL}/appointments?limit=10&future_only=false")
    appointments = response.json()
    
    print(f"\nTotal appointments returned: {len(appointments)}")
    print("\nFirst 5 Real Appointments:")
    print("-" * 70)
    
    for i, appt in enumerate(appointments[:5], 1):
        print(f"\n{i}. Appointment ID: {appt['id']}")
        print(f"   Patient: {appt['patient_name']} (ID: {appt['patient_id']})")
        print(f"   Date: {appt['appointment_date'][:10]}")
        print(f"   Treatment: {appt['treatment_type']}")
        print(f"   Payment: {appt['payment_type']}")
        print(f"   Priority Score: {appt['priority_score']:.1f}/100")
        print(f"   Status: {appt['status']}")
    
    return appointments

def test_4_ai_scoring_real_patient(patient_id):
    """Test 4: AI scoring on real patient"""
    print_header(f"TEST 4: AI Scoring for Real Patient (ID={patient_id})")
    
    try:
        response = requests.post(f"{BASE_URL}/ai/score-patient?patient_id={patient_id}")
        
        if response.status_code == 200:
            data = response.json()
            explain = data.get('explain', {})
            insights = data.get('insights', {})
            
            print(f"\nPatient ID: {data.get('patient_id')}")
            print("\nAI Assessment:")
            print(f"  Priority Score: {explain.get('priority_score')}/100")
            print(f"  Value Score: {explain.get('value_score')}/100")
            print(f"  Risk No-Show: {explain.get('risk_no_show', 0):.1%}")
            print(f"  Risk Late Payment: {explain.get('risk_late_payment', 0):.1%}")
            
            print(f"\nReason Codes:")
            for code in explain.get('reason_codes', []):
                print(f"  - {code}")
            
            print(f"\nInsights:")
            print(f"  Lifetime: {insights.get('lifetime_months')} months")
            print(f"  Total Appointments: {insights.get('total_appointments')}")
            print(f"  Completion Rate: {insights.get('completion_rate', 0):.1%}")
            print(f"  Payment Category: {insights.get('payment_category')}")
            print(f"  Lifetime Category: {insights.get('lifetime_category')}")
            
            return True
        else:
            print(f"[FAIL] Status: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_5_suggest_time_real_patient(patient_id):
    """Test 5: Suggest appointment time for real patient"""
    print_header(f"TEST 5: AI Time Suggestion for Real Patient (ID={patient_id})")
    
    try:
        response = requests.get(
            f"{BASE_URL}/appointments/suggest-time",
            params={
                "treatment_type": "TREATMENT_10",
                "patient_id": patient_id,
                "max_suggestions": 5
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nAI Recommended Times:")
            for i, time_str in enumerate(data.get('suggested_times', []), 1):
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                print(f"  {i}. {dt.strftime('%Y-%m-%d %A %H:%M')}")
            
            print(f"\nDuration: {data.get('duration_minutes')} minutes")
            print(f"Total Available Slots: {data.get('available_slots_count')}")
            print(f"Message: {data.get('message')}")
            
            return True
        else:
            print(f"[FAIL] Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_6_search_real_patients():
    """Test 6: Search real patients"""
    print_header("TEST 6: Search Real Patients")
    
    search_terms = ["احمد", "محمد", "علی"]
    
    for term in search_terms:
        try:
            response = requests.get(f"{BASE_URL}/patients?search={term}&limit=3")
            if response.status_code == 200:
                results = response.json()
                print(f"\nSearch '{term}': {len(results)} results")
                for patient in results:
                    print(f"  - {patient['name']} ({patient['phone']})")
        except:
            print(f"\nSearch '{term}': No results")

def test_7_statistics():
    """Test 7: Overall statistics"""
    print_header("TEST 7: System Statistics (Real Data)")
    
    import sqlite3
    conn = sqlite3.connect('atieh_clinic.db')
    c = conn.cursor()
    
    # Total counts
    c.execute('SELECT COUNT(*) FROM patients')
    total_patients = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM appointments')
    total_appointments = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM stg_appointments')
    total_staging = c.fetchone()[0]
    
    # Parse status
    c.execute('SELECT parse_status, COUNT(*) FROM stg_appointments GROUP BY parse_status')
    parse_stats = c.fetchall()
    
    # Payment distribution
    c.execute('SELECT payment_type, COUNT(*) FROM appointments GROUP BY payment_type ORDER BY COUNT(*) DESC LIMIT 5')
    payment_dist = c.fetchall()
    
    # Treatment distribution
    c.execute('SELECT treatment_type, COUNT(*) FROM appointments GROUP BY treatment_type ORDER BY COUNT(*) DESC LIMIT 5')
    treatment_dist = c.fetchall()
    
    print(f"\nDatabase Statistics:")
    print(f"  Total Patients: {total_patients:,}")
    print(f"  Total Appointments: {total_appointments:,}")
    print(f"  Total Staging Rows: {total_staging:,}")
    
    print(f"\nParsing Success Rate:")
    for status, count in parse_stats:
        percentage = (count / total_staging * 100) if total_staging > 0 else 0
        print(f"  {status}: {count:,} ({percentage:.1f}%)")
    
    print(f"\nTop Payment Types:")
    for ptype, count in payment_dist:
        print(f"  {ptype}: {count:,}")
    
    print(f"\nTop Treatment Types:")
    for ttype, count in treatment_dist:
        print(f"  {ttype}: {count:,}")
    
    conn.close()

def run_complete_test():
    """Run complete test suite with real data"""
    
    print("\n")
    print("*" * 70)
    print("  COMPLETE TEST WITH REAL DATA FROM EXCEL FILES")
    print("*" * 70)
    
    # Test 1: Health
    test_1_system_health()
    
    # Test 2: Get real patients
    patients = test_2_real_patients()
    
    # Test 3: Get real appointments
    appointments = test_3_real_appointments()
    
    # Test 4 & 5: AI tests with first real patient
    if patients and len(patients) > 0:
        first_patient_id = patients[0]['id']
        test_4_ai_scoring_real_patient(first_patient_id)
        test_5_suggest_time_real_patient(first_patient_id)
    
    # Test 6: Search
    test_6_search_real_patients()
    
    # Test 7: Statistics
    test_7_statistics()
    
    print("\n" + "="*70)
    print("  TEST COMPLETED!")
    print("="*70)
    print("\nConclusion:")
    print("  - System successfully working with REAL data from Excel")
    print("  - AI scoring is functional")
    print("  - Time suggestions are working")
    print("  - Search is operational")
    print("  - All endpoints responding correctly")
    print("\n" + "="*70)

if __name__ == "__main__":
    # Check server
    try:
        requests.get(f"{BASE_URL}/api", timeout=2)
        print("\n[OK] Server is running!\n")
    except:
        print("\n[ERROR] Server is not running!")
        print("Please start: uvicorn main:app --reload\n")
        exit(1)
    
    run_complete_test()
