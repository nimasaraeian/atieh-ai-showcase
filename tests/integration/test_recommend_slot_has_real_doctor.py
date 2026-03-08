"""
Test: Slot Recommendations Include Real Doctor Information
===========================================================
Ensures all recommended slots have:
- doctor_id != "AUTO"
- doctor_name not null
- doctor_name is a string
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_recommend_slot_has_real_doctor():
    """Test that slots have real doctor assignments (not AUTO)."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "1",
            "service_id": "TREATMENT_5",
            "days_ahead": 7,
            "max_slots": 3
        }
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Check we have slots
    assert "recommended_slots" in data
    slots = data["recommended_slots"]
    assert len(slots) > 0, "Should have at least one slot"
    
    # Check each slot has real doctor info
    for i, slot in enumerate(slots):
        assert "doctor_id" in slot, f"Slot {i} missing doctor_id"
        assert "doctor_name" in slot, f"Slot {i} missing doctor_name"
        
        # doctor_id should NOT be "AUTO"
        assert slot["doctor_id"] != "AUTO", f"Slot {i} has doctor_id='AUTO', expected real doctor ID"
        
        # doctor_name should not be null/None
        assert slot["doctor_name"] is not None, f"Slot {i} has doctor_name=null"
        assert isinstance(slot["doctor_name"], str), f"Slot {i} doctor_name is not a string"
        assert len(slot["doctor_name"]) > 0, f"Slot {i} doctor_name is empty string"
        
        print(f"OK: Slot {i}: doctor_id={slot['doctor_id']}, doctor_name={slot['doctor_name']}")


def test_recommend_slot_multiple_doctors():
    """Test that recommendations can include multiple different doctors."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "2",
            "service_id": "TREATMENT_10",
            "days_ahead": 14,
            "max_slots": 5
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    slots = data["recommended_slots"]
    
    # Collect unique doctor IDs
    doctor_ids = set(slot["doctor_id"] for slot in slots)
    
    # We expect diversity (if available in mock data)
    print(f"Found {len(doctor_ids)} unique doctors across {len(slots)} slots")
    
    # At minimum, all doctor IDs should be non-AUTO
    for doctor_id in doctor_ids:
        assert doctor_id != "AUTO", "Found AUTO doctor_id in recommendations"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
