"""
Test: Persian Text Encoding is Correct
=======================================
Ensures:
- payment_category contains Persian characters (not mojibake like "Ø")
- lifetime_category contains Persian characters
- doctor_name contains Persian characters
- No encoding artifacts in JSON responses
"""
import pytest
from fastapi.testclient import TestClient
from main import app
import re

client = TestClient(app)


def test_persian_encoding_in_score_patient():
    """Test that payment_category and lifetime_category have valid Persian text."""
    response = client.post(
        "/ai/score-patient",
        params={"patient_id": "1"}
    )
    
    assert response.status_code == 200
    
    # Check raw response text for encoding artifacts
    response_text = response.text
    
    # Look for mojibake patterns (like "Ø", "Û", etc.)
    mojibake_pattern = r'[ÃƒÂØÙÛÝÞ]{3,}'
    
    assert not re.search(mojibake_pattern, response_text), (
        f"Found mojibake in response: {response_text[:500]}"
    )
    
    data = response.json()
    
    # Check insights for Persian text
    if "insights" in data:
        insights = data["insights"]
        
        if "payment_category" in insights and insights["payment_category"]:
            payment_cat = insights["payment_category"]
            assert isinstance(payment_cat, str)
            # Check for Persian Unicode range (0x0600-0x06FF)
            has_persian = any('\u0600' <= c <= '\u06FF' for c in payment_cat)
            assert has_persian, f"payment_category '{payment_cat}' does not contain Persian characters"
            print(f"OK: payment_category: {payment_cat} (valid Persian)")
        
        if "lifetime_category" in insights and insights["lifetime_category"]:
            lifetime_cat = insights["lifetime_category"]
            assert isinstance(lifetime_cat, str)
            has_persian = any('\u0600' <= c <= '\u06FF' for c in lifetime_cat)
            assert has_persian, f"lifetime_category '{lifetime_cat}' does not contain Persian characters"
            print(f"OK: lifetime_category: {lifetime_cat} (valid Persian)")


def test_persian_encoding_in_recommend_slot():
    """Test that doctor names in slot recommendations have valid Persian text."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "1",
            "service_id": "TREATMENT_5",
            "days_ahead": 7,
            "max_slots": 3
        }
    )
    
    assert response.status_code == 200
    
    # Check raw response for mojibake
    response_text = response.text
    mojibake_pattern = r'[ÃƒÂØÙÛÝÞ]{3,}'
    
    assert not re.search(mojibake_pattern, response_text), (
        f"Found mojibake in recommend-slot response"
    )
    
    data = response.json()
    
    # Check doctor names
    if "recommended_slots" in data:
        slots = data["recommended_slots"]
        
        for i, slot in enumerate(slots):
            if "doctor_name" in slot and slot["doctor_name"]:
                doctor_name = slot["doctor_name"]
                assert isinstance(doctor_name, str)
                
                # Check for Persian characters
                has_persian = any('\u0600' <= c <= '\u06FF' for c in doctor_name)
                assert has_persian, f"Slot {i} doctor_name '{doctor_name}' does not contain Persian characters"
                print(f"OK: Slot {i} doctor_name: {doctor_name} (valid Persian)")


def test_recommend_slot_doctor_name_from_reference():
    """
    Assert recommend-slot returns Persian doctor_name for every slot.
    doctor_name must NOT contain 'Dr. ' (placeholders); must be Persian or 'دکتر نامشخص'.
    """
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "1",
            "service_id": "TREATMENT_5",
            "days_ahead": 7,
            "max_slots": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    slots = data.get("recommended_slots", [])

    for i, slot in enumerate(slots):
        doctor_name = slot.get("doctor_name") or ""
        assert "Dr. " not in doctor_name, (
            f"Slot {i} doctor_name must not contain 'Dr. ' – got '{doctor_name}'"
        )
        has_persian = any("\u0600" <= c <= "\u06FF" for c in doctor_name)
        assert has_persian or doctor_name == "دکتر نامشخص", (
            f"Slot {i} doctor_name must be Persian or 'دکتر نامشخص' – got '{doctor_name}'"
        )


def test_utf8_content_type():
    """Test that API responses specify UTF-8 encoding."""
    response = client.post(
        "/ai/score-patient",
        params={"patient_id": "1"}
    )
    
    assert response.status_code == 200
    
    # Check Content-Type header
    content_type = response.headers.get("content-type", "")
    print(f"Content-Type: {content_type}")
    
    # Should include charset=utf-8 or be application/json (which defaults to UTF-8)
    assert "application/json" in content_type.lower(), (
        f"Expected application/json, got {content_type}"
    )


def test_no_double_encoding():
    """Test that Persian text is not double-encoded."""
    response = client.post(
        "/ai/score-patient",
        params={"patient_id": "1"}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Get all string values from response
    def extract_strings(obj, depth=0):
        """Recursively extract all strings from JSON object."""
        if depth > 10:
            return []
        
        strings = []
        if isinstance(obj, dict):
            for value in obj.values():
                strings.extend(extract_strings(value, depth + 1))
        elif isinstance(obj, list):
            for item in obj:
                strings.extend(extract_strings(item, depth + 1))
        elif isinstance(obj, str):
            strings.append(obj)
        
        return strings
    
    all_strings = extract_strings(data)
    
    # Check for double-encoding patterns
    for s in all_strings:
        # No escape sequences like \u0639 in the actual string
        assert '\\u' not in s, f"Found escape sequence in string: {s}"
        
        # No HTML entities
        assert '&#' not in s, f"Found HTML entity in string: {s}"
        
        # No URL encoding
        assert '%D8' not in s and '%D9' not in s, f"Found URL encoding in string: {s}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
