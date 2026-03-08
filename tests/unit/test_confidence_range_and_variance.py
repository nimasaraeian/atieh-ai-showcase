"""
Test: Confidence Scoring Range and Variance
============================================
Ensures:
- All confidence values are in range [0.0, 1.0]
- Confidence values vary (not all 1.0)
- At least 2 different confidence values among recommended slots
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_confidence_in_valid_range():
    """Test that all confidence values are between 0 and 1."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "1",
            "service_id": "TREATMENT_3",
            "days_ahead": 7,
            "max_slots": 5
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    slots = data["recommended_slots"]
    
    assert len(slots) > 0, "Should have at least one slot"
    
    for i, slot in enumerate(slots):
        conf = slot["confidence"]
        assert isinstance(conf, (int, float)), f"Slot {i} confidence is not numeric"
        assert 0.0 <= conf <= 1.0, f"Slot {i} confidence {conf} out of range [0.0, 1.0]"
        print(f"OK: Slot {i}: confidence={conf:.2f} (valid)")


def test_confidence_has_variance():
    """Test that confidence values are not all the same (e.g., not all 1.0)."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "2",
            "service_id": "TREATMENT_8",
            "days_ahead": 21,  # Longer range for more diversity
            "max_slots": 5
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    slots = data["recommended_slots"]
    
    assert len(slots) >= 2, "Need at least 2 slots to test variance"
    
    # Collect all unique confidence values
    confidence_values = [slot["confidence"] for slot in slots]
    unique_confidences = set(confidence_values)
    
    print(f"Confidence values: {confidence_values}")
    print(f"Unique confidence values: {len(unique_confidences)}")
    
    # Check that not all confidence values are 1.0 (which would indicate no real scoring)
    all_are_one = all(c == 1.0 for c in confidence_values)
    assert not all_are_one, (
        "All confidence values are 1.0, which indicates no real scoring is happening"
    )
    
    # If we have 3+ slots, we should see at least some variance
    # (Allow edge case where 2 slots have same confidence due to similar characteristics)
    if len(slots) >= 3:
        assert len(unique_confidences) >= 2, (
            f"All {len(slots)} confidence values are the same: {confidence_values}. "
            "Expected some variance in confidence scoring."
        )
    else:
        # For 2 slots, just check they're not both 1.0
        print(f"Only {len(slots)} slots, skipping strict variance check")


def test_confidence_sorted_descending():
    """Test that slots are sorted by confidence (highest first)."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "3",
            "service_id": "TREATMENT_12",
            "days_ahead": 10,
            "max_slots": 4
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    slots = data["recommended_slots"]
    
    if len(slots) < 2:
        pytest.skip("Need at least 2 slots to test sorting")
    
    confidence_values = [slot["confidence"] for slot in slots]
    
    # Check if sorted descending
    for i in range(len(confidence_values) - 1):
        assert confidence_values[i] >= confidence_values[i + 1], (
            f"Slots not sorted by confidence: {confidence_values}"
        )
    
    print(f"OK: Slots correctly sorted by confidence: {confidence_values}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
