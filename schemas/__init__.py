"""
مدل‌های Pydantic برای درخواست‌ها و پاسخ‌ها
"""
from .patient_schemas import PatientCreate, PatientResponse
from .appointment_schemas import (
    AppointmentCreate,
    AppointmentResponse,
    AIPredictRequest,
    AppointmentOutcomeRequest
)

__all__ = [
    "PatientCreate",
    "PatientResponse",
    "AppointmentCreate",
    "AppointmentResponse",
    "AIPredictRequest",
    "AppointmentOutcomeRequest",
]




