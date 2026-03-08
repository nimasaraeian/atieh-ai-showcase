"""Explore the MockCRMClient data for testing and debugging."""
import sys
import os

# Set UTF-8 encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.integrations.crm.mock import MockCRMClient

print("="*80)
print("MockCRMClient Data Explorer")
print("="*80)

# Initialize client
client = MockCRMClient()

# List all patients
print("\n[PATIENTS]")
print("-" * 80)
print(f"Available patient IDs: {list(client.patients.keys())}")
print(f"Total patients: {len(client.patients)}")

print("\nPatient Details:")
for patient_id, data in client.patients.items():
    print(f"\n  Patient {patient_id}:")
    print(f"    Name: {data['full_name']}")
    print(f"    Phone: {data['phone']}")
    print(f"    Insurance: {client.insurances.get(patient_id, 'None')}")
    print(f"    Payment behavior: {client.payment_behaviors.get(patient_id, 'unknown')}")
    
    # Unfinished treatments
    unfinished = client.unfinished_treatments.get(patient_id, [])
    if unfinished:
        print(f"    Unfinished treatments: {len(unfinished)}")
        for treatment in unfinished:
            print(f"      - {treatment['title']} (urgency: {treatment['urgency']})")
    else:
        print(f"    Unfinished treatments: None")
    
    # Preferences
    prefs = client.preferences.get(patient_id, {})
    if prefs.get('preferred_doctor'):
        print(f"    Preferred doctor: {prefs['preferred_doctor']}")
    if prefs.get('preferred_weekdays'):
        print(f"    Preferred days: {', '.join(prefs['preferred_weekdays'])}")

# Test methods
print("\n" + "="*80)
print("[METHOD TESTING]")
print("="*80)

print("\nTesting get_patient('123'):")
patient = client.get_patient('123')
print(f"  Name: {patient['full_name']}")
print(f"  Phone: {patient['phone']}")

print("\nTesting get_patient_insurance('123'):")
insurance = client.get_patient_insurance('123')
print(f"  Insurance: {insurance}")

print("\nTesting get_patient_unfinished('456'):")
unfinished = client.get_patient_unfinished('456')
print(f"  Count: {len(unfinished)}")
for t in unfinished:
    print(f"  - {t['title']}")

print("\nTesting get_patient_preferences('456'):")
prefs = client.get_patient_preferences('456')
print(f"  Preferred doctor: {prefs.get('preferred_doctor')}")
print(f"  Preferred days: {prefs.get('preferred_weekdays')}")

print("\n" + "="*80)
print("Quick Access Examples:")
print("="*80)
print("\nUsing properties (easier):")
print("  client.patients         # All patient data")
print("  client.insurances       # Insurance mappings")
print("  client.unfinished_treatments  # Unfinished treatments")
print("  client.preferences      # Patient preferences")
print("  client.payment_behaviors  # Payment behavior tags")

print("\nUsing methods (CRM interface):")
print("  client.get_patient('123')")
print("  client.get_patient_insurance('123')")
print("  client.get_patient_unfinished('456')")
print("  client.get_patient_preferences('456')")
print("  client.get_payment_behavior('123')")
print("="*80)
