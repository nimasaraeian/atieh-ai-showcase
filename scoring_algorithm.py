"""
الگوریتم امتیازدهی AI برای سیستم نوبت دهی کلینیک دندانپزشکی آتیه
این الگوریتم بر اساس سه پارامتر امتیاز اولویت را محاسبه می‌کند:
1. نوع پرداخت (نقدی یا بیمه 1-20)
2. نوع درمان (1-20)
3. طول عمر مشتری (مدت زمان عضویت در کلینیک)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from models import PaymentType, TreatmentType, Patient


class AppointmentScoringAlgorithm:
    """کلاس محاسبه امتیاز اولویت نوبت"""
    
    # وزن‌های پارامترها (مجموع باید 100 باشد)
    PAYMENT_WEIGHT = 40  # 40% وزن برای نوع پرداخت
    TREATMENT_WEIGHT = 35  # 35% وزن برای نوع درمان
    LIFETIME_WEIGHT = 25  # 25% وزن برای طول عمر مشتری
    
    # امتیازهای نوع پرداخت
    PAYMENT_SCORES = {
        PaymentType.CASH: 100,  # نقدی - عالی
        
        # بیمه‌های 1-7: خیلی خوب
        PaymentType.INSURANCE_1: 90,
        PaymentType.INSURANCE_2: 85,
        PaymentType.INSURANCE_3: 80,
        PaymentType.INSURANCE_4: 75,
        PaymentType.INSURANCE_5: 70,
        PaymentType.INSURANCE_6: 65,
        PaymentType.INSURANCE_7: 60,
        
        # بیمه‌های 8-14: متوسط
        PaymentType.INSURANCE_8: 50,
        PaymentType.INSURANCE_9: 45,
        PaymentType.INSURANCE_10: 40,
        PaymentType.INSURANCE_11: 35,
        PaymentType.INSURANCE_12: 30,
        PaymentType.INSURANCE_13: 25,
        PaymentType.INSURANCE_14: 20,
        
        # بیمه‌های 15-20: بد
        PaymentType.INSURANCE_15: 15,
        PaymentType.INSURANCE_16: 12,
        PaymentType.INSURANCE_17: 10,
        PaymentType.INSURANCE_18: 8,
        PaymentType.INSURANCE_19: 5,
        PaymentType.INSURANCE_20: 3,
    }
    
    # امتیازهای نوع درمان
    TREATMENT_SCORES = {
        # درمان‌های 1-5: عالی
        TreatmentType.TREATMENT_1: 100,
        TreatmentType.TREATMENT_2: 95,
        TreatmentType.TREATMENT_3: 90,
        TreatmentType.TREATMENT_4: 85,
        TreatmentType.TREATMENT_5: 80,
        
        # درمان‌های 6-10: خیلی خوب
        TreatmentType.TREATMENT_6: 70,
        TreatmentType.TREATMENT_7: 65,
        TreatmentType.TREATMENT_8: 60,
        TreatmentType.TREATMENT_9: 55,
        TreatmentType.TREATMENT_10: 50,
        
        # درمان‌های 11-15: متوسط
        TreatmentType.TREATMENT_11: 40,
        TreatmentType.TREATMENT_12: 35,
        TreatmentType.TREATMENT_13: 30,
        TreatmentType.TREATMENT_14: 25,
        TreatmentType.TREATMENT_15: 20,
        
        # درمان‌های 16-20: بد
        TreatmentType.TREATMENT_16: 15,
        TreatmentType.TREATMENT_17: 12,
        TreatmentType.TREATMENT_18: 10,
        TreatmentType.TREATMENT_19: 8,
        TreatmentType.TREATMENT_20: 5,
    }
    
    @staticmethod
    def calculate_lifetime_score(patient: Patient) -> float:
        """
        محاسبه امتیاز طول عمر مشتری
        
        - کمتر از 6 ماه: متوسط (50 امتیاز)
        - 6 ماه تا 1 سال: خوب (70 امتیاز)
        - 1 سال تا 2 سال: خیلی خوب (85 امتیاز)
        - 2 سال به بالا: عالی (100 امتیاز)
        """
        now = datetime.now(timezone.utc)
        # تبدیل first_visit_date به timezone-aware اگر نیست
        if patient.first_visit_date.tzinfo is None:
            first_visit = patient.first_visit_date.replace(tzinfo=timezone.utc)
        else:
            first_visit = patient.first_visit_date
        lifetime = now - first_visit
        
        # تبدیل به ماه
        months = lifetime.days / 30.0
        
        if months < 6:
            return 50  # متوسط
        elif months < 12:
            return 70  # خوب
        elif months < 24:
            return 85  # خیلی خوب
        else:
            return 100  # عالی
    
    @classmethod
    def calculate_priority_score(
        cls,
        payment_type: PaymentType,
        treatment_type: TreatmentType,
        patient: Patient
    ) -> float:
        """
        محاسبه امتیاز اولویت نهایی
        
        Args:
            payment_type: نوع پرداخت
            treatment_type: نوع درمان
            patient: اطلاعات بیمار
            
        Returns:
            امتیاز اولویت (0-100)
        """
        # محاسبه امتیاز هر پارامتر
        payment_score = cls.PAYMENT_SCORES.get(payment_type, 0)
        treatment_score = cls.TREATMENT_SCORES.get(treatment_type, 0)
        lifetime_score = cls.calculate_lifetime_score(patient)
        
        # محاسبه امتیاز وزنی
        weighted_score = (
            (payment_score * cls.PAYMENT_WEIGHT / 100) +
            (treatment_score * cls.TREATMENT_WEIGHT / 100) +
            (lifetime_score * cls.LIFETIME_WEIGHT / 100)
        )
        
        return round(weighted_score, 2)
    
    @classmethod
    def get_payment_category(cls, payment_type: Optional[PaymentType]) -> str:
        """دریافت دسته‌بندی نوع پرداخت"""
        if payment_type is None:
            return "مشخص نشده"
        if payment_type == PaymentType.CASH:
            return "عالی"
        elif payment_type in [
            PaymentType.INSURANCE_1, PaymentType.INSURANCE_2, PaymentType.INSURANCE_3,
            PaymentType.INSURANCE_4, PaymentType.INSURANCE_5, PaymentType.INSURANCE_6,
            PaymentType.INSURANCE_7
        ]:
            return "خیلی خوب"
        elif payment_type in [
            PaymentType.INSURANCE_8, PaymentType.INSURANCE_9, PaymentType.INSURANCE_10,
            PaymentType.INSURANCE_11, PaymentType.INSURANCE_12, PaymentType.INSURANCE_13,
            PaymentType.INSURANCE_14
        ]:
            return "متوسط"
        else:
            return "بد"
    
    @classmethod
    def get_treatment_category(cls, treatment_type: TreatmentType) -> str:
        """دریافت دسته‌بندی نوع درمان"""
        if treatment_type is None:
            return "مشخص نشده"
        if treatment_type in [
            TreatmentType.TREATMENT_1, TreatmentType.TREATMENT_2, TreatmentType.TREATMENT_3,
            TreatmentType.TREATMENT_4, TreatmentType.TREATMENT_5
        ]:
            return "عالی"
        elif treatment_type in [
            TreatmentType.TREATMENT_6, TreatmentType.TREATMENT_7, TreatmentType.TREATMENT_8,
            TreatmentType.TREATMENT_9, TreatmentType.TREATMENT_10
        ]:
            return "خیلی خوب"
        elif treatment_type in [
            TreatmentType.TREATMENT_11, TreatmentType.TREATMENT_12, TreatmentType.TREATMENT_13,
            TreatmentType.TREATMENT_14, TreatmentType.TREATMENT_15
        ]:
            return "متوسط"
        else:
            return "بد"
    
    @classmethod
    def get_lifetime_category(cls, patient: Patient) -> str:
        """دریافت دسته‌بندی طول عمر مشتری"""
        now = datetime.now(timezone.utc)
        # تبدیل first_visit_date به timezone-aware اگر نیست
        if patient.first_visit_date.tzinfo is None:
            first_visit = patient.first_visit_date.replace(tzinfo=timezone.utc)
        else:
            first_visit = patient.first_visit_date
        lifetime = now - first_visit
        months = lifetime.days / 30.0
        
        if months < 6:
            return "متوسط"
        elif months < 12:
            return "خوب"
        elif months < 24:
            return "خیلی خوب"
        else:
            return "عالی"

