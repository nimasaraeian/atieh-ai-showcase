"""
Tests for AI Scoring Contract
==============================
Validates that scoring outputs conform to the defined contract.
"""
import pytest
from app.schemas.ai_contract import AIExplain, SlotSuggestion, AIRecommendSlotResponse, ReasonCodes
from datetime import datetime, timedelta


def test_ai_explain_score_ranges():
    """Test that scores are within valid ranges (0-100)."""
    # Valid scores
    explain = AIExplain(
        priority_score=75,
        value_score=80,
        risk_no_show=0.15,
        risk_late_payment=0.10,
        reason_codes=["HIGH_VALUE"]
    )
    
    assert 0 <= explain.priority_score <= 100
    assert 0 <= explain.value_score <= 100
    assert 0.0 <= explain.risk_no_show <= 1.0
    assert 0.0 <= explain.risk_late_payment <= 1.0


def test_ai_explain_invalid_scores():
    """Test that invalid scores are rejected."""
    # Priority score > 100
    with pytest.raises(ValueError):
        AIExplain(
            priority_score=101,  # Invalid!
            value_score=80,
            risk_no_show=0.15,
            risk_late_payment=0.10,
            reason_codes=[]
        )
    
    # Negative value score
    with pytest.raises(ValueError):
        AIExplain(
            priority_score=75,
            value_score=-1,  # Invalid!
            risk_no_show=0.15,
            risk_late_payment=0.10,
            reason_codes=[]
        )
    
    # Risk > 1.0
    with pytest.raises(ValueError):
        AIExplain(
            priority_score=75,
            value_score=80,
            risk_no_show=1.5,  # Invalid!
            risk_late_payment=0.10,
            reason_codes=[]
        )


def test_slot_suggestion_confidence_range():
    """Test that slot confidence is within 0-1 range."""
    now = datetime.now()
    
    # Valid confidence
    slot = SlotSuggestion(
        start_datetime=now,
        end_datetime=now + timedelta(minutes=30),
        doctor_id="D001",
        doctor_name="دکتر احمدی",
        confidence=0.85,
        reason_codes=["BEST_MATCH"]
    )
    
    assert 0.0 <= slot.confidence <= 1.0


def test_slot_suggestion_invalid_confidence():
    """Test that invalid confidence values are rejected."""
    now = datetime.now()
    
    # Confidence > 1.0
    with pytest.raises(ValueError):
        SlotSuggestion(
            start_datetime=now,
            end_datetime=now + timedelta(minutes=30),
            doctor_id="D001",
            confidence=1.5,  # Invalid!
            reason_codes=[]
        )
    
    # Negative confidence
    with pytest.raises(ValueError):
        SlotSuggestion(
            start_datetime=now,
            end_datetime=now + timedelta(minutes=30),
            doctor_id="D001",
            confidence=-0.1,  # Invalid!
            reason_codes=[]
        )


def test_reason_codes_normalization():
    """Test that reason codes are normalized to uppercase."""
    now = datetime.now()
    
    slot = SlotSuggestion(
        start_datetime=now,
        end_datetime=now + timedelta(minutes=30),
        doctor_id="D001",
        confidence=0.85,
        reason_codes=["best match", "high priority"]  # lowercase input
    )
    
    # Should be normalized to uppercase with underscores
    assert "BEST_MATCH" in slot.reason_codes
    assert "HIGH_PRIORITY" in slot.reason_codes


def test_recommend_slot_response_structure():
    """Test complete recommendation response structure."""
    now = datetime.now()
    
    explain = AIExplain(
        priority_score=85,
        value_score=90,
        risk_no_show=0.05,
        risk_late_payment=0.03,
        reason_codes=["HIGH_VALUE", "CASH_PAYMENT"]
    )
    
    slot = SlotSuggestion(
        start_datetime=now,
        end_datetime=now + timedelta(minutes=30),
        doctor_id="D001",
        doctor_name="دکتر احمدی",
        confidence=0.92,
        reason_codes=["BEST_MATCH", "MORNING_SLOT"]
    )
    
    response = AIRecommendSlotResponse(
        patient_id="P00123",
        service_id="treatment_5",
        urgency_level="high",
        explain=explain,
        recommended_slots=[slot]
    )
    
    # Validate structure
    assert response.patient_id == "P00123"
    assert response.service_id == "treatment_5"
    assert response.urgency_level == "high"
    assert response.explain.priority_score == 85
    assert len(response.recommended_slots) == 1
    assert response.recommended_slots[0].confidence == 0.92


def test_urgency_level_validation():
    """Test that urgency level is validated."""
    now = datetime.now()
    
    explain = AIExplain(
        priority_score=75,
        value_score=80,
        risk_no_show=0.15,
        risk_late_payment=0.10,
        reason_codes=[]
    )
    
    # Valid urgency levels
    for urgency in ["low", "medium", "high", "critical"]:
        response = AIRecommendSlotResponse(
            patient_id="P00123",
            service_id="treatment_5",
            urgency_level=urgency,
            explain=explain,
            recommended_slots=[]
        )
        assert response.urgency_level == urgency
    
    # Invalid urgency level
    with pytest.raises(ValueError):
        AIRecommendSlotResponse(
            patient_id="P00123",
            service_id="treatment_5",
            urgency_level="invalid",  # Invalid!
            explain=explain,
            recommended_slots=[]
        )


def test_reason_codes_constants():
    """Test that ReasonCodes constants are available."""
    # Test a few constants
    assert ReasonCodes.HIGH_PRIORITY == "HIGH_PRIORITY"
    assert ReasonCodes.CASH_PAYMENT == "CASH_PAYMENT"
    assert ReasonCodes.HIGH_VALUE == "HIGH_VALUE"
    assert ReasonCodes.BEST_MATCH == "BEST_MATCH"
    assert ReasonCodes.MORNING_SLOT == "MORNING_SLOT"
    
    # Test get_all method
    all_codes = ReasonCodes.get_all()
    assert len(all_codes) > 20  # Should have many codes
    assert "HIGH_PRIORITY" in all_codes
    assert "CASH_PAYMENT" in all_codes


def test_multiple_slots_limit():
    """Test that too many slots are rejected."""
    now = datetime.now()
    
    explain = AIExplain(
        priority_score=75,
        value_score=80,
        risk_no_show=0.15,
        risk_late_payment=0.10,
        reason_codes=[]
    )
    
    # Create 11 slots (over the limit of 10)
    slots = [
        SlotSuggestion(
            start_datetime=now + timedelta(hours=i),
            end_datetime=now + timedelta(hours=i, minutes=30),
            doctor_id=f"D{i:03d}",
            confidence=0.8,
            reason_codes=[]
        )
        for i in range(11)
    ]
    
    # Should raise validation error
    with pytest.raises(ValueError):
        AIRecommendSlotResponse(
            patient_id="P00123",
            service_id="treatment_5",
            urgency_level="medium",
            explain=explain,
            recommended_slots=slots  # Too many!
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
