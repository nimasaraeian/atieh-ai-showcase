"""
Tests for AI API Endpoints
===========================
End-to-end tests for /health, /ai/score-patient, /ai/recommend-slot endpoints.

All fixtures are provided by conftest.py:
- client: TestClient with test database
- seed_patients: 3 test patients (IDs 1, 2, 3)
- seeded_db: Full test database with patients and appointments
"""
import pytest
from datetime import datetime


def test_health_endpoint(client):
    """Test /health endpoint returns proper structure."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert "version" in data
    assert "crm_mode" in data
    assert "crm_healthy" in data
    assert "timestamp" in data
    
    # Check values
    assert data["status"] == "ok"
    assert data["crm_mode"] in ["mock", "live"]
    assert isinstance(data["crm_healthy"], bool)


def test_score_patient_endpoint(client, seed_patients):
    """Test /ai/score-patient endpoint returns valid structure."""
    response = client.post("/ai/score-patient?patient_id=1")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check structure matches AIScorePatientResponse
    assert "patient_id" in data
    assert "explain" in data
    assert "insights" in data
    
    explain = data["explain"]
    assert "priority_score" in explain
    assert "value_score" in explain
    assert "risk_no_show" in explain
    assert "risk_late_payment" in explain
    assert "reason_codes" in explain
    
    # Validate ranges
    assert 0 <= explain["priority_score"] <= 100
    assert 0 <= explain["value_score"] <= 100
    assert 0.0 <= explain["risk_no_show"] <= 1.0
    assert 0.0 <= explain["risk_late_payment"] <= 1.0
    
    # Reason codes should be list of strings
    assert isinstance(explain["reason_codes"], list)


def test_score_patient_not_found(client):
    """Test /ai/score-patient with non-existent patient."""
    response = client.post("/ai/score-patient?patient_id=99999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_recommend_slot_endpoint(client, seed_patients):
    """Test /ai/recommend-slot endpoint returns valid structure."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "1",
            "service_id": "TREATMENT_5",
            "days_ahead": 30,
            "max_slots": 5
        }
    )
    
    # Note: might fail if no slots available, but should have proper structure
    if response.status_code == 200:
        data = response.json()
        
        # Check structure matches AIRecommendSlotResponse
        assert "patient_id" in data
        assert "service_id" in data
        assert "urgency_level" in data
        assert "explain" in data
        assert "recommended_slots" in data
        
        # Validate urgency level
        assert data["urgency_level"] in ["low", "medium", "high", "critical"]
        
        # Validate explain
        explain = data["explain"]
        assert 0 <= explain["priority_score"] <= 100
        assert 0 <= explain["value_score"] <= 100
        assert 0.0 <= explain["risk_no_show"] <= 1.0
        assert 0.0 <= explain["risk_late_payment"] <= 1.0
        
        # Validate slots
        slots = data["recommended_slots"]
        assert isinstance(slots, list)
        assert len(slots) <= 5  # max_slots parameter
        
        for slot in slots:
            assert "start_datetime" in slot
            assert "end_datetime" in slot
            assert "doctor_id" in slot
            assert "confidence" in slot
            assert "reason_codes" in slot
            
            # Validate confidence range
            assert 0.0 <= slot["confidence"] <= 1.0
            
            # Validate reason codes
            assert isinstance(slot["reason_codes"], list)
    
    elif response.status_code == 404:
        # No slots available - acceptable
        assert "no available slots" in response.json()["detail"].lower()
    else:
        pytest.fail(f"Unexpected status code: {response.status_code}")


def test_recommend_slot_invalid_service(client, seed_patients):
    """Test /ai/recommend-slot with invalid service ID."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "1",
            "service_id": "INVALID_SERVICE",
            "days_ahead": 30
        }
    )
    
    assert response.status_code == 400
    assert "invalid service_id" in response.json()["detail"].lower()


def test_recommend_slot_missing_patient(client):
    """Test /ai/recommend-slot with non-existent patient."""
    response = client.post(
        "/ai/recommend-slot",
        params={
            "patient_id": "99999",
            "service_id": "TREATMENT_5",
            "days_ahead": 30
        }
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_docs_available(client):
    """Test that API documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema(client):
    """Test that OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    schema = response.json()
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/ai/score-patient" in schema["paths"]
    assert "/ai/recommend-slot" in schema["paths"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
