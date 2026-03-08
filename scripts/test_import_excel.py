"""
Test Excel History Import via API
"""
import requests
import json
import os
import sys
import io

# Fix Unicode output for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def test_import_history():
    """Test importing Excel history files"""
    
    print("="*70)
    print("  TEST: Import Excel History Files")
    print("="*70)
    
    # Check what Excel files exist
    print("\n1. Checking for Excel files...")
    
    possible_paths = [
        "data/inputs/history/1404",
        "data/history",
        "uploads",
        "data"
    ]
    
    excel_files = []
    for path in possible_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith(('.xlsx', '.xls')):
                    full_path = os.path.join(path, file)
                    excel_files.append(full_path)
                    print(f"   Found: {full_path}")
    
    if not excel_files:
        print("\n[WARNING] No Excel files found!")
        print("Please place your Excel files in one of these folders:")
        for path in possible_paths:
            print(f"  - {path}")
        return False
    
    # Prepare import request
    print(f"\n2. Preparing to import {len(excel_files)} file(s)...")
    
    files_to_import = []
    for excel_file in excel_files[:1]:  # Import only first file for test
        files_to_import.append({
            "path": excel_file,
            "year": 1404,  # Default Jalali year
            "sheet": 0
        })
    
    request_data = {
        "files": files_to_import
    }
    
    print(f"\nRequest payload:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    # Send import request
    print("\n3. Sending import request...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/import/history",
            json=request_data,
            timeout=300  # 5 minutes timeout
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n[SUCCESS] Import completed!")
            print(f"\nImport Run ID: {result.get('import_run_id')}")
            print(f"Status: {result.get('status')}")
            
            stats = result.get('stats', {})
            if stats:
                print(f"\nStatistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            
            return True
        else:
            print(f"\n[FAIL] Import failed!")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n[TIMEOUT] Import is taking too long (>5 min)")
        print("This might be normal for large files.")
        print("Check import status via API: /api/import/history")
        return False
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False

def check_import_api():
    """Check if import API is available"""
    print("\n" + "="*70)
    print("  Checking Import API Availability")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/api/import/ping")
        if response.status_code == 200:
            print("\n[OK] Import API is available!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"\n[FAIL] Import API returned {response.status_code}")
            return False
    except Exception as e:
        print(f"\n[ERROR] Cannot connect to Import API: {e}")
        return False

def show_usage_guide():
    """Show usage guide for import"""
    print("\n" + "="*70)
    print("  HOW TO IMPORT EXCEL FILES")
    print("="*70)
    
    print("""
METHOD 1: Via API (this script)
---------------------------------
1. Place Excel file in one of these folders:
   - data/inputs/history/1404/
   - data/history/
   - data/

2. Run this script:
   python scripts/test_import_excel.py


METHOD 2: Via API with Postman/curl
---------------------------------
POST http://localhost:8000/api/import/history

Body (JSON):
{
  "files": [
    {
      "path": "data/history/your_file.xlsx",
      "year": 1404,
      "sheet": 0
    }
  ]
}


METHOD 3: Direct with Python
--------------------------
from app.importers.history_importer import import_history_excel

result = import_history_excel(
    file_path="data/history/your_file.xlsx",
    db=db,
    year_hint=1404,
    import_run_id=1
)


METHOD 4: Check Results
--------------------
http://localhost:8000/api/import/history?limit=10
""")

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
        show_usage_guide()
        exit(1)
    
    # Check import API
    if not check_import_api():
        print("\n[ERROR] Import API is not available!")
        exit(1)
    
    # Show usage guide
    show_usage_guide()
    
    # Test import
    print("\n" + "="*70)
    print("  STARTING IMPORT TEST")
    print("="*70)
    
    success = test_import_history()
    
    if success:
        print("\n" + "="*70)
        print("  [SUCCESS] Import test completed!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("  [INFO] Check the guide above for manual import")
        print("="*70)
