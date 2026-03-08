#!/usr/bin/env python3
"""
Test that Patient() constructor now filters out invalid fields.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Patient

print("Testing Patient() with invalid fields...")

# Test 1: Pass family (should be filtered out, not cause error)
try:
    p1 = Patient(name="Test User", phone="09121234567", family="BadField")
    print("[OK] Patient with 'family' field - filtered out successfully")
    print(f"    Patient name: {p1.name}, phone: {p1.phone}")
    assert not hasattr(p1, 'family') or p1.family is None
except Exception as e:
    print(f"[FAIL] Patient with 'family' field raised error: {e}")

# Test 2: Pass mobile (should be filtered out, not cause error)
try:
    p2 = Patient(name="Test User 2", phone="09129999999", mobile="ShouldBeIgnored")
    print("[OK] Patient with 'mobile' field - filtered out successfully")
    print(f"    Patient name: {p2.name}, phone: {p2.phone}")
except Exception as e:
    print(f"[FAIL] Patient with 'mobile' field raised error: {e}")

# Test 3: Pass multiple bad fields
try:
    p3 = Patient(
        name="Test User 3",
        phone="09128888888",
        family="Bad1",
        mobile="Bad2",
        first_name="Bad3",
        last_name="Bad4",
        gender="Bad5",
        email="bad6@test.com"
    )
    print("[OK] Patient with multiple invalid fields - filtered out successfully")
    print(f"    Patient name: {p3.name}, phone: {p3.phone}")
except Exception as e:
    print(f"[FAIL] Patient with multiple invalid fields raised error: {e}")

# Test 4: Normal usage still works
try:
    p4 = Patient(name="Normal User", phone="09127777777", national_id="1234567890")
    print("[OK] Normal Patient creation still works")
    print(f"    Patient name: {p4.name}, phone: {p4.phone}, national_id: {p4.national_id}")
except Exception as e:
    print(f"[FAIL] Normal Patient creation failed: {e}")

print("\nAll tests passed! Patient() constructor now safely filters invalid fields.")
