from datetime import datetime, timedelta
import enum
import logging

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

_models_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe Enum TypeDecorators
# ---------------------------------------------------------------------------
# SQLite stores enum values as plain strings (e.g. 'insurance', 'dental_care').
# If the stored string is not a valid member of the Python Enum, SQLAlchemy's
# built-in Enum() type raises LookupError at hydration time, crashing the
# request before any application code runs.
#
# _SafeEnumType overrides that behaviour:
#   READ  (DB → Python): unknown string  → None   (no exception)
#   WRITE (Python → DB): enum instance   → enum.value string (unchanged)
#                        raw string      → stored as-is + warning if unknown
#                        None            → NULL (unchanged)
# ---------------------------------------------------------------------------

class _SafeEnumType(TypeDecorator):
    """
    Generic TypeDecorator that maps an arbitrary Python Enum over a String
    column without raising on unknown DB values.
    """
    impl = String
    cache_ok = True

    def __init__(self, enum_class, *args, **kwargs):
        self._enum_class = enum_class
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        """Python -> DB: accept enum instance or raw string."""
        if value is None:
            return None
        if isinstance(value, self._enum_class):
            return value.value
        raw = str(value)
        try:
            self._enum_class(raw)   # validate — raises ValueError if unknown
        except ValueError:
            _models_logger.warning(
                "SafeEnumType(%s): storing unknown value %r",
                self._enum_class.__name__, raw,
            )
        return raw

    def process_result_value(self, value, dialect):
        """DB -> Python: map to enum member; return None for unknown values."""
        if value is None:
            return None
        try:
            return self._enum_class(value)
        except ValueError:
            _models_logger.debug(
                "SafeEnumType(%s): unknown DB value %r -> None",
                self._enum_class.__name__, value,
            )
            return None


class SafePaymentType(_SafeEnumType):
    """String-backed, crash-safe column type for the PaymentType enum."""
    cache_ok = True

    def __init__(self, *args, **kwargs):
        # PaymentType not yet defined here; resolved at first use via lazy ref
        super().__init__(None, *args, **kwargs)

    def _resolve(self):
        if self._enum_class is None:
            self._enum_class = PaymentType

    def process_bind_param(self, value, dialect):
        self._resolve()
        return super().process_bind_param(value, dialect)

    def process_result_value(self, value, dialect):
        self._resolve()
        return super().process_result_value(value, dialect)


class SafeTreatmentType(_SafeEnumType):
    """String-backed, crash-safe column type for the TreatmentType enum."""
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(None, *args, **kwargs)

    def _resolve(self):
        if self._enum_class is None:
            self._enum_class = TreatmentType

    def process_bind_param(self, value, dialect):
        self._resolve()
        return super().process_bind_param(value, dialect)

    def process_result_value(self, value, dialect):
        self._resolve()
        return super().process_result_value(value, dialect)


# Whitelist of valid Patient fields - used for sanitization
PATIENT_VALID_FIELDS = {
    'name', 'phone', 'national_id', 'first_visit_date',
    'created_at', 'updated_at', 'payment_type', 'lifetime_value_score'
}


class PaymentType(enum.Enum):
    """نوع پرداخت"""
    CASH = "cash"  # نقدی - عالی
    INSURANCE_1 = "insurance_1"  # بیمه 1 - خیلی خوب
    INSURANCE_2 = "insurance_2"
    INSURANCE_3 = "insurance_3"
    INSURANCE_4 = "insurance_4"
    INSURANCE_5 = "insurance_5"
    INSURANCE_6 = "insurance_6"
    INSURANCE_7 = "insurance_7"
    INSURANCE_8 = "insurance_8"  # بیمه 8 - متوسط
    INSURANCE_9 = "insurance_9"
    INSURANCE_10 = "insurance_10"
    INSURANCE_11 = "insurance_11"
    INSURANCE_12 = "insurance_12"
    INSURANCE_13 = "insurance_13"
    INSURANCE_14 = "insurance_14"
    INSURANCE_15 = "insurance_15"  # بیمه 15 - بد
    INSURANCE_16 = "insurance_16"
    INSURANCE_17 = "insurance_17"
    INSURANCE_18 = "insurance_18"
    INSURANCE_19 = "insurance_19"
    INSURANCE_20 = "insurance_20"


