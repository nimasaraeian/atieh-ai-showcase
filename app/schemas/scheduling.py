"""Pydantic schemas for scheduling requests and responses."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Union
from datetime import datetime


class PatientContext(BaseModel):
    """Patient information context for scheduling."""
    patient_id: Union[str, int] = Field(..., description="Unique patient identifier")
    full_name: Optional[str] = Field(None, description="Patient full name")
    phone: Optional[str] = Field(None, description="Patient phone number")
    insurance_name: Optional[str] = Field(None, description="Patient insurance company")
    payment_behavior_tag: Optional[str] = Field(None, description="Payment behavior tag (good/fair/poor)")
    unfinished_treatment_title: Optional[str] = Field(None, description="Pending treatment title")
    preferred_doctor: Optional[str] = Field(None, description="Preferred doctor name")
    preferred_weekday: Optional[str] = Field(None, description="Preferred weekday (Persian)")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_id": "12345",
                "full_name": "علی احمدی",
                "phone": "09121234567",
                "insurance_name": "ایران",
                "payment_behavior_tag": "good",
                "unfinished_treatment_title": "درمان ریشه",
                "preferred_doctor": "دکتر احمدی",
                "preferred_weekday": "شنبه",
                "notes": "Patient prefers morning appointments"
            }
        }
    )


class SchedulingRequest(BaseModel):
    """Request for scheduling slot recommendations."""
    service_name: str = Field(..., description="Name of the service/treatment (Persian)")
    service_id: Optional[str] = Field(None, description="Service ID (e.g. TREATMENT_5); used for catalog lookup when provided")
    desired_weekday: Optional[str] = Field(None, description="Desired weekday (Persian)")
    preferred_doctor: Optional[str] = Field(None, description="Preferred doctor name (can override patient pref)")
    preferred_doctor_id: Optional[int] = Field(None, description="Preferred doctor id (CLI/CRM override)")
    slot_minutes: int = Field(30, description="Slot duration in minutes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "service_name": "کشیدن دندان",
                "desired_weekday": "شنبه",
                "preferred_doctor": "دکتر احمدی",
                "slot_minutes": 30
            }
        }
    )


class CaseContext(BaseModel):
    """Complete case context combining patient and scheduling request."""
    patient: PatientContext = Field(..., description="Patient context information")
    request: SchedulingRequest = Field(..., description="Scheduling request details")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient": {
                    "patient_id": "12345",
                    "full_name": "علی احمدی",
                    "insurance_name": "ایران",
                    "unfinished_treatment_title": "درمان ریشه"
                },
                "request": {
                    "service_name": "کشیدن دندان",
                    "slot_minutes": 30
                }
            }
        }
    )


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of recommendation score."""
    urgency_score: float = Field(..., ge=0.0, le=1.0, description="Urgency score (0-1)")
    financial_score: float = Field(..., ge=0.0, le=1.0, description="Financial/insurance score (0-1)")
    availability_score: float = Field(..., ge=0.0, le=1.0, description="Doctor availability score (0-1)")
    complexity_fit_score: float = Field(..., ge=0.0, le=1.0, description="Complexity fit score (0-1)")
    time_score: float = Field(..., ge=0.0, le=1.0, description="Time preference score (0-1)")
    total_score: float = Field(..., ge=0.0, le=1.0, description="Weighted total score (0-1)")
    
    def calculate_total(self) -> float:
        """Calculate weighted total score."""
        return (
            0.30 * self.urgency_score +
            0.25 * self.financial_score +
            0.20 * self.availability_score +
            0.15 * self.complexity_fit_score +
            0.10 * self.time_score
        )


class SlotRecommendation(BaseModel):
    """A recommended time slot with scoring details."""
    weekday: str = Field(..., description="Persian weekday")
    shift_code: str = Field(..., description="Shift code (D/E/N)")
    start_time: str = Field(..., description="Slot start time (HH:MM)")
    end_time: str = Field(..., description="Slot end time (HH:MM)")
    doctor: str = Field(..., description="Doctor name for this slot")
    doctor_id: Optional[int] = Field(None, description="Doctor ID from reference (if matched)")
    score: float = Field(..., ge=0.0, le=1.0, description="Total recommendation score")
    breakdown: ScoreBreakdown = Field(..., description="Score breakdown")
    service_duration_min: int = Field(..., description="Service duration in minutes")
    service_complexity: float = Field(..., description="Service complexity weight")
    reason_strings_fa: Optional[List[str]] = Field(None, description="Persian explanation strings for this slot")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "weekday": "شنبه",
                "shift_code": "D",
                "start_time": "09:00",
                "end_time": "09:30",
                "doctor": "دکتر احمدی",
                "score": 0.85,
                "breakdown": {
                    "urgency_score": 0.9,
                    "financial_score": 0.8,
                    "availability_score": 1.0,
                    "complexity_fit_score": 0.7,
                    "total_score": 0.85
                },
                "service_duration_min": 30,
                "service_complexity": 0.6
            }
        }
    )


class ScheduleDraft(BaseModel):
    """A single scheduled appointment draft."""
    chosen_weekday: str = Field(..., description="Selected weekday")
    shift_code: str = Field(..., description="Selected shift code (D/E/N)")
    start_time: str = Field(..., description="Appointment start time (HH:MM)")
    end_time: str = Field(..., description="Appointment end time (HH:MM)")
    doctor: str = Field(..., description="Assigned doctor name")
    score: float = Field(..., ge=0.0, le=1.0, description="Recommendation score")
    reason: str = Field(..., description="Explanation for this choice")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chosen_weekday": "شنبه",
                "shift_code": "D",
                "start_time": "09:00",
                "end_time": "09:30",
                "doctor": "دکتر احمدی",
                "score": 0.85,
                "reason": "Highest score with preferred doctor available"
            }
        }
    )


class SchedulingResult(BaseModel):
    """Complete scheduling recommendation result."""
    top_recommendations: List[SlotRecommendation] = Field(..., description="Top recommended slots")
    generated_at: datetime = Field(default_factory=datetime.now, description="Timestamp of generation")
    inputs_echo: SchedulingRequest = Field(..., description="Echo of input request")
    total_slots_evaluated: int = Field(..., description="Total number of slots evaluated")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "top_recommendations": [],
                "generated_at": "2026-02-03T10:30:00",
                "inputs_echo": {
                    "service_name": "کشیدن دندان"
                },
                "total_slots_evaluated": 252
            }
        }
    )
