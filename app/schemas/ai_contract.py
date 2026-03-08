"""
AI Output Contract - Stable Response Schema
============================================
This module defines the stable API contract for all AI-powered endpoints.
All AI responses must conform to these schemas to ensure consistency.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SlotSuggestion(BaseModel):
    """A single time slot suggestion for an appointment"""
    
    start_datetime: datetime = Field(..., description="Start time of the slot")
    end_datetime: datetime = Field(..., description="End time of the slot")
    doctor_id: str | int = Field(..., description="ID of the doctor for this slot")
    doctor_name: Optional[str] = Field(None, description="Name of the doctor")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    reason_codes: List[str] = Field(default_factory=list, description="Short reason codes")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('confidence must be between 0 and 1')
        return v
    
    @field_validator('reason_codes')
    @classmethod
    def validate_reason_codes(cls, v):
        # Ensure reason codes are short and uppercase
        return [code.upper().replace(' ', '_') for code in v]
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "start_datetime": "2026-02-10T09:00:00Z",
                "end_datetime": "2026-02-10T09:30:00Z",
                "doctor_id": "123",
                "doctor_name": "دکتر احمدی",
                "confidence": 0.85,
                "reason_codes": ["HIGH_PRIORITY", "MORNING_SLOT", "PREFERRED_DOCTOR"]
            }
        })


class AIExplain(BaseModel):
    """Explanation of AI scoring and reasoning"""
    
    priority_score: int = Field(..., ge=0, le=100, description="Overall priority (0-100)")
    value_score: int = Field(..., ge=0, le=100, description="Patient value score (0-100)")
    risk_no_show: float = Field(..., ge=0.0, le=1.0, description="Risk of no-show (0-1)")
    risk_late_payment: float = Field(..., ge=0.0, le=1.0, description="Risk of late payment (0-1)")
    reason_codes: List[str] = Field(default_factory=list, description="Explanation codes")
    
    @field_validator('priority_score', 'value_score')
    @classmethod
    def validate_score_range(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('score must be between 0 and 100')
        return v
    
    @field_validator('risk_no_show', 'risk_late_payment')
    @classmethod
    def validate_risk_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('risk must be between 0 and 1')
        return v
    
    @field_validator('reason_codes')
    @classmethod
    def validate_reason_codes(cls, v):
        return [code.upper().replace(' ', '_') for code in v]
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "priority_score": 75,
                "value_score": 80,
                "risk_no_show": 0.15,
                "risk_late_payment": 0.10,
                "reason_codes": ["HIGH_VALUE", "CASH_PAYMENT", "LOYAL_CUSTOMER"]
            }
        })


class AIRecommendSlotResponse(BaseModel):
    """Complete AI recommendation response for slot booking"""
    
    patient_id: str | int = Field(..., description="Patient identifier")
    service_id: Optional[str | int] = Field(None, description="Service/treatment identifier")
    urgency_level: Optional[str] = Field(None, description="Urgency level (low, medium, high, critical)")
    explain: AIExplain = Field(..., description="AI explanation and scoring")
    recommended_slots: List[SlotSuggestion] = Field(
        default_factory=list,
        description="List of recommended time slots (3-5 suggestions)"
    )
    
    @field_validator('urgency_level')
    @classmethod
    def validate_urgency(cls, v):
        if v is not None and v.lower() not in ['low', 'medium', 'high', 'critical']:
            raise ValueError('urgency_level must be one of: low, medium, high, critical')
        return v.lower() if v else None
    
    @field_validator('recommended_slots')
    @classmethod
    def validate_slots_count(cls, v):
        if len(v) > 10:
            raise ValueError('Too many slots (max 10)')
        return v
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "patient_id": "12345",
                "service_id": "treatment_5",
                "urgency_level": "high",
                "explain": {
                    "priority_score": 85,
                    "value_score": 90,
                    "risk_no_show": 0.05,
                    "risk_late_payment": 0.03,
                    "reason_codes": ["CASH_PAYMENT", "HIGH_VALUE", "URGENT_TREATMENT"]
                },
                "recommended_slots": [
                    {
                        "start_datetime": "2026-02-10T09:00:00Z",
                        "end_datetime": "2026-02-10T09:30:00Z",
                        "doctor_id": "123",
                        "doctor_name": "دکتر احمدی",
                        "confidence": 0.92,
                        "reason_codes": ["BEST_MATCH", "MORNING_SLOT"]
                    }
                ]
            }
        })


class AIScorePatientResponse(BaseModel):
    """Response for scoring a patient without slot recommendation"""
    
    patient_id: str | int
    explain: AIExplain
    insights: Optional[dict] = Field(None, description="Additional insights")
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "patient_id": "12345",
                "explain": {
                    "priority_score": 75,
                    "value_score": 80,
                    "risk_no_show": 0.15,
                    "risk_late_payment": 0.10,
                    "reason_codes": ["HIGH_VALUE", "LOYAL_CUSTOMER"]
                },
                "insights": {
                    "lifetime_months": 24,
                    "total_appointments": 15,
                    "completion_rate": 0.93
                }
            }
        })


# Reason Code Constants
class ReasonCodes:
    """Standard reason codes used across the AI system"""
    
    # Priority reasons
    HIGH_PRIORITY = "HIGH_PRIORITY"
    MEDIUM_PRIORITY = "MEDIUM_PRIORITY"
    LOW_PRIORITY = "LOW_PRIORITY"
    
    # Payment reasons
    CASH_PAYMENT = "CASH_PAYMENT"
    INSURANCE_GOOD = "INSURANCE_GOOD"
    INSURANCE_POOR = "INSURANCE_POOR"
    
    # Value reasons
    HIGH_VALUE = "HIGH_VALUE"
    MEDIUM_VALUE = "MEDIUM_VALUE"
    LOW_VALUE = "LOW_VALUE"
    LOYAL_CUSTOMER = "LOYAL_CUSTOMER"
    NEW_PATIENT = "NEW_PATIENT"
    
    # Risk reasons
    NO_SHOW_RISK = "NO_SHOW_RISK"
    NO_SHOW_HIGH = "NO_SHOW_HIGH"
    LATE_PAYMENT_RISK = "LATE_PAYMENT_RISK"
    PERFECT_RECORD = "PERFECT_RECORD"
    
    # Treatment reasons
    URGENT_TREATMENT = "URGENT_TREATMENT"
    ROUTINE_TREATMENT = "ROUTINE_TREATMENT"
    COMPLEX_TREATMENT = "COMPLEX_TREATMENT"
    
    # Slot reasons
    BEST_MATCH = "BEST_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    MORNING_SLOT = "MORNING_SLOT"
    AFTERNOON_SLOT = "AFTERNOON_SLOT"
    EVENING_SLOT = "EVENING_SLOT"
    PREFERRED_DOCTOR = "PREFERRED_DOCTOR"
    PREFERRED_DAY = "PREFERRED_DAY"
    AVAILABLE_SOON = "AVAILABLE_SOON"
    
    # Availability reasons
    HIGH_AVAILABILITY = "HIGH_AVAILABILITY"
    LOW_AVAILABILITY = "LOW_AVAILABILITY"
    LAST_SLOT = "LAST_SLOT"
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all reason codes"""
        return [
            getattr(cls, attr) for attr in dir(cls)
            if not attr.startswith('_') and isinstance(getattr(cls, attr), str) and attr.isupper()
        ]
