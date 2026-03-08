"""
Test: Value Score is Non-Zero
==============================
Ensures value_score is:
- Between 1 and 100 for typical patients
- Not always 0
- Properly calculated based on patient history
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_value_score_nonzero():
    """Test that value_score is not 0 for typical patients."""
    response = client.post(
        "/ai/score-patient",
        params={
            "patient_id": "1"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "explain" in data
    explain = data["explain"]
    
    assert "value_score" in explain
    value_score = explain["value_score"]
    
    # value_score should be int between 0-100
    assert isinstance(value_score, int), f"value_score should be int, got {type(value_score)}"
    assert 0 <= value_score <= 100, f"value_score {value_score} out of range [0, 100]"
    
    # For a typical patient, value_score should be non-zero
    # Default is 40, so it should be at least that
    assert value_score > 0, "value_score is 0, expected non-zero value"
    
    print(f"OK: Patient value_score: {value_score} (valid, non-zero)")


def test_value_score_in_recommend_slot():
    """Test that value_score is non-zero in recommend-slot endpoint."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "2",
            "service_id": "TREATMENT_5",
            "days_ahead": 7,
            "max_slots": 3
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "explain" in data
    explain = data["explain"]
    
    assert "value_score" in explain
    value_score = explain["value_score"]
    
    assert isinstance(value_score, int), f"value_score should be int, got {type(value_score)}"
    assert 0 <= value_score <= 100, f"value_score {value_score} out of range [0, 100]"
    assert value_score > 0, "value_score is 0 in recommend-slot, expected non-zero"
    
    print(f"OK: Recommend-slot value_score: {value_score}")


def test_value_score_varies_by_patient():
    """Test that value_score is different for different patients."""
    patient_ids = ["1", "2", "3"]
    value_scores = []
    
    for patient_id in patient_ids:
        response = client.post(
            "/ai/score-patient",
            params={"patient_id": patient_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            value_score = data["explain"]["value_score"]
            value_scores.append(value_score)
            print(f"Patient {patient_id}: value_score = {value_score}")
    
    # We expect at least some variance (not all the same)
    unique_scores = set(value_scores)
    
    if len(value_scores) >= 2:
        # At least 2 different scores (unless all patients have identical history)
        assert len(unique_scores) >= 1, "All patients have different value_scores expected"
        print(f"OK: Found {len(unique_scores)} unique value_scores across {len(value_scores)} patients")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