class TreatmentType(enum.Enum):
    """نوع درمان - 20 نوع درمان"""
    TREATMENT_1 = "treatment_1"  # 1-5: عالی
    TREATMENT_2 = "treatment_2"
    TREATMENT_3 = "treatment_3"
    TREATMENT_4 = "treatment_4"
    TREATMENT_5 = "treatment_5"
    TREATMENT_6 = "treatment_6"  # 5-10: خیلی خوب
    TREATMENT_7 = "treatment_7"
    TREATMENT_8 = "treatment_8"
    TREATMENT_9 = "treatment_9"
    TREATMENT_10 = "treatment_10"
    TREATMENT_11 = "treatment_11"  # 10-15: متوسط
    TREATMENT_12 = "treatment_12"
    TREATMENT_13 = "treatment_13"
    TREATMENT_14 = "treatment_14"
    TREATMENT_15 = "treatment_15"
    TREATMENT_16 = "treatment_16"  # 15-20: بد
    TREATMENT_17 = "treatment_17"
    TREATMENT_18 = "treatment_18"
    TREATMENT_19 = "treatment_19"
    TREATMENT_20 = "treatment_20"


class Patient(Base):
    """مدل بیمار"""
    __tablename__ = 'patients'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    national_id = Column(String(20), unique=True)
    payment_type = Column(SafePaymentType(), nullable=True)  # نوع پرداخت پیش‌فرض بیمار
    first_visit_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    appointments = relationship("Appointment", back_populates="patient")
    
    # Backward compatibility aliases
    @property
    def mobile(self):
        """Alias for phone field for backward compatibility"""
        return self.phone
    
    @mobile.setter
    def mobile(self, value):
        """Alias setter for phone field"""
        self.phone = value
    
    def __init__(self, **kwargs):
        """
        Custom init with field validation to prevent 'family' and 'mobile' errors.
        
        This is the CHOKE POINT - filters out invalid fields before SQLAlchemy sees them.
        """
        # Filter to only valid fields
        valid_kwargs = {k: v for k, v in kwargs.items() if k in PATIENT_VALID_FIELDS}
        
        # Explicitly reject known bad fields with helpful error message
        bad_fields = {'family', 'mobile', 'first_name', 'last_name', 'gender', 'email'}
        rejected = [k for k in kwargs.keys() if k in bad_fields]
        
        if rejected:
            # Don't raise error - just log and filter them out
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Patient() called with invalid fields {rejected} - ignoring them")
        
        # Call parent init with only valid fields
        super().__init__(**valid_kwargs)


class Appointment(Base):
    """مدل نوبت"""
    __tablename__ = 'appointments'
    
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)  # مدت زمان نوبت به دقیقه
    payment_type = Column(SafePaymentType(), nullable=True)    # DB has legacy 'insurance'/'cash' strings
    treatment_type = Column(SafeTreatmentType(), nullable=True) # DB has legacy 'dental_care'/'endo' strings
    priority_score = Column(Float, nullable=False)  # امتیاز اولویت
    status = Column(String(20), default='pending')  # pending, confirmed, completed, cancelled
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # AI-related fields
    ai_priority_score = Column(Float, nullable=True)  # optional AI-based priority
    
    # Outcome logging fields
    did_patient_show_up = Column(Boolean, nullable=True)  # True / False / None
    paid_on_time = Column(Boolean, nullable=True)         # پرداخت به موقع یا نه
    payment_delay_days = Column(Integer, nullable=True)   # تعداد روز تأخیر (اگر هست)
    final_amount_paid = Column(Float, nullable=True)      # مبلغ نهایی پرداخت شده
    cancellation_reason = Column(Text, nullable=True)     # در صورت لغو نوبت
    
    patient = relationship("Patient", back_populates="appointments")


class ClinicSchedule(Base):
    """مدل زمان‌های کاری کلینیک"""
    __tablename__ = 'clinic_schedules'
    
    id = Column(Integer, primary_key=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(String(10), nullable=False)  # "09:00"
    end_time = Column(String(10), nullable=False)  # "18:00"
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    created_at = Column(DateTime, default=datetime.utcnow)

