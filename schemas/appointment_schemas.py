"""
مدل‌های Pydantic برای نوبت‌ها
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    """مدل ایجاد نوبت جدید"""
    patient_id: int
    treatment_type: str
    payment_type: Optional[str] = None  # اختیاری - اگر مشخص نشود، از اطلاعات بیمار استفاده می‌شود
    appointment_date: Optional[datetime] = None  # اختیاری - AI پیشنهاد می‌دهد
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    """مدل پاسخ اطلاعات نوبت"""
    id: int
    patient_id: int
    patient_name: str
    appointment_date: datetime
    # SafePaymentType / SafeTreatmentType return None for unknown DB strings
    # (e.g. 'insurance', 'dental_care') so these must be Optional.
    payment_type: Optional[str] = None
    payment_category: Optional[str] = None
    treatment_type: Optional[str] = None
    treatment_category: Optional[str] = None
    priority_score: float
    lifetime_category: Optional[str] = None
    status: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class AIPredictRequest(BaseModel):
    """مدل درخواست پیش‌بینی AI"""
    patient_id: int
    treatment_type: str
    payment_type: Optional[str] = None  # اختیاری - اگر مشخص نشود، از اطلاعات بیمار استفاده می‌شود
    appointment_date: Optional[datetime] = None


class AppointmentOutcomeRequest(BaseModel):
    """مدل ثبت نتیجه نوبت"""
    did_patient_show_up: Optional[bool] = None
    paid_on_time: Optional[bool] = None
    payment_delay_days: Optional[int] = None
    final_amount_paid: Optional[float] = None
    cancellation_reason: Optional[str] = None




