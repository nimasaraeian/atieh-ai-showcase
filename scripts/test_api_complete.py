"""
Complete API Test Suite
Tests all major endpoints of the appointment system
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_health():
    """Test 1: Health check"""
    print_section("TEST 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_get_patients():
    """Test 2: Get patients list"""
    print_section("TEST 2: Get Patients (first 5)")
    try:
        response = requests.get(f"{BASE_URL}/patients?limit=5")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total patients returned: {len(data)}")
        if data:
            print("\nFirst patient:")
            print(json.dumps(data[0], indent=2, ensure_ascii=False, default=str))
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_get_patient_detail(patient_id=1):
    """Test 3: Get patient detail"""
    print_section(f"TEST 3: Get Patient Detail (ID={patient_id})")
    try:
        response = requests.get(f"{BASE_URL}/patients/{patient_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False, default=str))
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_get_appointments():
    """Test 4: Get appointments"""
    print_section("TEST 4: Get Appointments (first 5)")
    try:
        response = requests.get(f"{BASE_URL}/appointments?limit=5&future_only=false")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total appointments returned: {len(data)}")
        if data:
            print("\nFirst appointment:")
            print(json.dumps(data[0], indent=2, ensure_ascii=False, default=str))
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_payment_types():
    """Test 5: Get payment types"""
    print_section("TEST 5: Get Payment Types")
    try:
        response = requests.get(f"{BASE_URL}/payment-types")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Cash: {data.get('cash')}")
        print(f"Insurance types: {len(data.get('insurance_types', []))} types")
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_treatment_types():
    """Test 6: Get treatment types"""
    print_section("TEST 6: Get Treatment Types")
    try:
        response = requests.get(f"{BASE_URL}/treatment-types")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Treatment types: {len(data.get('treatment_types', []))} types")
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_ai_score_patient(patient_id=1):
    """Test 7: AI score patient"""
    print_section(f"TEST 7: AI Score Patient (ID={patient_id})")
    try:
        response = requests.post(f"{BASE_URL}/ai/score-patient?patient_id={patient_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"\nPatient ID: {data.get('patient_id')}")
            explain = data.get('explain', {})
            print(f"Priority Score: {explain.get('priority_score')}")
            print(f"Value Score: {explain.get('value_score')}")
            print(f"Risk No-Show: {explain.get('risk_no_show'):.2%}")
            print(f"Risk Late Payment: {explain.get('risk_late_payment'):.2%}")
            print(f"Reason Codes: {explain.get('reason_codes')}")
            print(f"\nInsights: {json.dumps(data.get('insights'), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_suggest_time(patient_id=1):
    """Test 8: Suggest appointment time"""
    print_section(f"TEST 8: Suggest Appointment Time (Patient={patient_id})")
    try:
        response = requests.get(
            f"{BASE_URL}/appointments/suggest-time",
            params={
                "treatment_type": "TREATMENT_10",
                "patient_id": patient_id,
                "max_suggestions": 3
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"\nSuggested times ({len(data.get('suggested_times', []))}):")
            for i, time in enumerate(data.get('suggested_times', []), 1):
                print(f"  {i}. {time}")
            print(f"\nDuration: {data.get('duration_minutes')} minutes")
            print(f"Available slots: {data.get('available_slots_count')}")
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_search_patient(search_term="Ali"):
    """Test 9: Search patients"""
    print_section(f"TEST 9: Search Patients ('{search_term}')")
    try:
        response = requests.get(f"{BASE_URL}/patients?search={search_term}&limit=3")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Results found: {len(data)}")
        for patient in data[:3]:
            print(f"  - {patient.get('name')} ({patient.get('phone')})")
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_import_status():
    """Test 10: Check import status"""
    print_section("TEST 10: Check Import Status")
    try:
        response = requests.get(f"{BASE_URL}/import/history?limit=3")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total import runs: {data.get('total', 0)}")
            if data.get('imports'):
                print(f"\nLatest import:")
                latest = data['imports'][0]
                print(f"  ID: {latest.get('id')}")
                print(f"  Filename: {latest.get('filename')}")
                print(f"  Status: {latest.get('status')}")
                print(f"  Rows: {latest.get('rows_imported')}/{latest.get('total_rows')}")
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("\n")
    print("*" * 70)
    print("  API TESTING SUITE - Atieh Clinic System")
    print("*" * 70)
    
    tests = [
        ("Health Check", test_health),
        ("Get Patients List", test_get_patients),
        ("Get Patient Detail", lambda: test_get_patient_detail(1)),
        ("Get Appointments", test_get_appointments),
        ("Get Payment Types", test_payment_types),
        ("Get Treatment Types", test_treatment_types),
        ("AI Score Patient", lambda: test_ai_score_patient(1)),
        ("Suggest Time", lambda: test_suggest_time(1)),
        ("Search Patients", lambda: test_search_patient("Ali")),
        ("Import Status", test_import_status),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n[ERROR] Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print_section("TEST RESULTS SUMMARY")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
    
    print("\n" + "="*70)
    print(f"Total: {passed_count}/{total_count} tests passed")
    print(f"Success Rate: {passed_count/total_count*100:.1f}%")
    print("="*70)
    
    if passed_count == total_count:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[WARNING] {total_count - passed_count} test(s) failed")
    
    return passed_count == total_count

if __name__ == "__main__":
    # Check if server is running
    print("\nChecking if server is running...")
    try:
        requests.get(f"{BASE_URL}/api", timeout=2)
        print("[OK] Server is running!\n")
    except:
        print(f"\n[ERROR] Server is not running!")
        print(f"Please start the server first:")
        print(f"  uvicorn main:app --reload\n")
        exit(1)
    
    success = run_all_tests()
    exit(0 if success else 1)
