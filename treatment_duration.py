"""
تعیین مدت زمان لازم برای هر نوع درمان
"""
from models import TreatmentType


class TreatmentDuration:
    """کلاس تعیین مدت زمان درمان"""
    
    # مدت زمان هر نوع درمان به دقیقه
    DURATION_MAP = {
        # درمان‌های 1-5: عالی (معمولاً درمان‌های ساده‌تر)
        TreatmentType.TREATMENT_1: 20,  # معاینه ساده
        TreatmentType.TREATMENT_2: 30,  # جرم‌گیری
        TreatmentType.TREATMENT_3: 45,  # پر کردن ساده
        TreatmentType.TREATMENT_4: 60,  # عصب‌کشی ساده
        TreatmentType.TREATMENT_5: 90,  # روکش ساده
        
        # درمان‌های 6-10: خیلی خوب (درمان‌های متوسط)
        TreatmentType.TREATMENT_6: 30,
        TreatmentType.TREATMENT_7: 45,
        TreatmentType.TREATMENT_8: 60,
        TreatmentType.TREATMENT_9: 75,
        TreatmentType.TREATMENT_10: 90,
        
        # درمان‌های 11-15: متوسط (درمان‌های پیچیده‌تر)
        TreatmentType.TREATMENT_11: 60,
        TreatmentType.TREATMENT_12: 75,
        TreatmentType.TREATMENT_13: 90,
        TreatmentType.TREATMENT_14: 120,  # عصب‌کشی پیچیده
        TreatmentType.TREATMENT_15: 120,
        
        # درمان‌های 16-20: بد (درمان‌های بسیار پیچیده)
        TreatmentType.TREATMENT_16: 90,
        TreatmentType.TREATMENT_17: 120,
        TreatmentType.TREATMENT_18: 150,  # جراحی ساده
        TreatmentType.TREATMENT_19: 180,  # جراحی پیچیده
        TreatmentType.TREATMENT_20: 240,  # جراحی بسیار پیچیده
    }
    
    @classmethod
    def get_duration(cls, treatment_type: TreatmentType) -> int:
        """
        دریافت مدت زمان لازم برای یک نوع درمان
        
        Args:
            treatment_type: نوع درمان
            
        Returns:
            مدت زمان به دقیقه
        """
        return cls.DURATION_MAP.get(treatment_type, 30)  # پیش‌فرض 30 دقیقه
    
    @classmethod
    def get_duration_for_string(cls, treatment_type_str: str) -> int:
        """
        دریافت مدت زمان از رشته
        
        Args:
            treatment_type_str: رشته نوع درمان (مثل "TREATMENT_1")
            
        Returns:
            مدت زمان به دقیقه
        """
        try:
            treatment_type = TreatmentType[treatment_type_str.upper()]
            return cls.get_duration(treatment_type)
        except (KeyError, AttributeError):
            return 30  # پیش‌فرض







