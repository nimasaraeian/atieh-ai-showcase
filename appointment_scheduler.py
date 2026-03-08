"""
سیستم پیشنهاد خودکار نوبت بر اساس زمان‌های خالی و امتیاز اولویت
"""
from datetime import datetime, timedelta, time, timezone
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from models import Appointment, Patient, PaymentType, TreatmentType
from scoring_algorithm import AppointmentScoringAlgorithm


class AppointmentScheduler:
    """کلاس مدیریت و پیشنهاد نوبت‌ها"""
    
    # تنظیمات پیش‌فرض
    DEFAULT_APPOINTMENT_DURATION = 30  # مدت زمان هر نوبت به دقیقه
    DEFAULT_START_HOUR = 9  # ساعت شروع کار
    DEFAULT_END_HOUR = 18  # ساعت پایان کار
    DEFAULT_LUNCH_START = 13  # شروع ناهار
    DEFAULT_LUNCH_END = 14  # پایان ناهار
    
    # روزهای هفته (0=دوشنبه، 6=یکشنبه)
    WORK_DAYS = [0, 1, 2, 3, 4]  # دوشنبه تا جمعه
    
    @classmethod
    def get_available_slots(
        cls,
        db: Session,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = DEFAULT_APPOINTMENT_DURATION
    ) -> List[datetime]:
        """
        دریافت لیست زمان‌های خالی در بازه زمانی مشخص
        
        Args:
            db: Session دیتابیس
            start_date: تاریخ شروع
            end_date: تاریخ پایان
            duration_minutes: مدت زمان هر نوبت به دقیقه
            
        Returns:
            لیست زمان‌های خالی
        """
        available_slots = []
        current_date = start_date.replace(hour=cls.DEFAULT_START_HOUR, minute=0, second=0, microsecond=0)
        
        while current_date <= end_date:
            # بررسی روز کاری
            day_of_week = current_date.weekday()
            if day_of_week not in cls.WORK_DAYS:
                current_date += timedelta(days=1)
                continue
            
            # بررسی ساعت کاری
            current_time = current_date
            while current_time.hour < cls.DEFAULT_END_HOUR:
                # رد کردن زمان ناهار
                if cls.DEFAULT_LUNCH_START <= current_time.hour < cls.DEFAULT_LUNCH_END:
                    current_time += timedelta(hours=1)
                    continue
                
                # بررسی اینکه آیا این زمان خالی است
                slot_end = current_time + timedelta(minutes=duration_minutes)
                
                # بررسی تداخل با نوبت‌های موجود
                # بررسی دستی برای اطمینان از صحت
                # تبدیل slot_end به timezone-aware اگر نیست
                if slot_end.tzinfo is None:
                    slot_end = slot_end.replace(tzinfo=timezone.utc)
                if current_time.tzinfo is None:
                    current_time = current_time.replace(tzinfo=timezone.utc)
                
                existing_appointments = db.query(Appointment).filter(
                    and_(
                        Appointment.status.in_(["pending", "confirmed"]),
                        Appointment.appointment_date < slot_end
                    )
                ).all()
                
                conflicting = None
                for apt in existing_appointments:
                    apt_duration = getattr(apt, 'duration_minutes', None) or cls.DEFAULT_APPOINTMENT_DURATION
                    apt_start = apt.appointment_date
                    # تبدیل apt_start به timezone-aware اگر نیست
                    if apt_start.tzinfo is None:
                        apt_start = apt_start.replace(tzinfo=timezone.utc)
                    apt_end = apt_start + timedelta(minutes=apt_duration)
                    if apt_end > current_time:
                        conflicting = apt
                        break
                
                if not conflicting:
                    available_slots.append(current_time)
                
                current_time += timedelta(minutes=duration_minutes)
            
            # رفتن به روز بعد
            current_date += timedelta(days=1)
            current_date = current_date.replace(hour=cls.DEFAULT_START_HOUR, minute=0, second=0, microsecond=0)
        
        return available_slots
    
    @classmethod
    def get_pending_appointments_with_scores(
        cls,
        db: Session,
        limit: int = 50
    ) -> List[Dict]:
        """
        دریافت نوبت‌های در انتظار با امتیاز اولویت
        
        Returns:
            لیست نوبت‌های در انتظار با اطلاعات کامل
        """
        appointments = db.query(Appointment).join(Patient).filter(
            Appointment.status == "pending"
        ).order_by(desc(Appointment.priority_score)).limit(limit).all()
        
        result = []
        for appointment in appointments:
            result.append({
                "appointment_id": appointment.id,
                "patient_id": appointment.patient_id,
                "patient_name": appointment.patient.name,
                "patient_phone": appointment.patient.phone,
                "payment_type": appointment.payment_type.value if appointment.payment_type else None,
                "payment_category": AppointmentScoringAlgorithm.get_payment_category(appointment.payment_type),
                "treatment_type": appointment.treatment_type.value if appointment.treatment_type else None,
                "treatment_category": AppointmentScoringAlgorithm.get_treatment_category(appointment.treatment_type),
                "lifetime_category": AppointmentScoringAlgorithm.get_lifetime_category(appointment.patient),
                "priority_score": appointment.priority_score,
                "current_appointment_date": appointment.appointment_date,
                "notes": appointment.notes
            })
        
        return result
    
    @classmethod
    def suggest_appointments(
        cls,
        db: Session,
        days_ahead: int = 7,
        max_suggestions: int = 10
    ) -> List[Dict]:
        """
        پیشنهاد نوبت‌ها بر اساس زمان‌های خالی و امتیاز اولویت
        
        Args:
            db: Session دیتابیس
            days_ahead: تعداد روزهای آینده برای بررسی
            max_suggestions: حداکثر تعداد پیشنهادات
            
        Returns:
            لیست پیشنهادات شامل: بیمار، زمان پیشنهادی، امتیاز اولویت
        """
        # دریافت زمان‌های خالی
        start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=days_ahead)
        
        available_slots = cls.get_available_slots(db, start_date, end_date)
        
        # دریافت نوبت‌های در انتظار
        pending_appointments = cls.get_pending_appointments_with_scores(db, limit=100)
        
        # تطبیق نوبت‌ها با زمان‌های خالی
        suggestions = []
        
        for appointment in pending_appointments:
            if len(suggestions) >= max_suggestions:
                break
            
            # پیدا کردن بهترین زمان خالی برای این نوبت
            best_slot = None
            min_time_diff = float('inf')
            
            current_appointment_time = appointment["current_appointment_date"]
            # اطمینان از timezone-aware بودن
            if isinstance(current_appointment_time, datetime):
                if current_appointment_time.tzinfo is None:
                    current_appointment_time = current_appointment_time.replace(tzinfo=timezone.utc)
            
            for slot in available_slots:
                # اطمینان از timezone-aware بودن slot
                slot_datetime = slot
                if isinstance(slot_datetime, datetime):
                    if slot_datetime.tzinfo is None:
                        slot_datetime = slot_datetime.replace(tzinfo=timezone.utc)
                
                # اگر زمان خالی قبل از زمان فعلی نوبت باشد، بهتر است
                if slot_datetime < current_appointment_time:
                    time_diff = (current_appointment_time - slot_datetime).total_seconds()
                    if time_diff < min_time_diff:
                        min_time_diff = time_diff
                        best_slot = slot_datetime
                # یا اگر زمان خالی نزدیک به زمان فعلی باشد
                elif slot_datetime >= current_appointment_time:
                    time_diff = (slot_datetime - current_appointment_time).total_seconds()
                    if time_diff < 3600:  # کمتر از 1 ساعت تفاوت
                        if time_diff < min_time_diff:
                            min_time_diff = time_diff
                            best_slot = slot_datetime
            
            if best_slot:
                # حذف این زمان از لیست زمان‌های خالی (تا دوباره استفاده نشود)
                # پیدا کردن index slot اصلی
                try:
                    available_slots.remove(best_slot)
                except ValueError:
                    # اگر پیدا نشد، با مقایسه timezone-aware پیدا می‌کنیم
                    for i, slot in enumerate(available_slots):
                        slot_normalized = slot
                        if isinstance(slot_normalized, datetime) and slot_normalized.tzinfo is None:
                            slot_normalized = slot_normalized.replace(tzinfo=timezone.utc)
                        if slot_normalized == best_slot:
                            available_slots.pop(i)
                            break
                
                suggestions.append({
                    "appointment_id": appointment["appointment_id"],
                    "patient_id": appointment["patient_id"],
                    "patient_name": appointment["patient_name"],
                    "patient_phone": appointment["patient_phone"],
                    "current_appointment_date": appointment["current_appointment_date"],
                    "suggested_appointment_date": best_slot,
                    "priority_score": appointment["priority_score"],
                    "payment_type": appointment["payment_type"],
                    "payment_category": appointment["payment_category"],
                    "treatment_type": appointment["treatment_type"],
                    "treatment_category": appointment["treatment_category"],
                    "lifetime_category": appointment["lifetime_category"],
                    "notes": appointment["notes"],
                    "time_improvement": f"{int(min_time_diff / 60)} دقیقه" if min_time_diff < 3600 else "زودتر"
                })
        
        # مرتب‌سازی بر اساس امتیاز اولویت
        suggestions.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return suggestions[:max_suggestions]
    
    @classmethod
    def auto_assign_appointment(
        cls,
        db: Session,
        appointment_id: int,
        suggested_date: datetime
    ) -> bool:
        """
        تخصیص خودکار نوبت به زمان پیشنهادی
        
        Args:
            db: Session دیتابیس
            appointment_id: شناسه نوبت
            suggested_date: زمان پیشنهادی
            
        Returns:
            True اگر موفق بود، False در غیر این صورت
        """
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment:
            return False
        
        # بررسی اینکه زمان هنوز خالی است
        slot_end = suggested_date + timedelta(
            minutes=appointment.duration_minutes or cls.DEFAULT_APPOINTMENT_DURATION
        )
        
        # بررسی تداخل - روش ساده‌تر
        existing_appointments = db.query(Appointment).filter(
            and_(
                Appointment.id != appointment_id,
                Appointment.status.in_(["pending", "confirmed"]),
                Appointment.appointment_date < slot_end
            )
        ).all()
        
        conflicting = None
        for apt in existing_appointments:
            apt_duration = apt.duration_minutes if hasattr(apt, 'duration_minutes') and apt.duration_minutes else cls.DEFAULT_APPOINTMENT_DURATION
            apt_end = apt.appointment_date + timedelta(minutes=apt_duration)
            if apt_end > suggested_date:
                conflicting = apt
                break
        
        if conflicting:
            return False
        
        # به‌روزرسانی زمان نوبت
        appointment.appointment_date = suggested_date
        db.commit()
        
        return True

