# -*- coding: utf-8 -*-
import sys
import io
import requests
import json

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    response = requests.get('http://localhost:8000/patients?limit=5')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        patients = response.json()
        print(f"Number of patients returned: {len(patients)}")
        if len(patients) > 0:
            print("\nFirst patient:")
            print(json.dumps(patients[0], ensure_ascii=False, indent=2))
        else:
            print("No patients returned!")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")





