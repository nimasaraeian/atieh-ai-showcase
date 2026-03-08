"""
Canonical Internal Models
==========================
Minimal, normalized data models used throughout the engine.
These models are independent of external CRM structure.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class PatientCore(BaseModel):
    """Core patient information (CRM-agnostic)."""
    
    id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Full name")
    phone: str = Field(..., description="Contact phone number")
    national_id: Optional[str] = Field(None, description="National ID number")
    payment_type: str = Field(..., description="Primary payment type")
    first_visit_date: datetime = Field(..., description="Date of first visit")
    lifetime_days: int = Field(0, description="Days since first visit")
    notes: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "P00123",
            "name": "علی احمدی",
                "phone": "09121234567",
                "national_id": "1234567890",
                "payment_type": "cash",
                "first_visit_date": "2024-01-15T00:00:00Z",
                "lifetime_days": 386,
                "notes": None
        }
    })


class AppointmentCore(BaseModel):
    """Core appointment information."""
    
    id: str = Field(..., description="Unique appointment identifier")
    patient_id: str = Field(..., description="Patient identifier")
    service_id: str = Field(..., description="Service/treatment identifier")
    service_name: str = Field(..., description="Service name")
    appointment_date: datetime = Field(..., description="Appointment datetime")
    duration_minutes: int = Field(..., description="Duration in minutes")
    payment_type: str = Field(..., description="Payment type for this appointment")
    status: str = Field(..., description="Appointment status")
    priority_score: float = Field(0.0, description="Calculated priority score")
    did_patient_show_up: Optional[bool] = Field(None, description="Did patient show up?")
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "A00456",
                "patient_id": "P00123",
                "service_id": "treatment_5",
                "service_name": "بلیچینگ",
                "appointment_date": "2026-02-10T09:00:00Z",
                "duration_minutes": 45,
                "payment_type": "cash",
                "status": "confirmed",
                "priority_score": 85.5,
                "did_patient_show_up": None,
                "cancellation_reason": None,
                "notes": None
        }
    })


class PaymentCore(BaseModel):
    """Core payment information."""
    
    id: str = Field(..., description="Unique payment identifier")
    appointment_id: str = Field(..., description="Related appointment ID")
    patient_id: str = Field(..., description="Patient identifier")
    amount: float = Field(..., description="Payment amount")
    payment_type: str = Field(..., description="Payment method/type")
    payment_status: str = Field(..., description="Payment status")
    paid_on_time: Optional[bool] = Field(None, description="Was payment on time?")
    payment_delay_days: Optional[int] = Field(None, description="Days delayed")
    payment_date: Optional[datetime] = Field(None, description="Actual payment date")
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "id": "PAY00789",
                "appointment_id": "A00456",
                "patient_id": "P00123",
                "amount": 1500000.0,
                "payment_type": "cash",
                "payment_status": "paid",
                "paid_on_time": True,
                "payment_delay_days": 0,
                "payment_date": "2026-02-10T10:00:00Z"
        }
    })


class DoctorCore(BaseModel):
    """Core doctor information."""
    
    id: str = Field(..., description="Unique doctor identifier")
    name: str = Field(..., description="Doctor name")
    specialty: Optional[str] = Field(None, description="Medical specialty")
    years_of_experience: int = Field(0, description="Years of experience")
    rating: float = Field(0.0, description="Rating (0-5)")
    is_active: bool = Field(True, description="Is currently active?")
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "id": "D001",
                "name": "دکتر احمدی",
                "specialty": "ارتودنسی",
                "years_of_experience": 15,
                "rating": 4.8,
                "is_active": True
        }
    })


class ScheduleCore(BaseModel):
    """Core schedule/availability information."""
    
    id: str = Field(..., description="Unique schedule identifier")
    doctor_id: str = Field(..., description="Doctor identifier")
    doctor_name: str = Field(..., description="Doctor name")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    shift_code: str = Field(..., description="Shift code (D, E, N)")
    shift_name: str = Field(..., description="Shift name")
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: str = Field(..., description="End time (HH:MM)")
    is_available: bool = Field(True, description="Is available for booking?")
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "id": "SCH00123",
                "doctor_id": "D001",
                "doctor_name": "دکتر احمدی",
                "date": "2026-02-10",
                "shift_code": "D",
                "shift_name": "صبح",
                "start_time": "08:00",
                "end_time": "14:00",
                "is_available": True
        }
    })


class BlockCore(BaseModel):
    """Core blocking event information."""
    
    id: str = Field(..., description="Unique block identifier")
    doctor_id: str = Field(..., description="Doctor identifier")
    doctor_name: str = Field(..., description="Doctor name")
    block_type: str = Field(..., description="Type of block")
    block_name: str = Field(..., description="Block name")
    start_datetime: datetime = Field(..., description="Start datetime")
    end_datetime: datetime = Field(..., description="End datetime")
    reason: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "id": "BLK00001",
                "doctor_id": "D001",
                "doctor_name": "دکتر احمدی",
                "block_type": "vacation",
                "block_name": "مرخصی",
                "start_datetime": "2026-02-15T00:00:00Z",
                "end_datetime": "2026-02-20T00:00:00Z",
                "reason": "مرخصی سالانه"
        }
    })


class PatientHistoryCore(BaseModel):
    """Complete patient history with stats."""
    
    patient: PatientCore
    appointments: List[AppointmentCore] = []
    payments: List[PaymentCore] = []
    
    # Calculated stats
    total_appointments: int = 0
    completed_appointments: int = 0
    cancelled_appointments: int = 0
    no_show_count: int = 0
    late_payment_count: int = 0
    completion_rate: float = 0.0
    payment_reliability: float = 1.0
    
    model_config = ConfigDict(json_schema_extra={
            "example": {
                "patient": {
                    "id": "P00123",
                    "name": "علی احمدی",
                    "phone": "09121234567",
                    "payment_type": "cash",
                    "first_visit_date": "2024-01-15T00:00:00Z",
                    "lifetime_days": 386
                },
                "appointments": [],
                "payments": [],
                "total_appointments": 15,
                "completed_appointments": 14,
                "cancelled_appointments": 1,
                "no_show_count": 0,
                "late_payment_count": 1,
                "completion_rate": 0.93,
                "payment_reliability": 0.93
        }
    })
