"""
مدل‌های Pydantic برای بیماران
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PatientCreate(BaseModel):
    """مدل ایجاد بیمار جدید"""
    name: str
    phone: str
    national_id: Optional[str] = None
    payment_type: Optional[str] = None  # نوع پرداخت پیش‌فرض
    first_visit_date: Optional[datetime] = None


class PatientResponse(BaseModel):
    """مدل پاسخ اطلاعات بیمار"""
    id: int
    name: str
    phone: str
    national_id: Optional[str]
    payment_type: Optional[str] = None
    payment_category: Optional[str] = None
    first_visit_date: datetime
    lifetime_months: float
    lifetime_category: str
    # سابقه بیمار در کلینیک
    total_appointments: int = 0  # تعداد کل نوبت‌ها
    completed_appointments: int = 0  # تعداد نوبت‌های تکمیل شده
    cancelled_appointments: int = 0  # تعداد نوبت‌های لغو شده
    no_show_count: int = 0  # تعداد عدم حضور
    late_payment_count: int = 0  # تعداد پرداخت‌های دیر
    last_appointment_date: Optional[datetime] = None  # تاریخ آخرین نوبت
    
    class Config:
        from_attributes = True




