"""
اسکریپت افزودن داده‌های نمونه به سیستم
"""
import sys
import io
# تنظیم encoding برای Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from models import Patient, Appointment, PaymentType, TreatmentType
from database import SessionLocal, init_db
from treatment_duration import TreatmentDuration
import random

# Import patient creation helper
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from app.utils.patient_helpers import sanitize_patient_data

# داده‌های نمونه
SAMPLE_DATA = [
    {"name": "Ali", "family": "Mohammadi", "gender": "M", "mobile": "0912000001", 
     "payment": "Cash", "insurance": None, "treatment": "T2", "lifetime": ">2y"},
    {"name": "Sara", "family": "Ahmadi", "gender": "F", "mobile": "0912000002", 
     "payment": "Insurance", "insurance": 3, "treatment": "T6", "lifetime": "1-2y"},
    {"name": "Reza", "family": "Karimi", "gender": "M", "mobile": "0912000003", 
     "payment": "Insurance", "insurance": 9, "treatment": "T4", "lifetime": "1-2y"},
    {"name": "Mina", "family": "Hosseini", "gender": "F", "mobile": "0912000004", 
     "payment": "Insurance", "insurance": 18, "treatment": "T17", "lifetime": "6-12m"},
    {"name": "Amir", "family": "Jalali", "gender": "M", "mobile": "0912000005", 
     "payment": "Cash", "insurance": None, "treatment": "T1", "lifetime": ">2y"},
    {"name": "Neda", "family": "Rostami", "gender": "F", "mobile": "0912000006", 
     "payment": "Insurance", "insurance": 12, "treatment": "T8", "lifetime": "1-2y"},
    {"name": "Hossein", "family": "Shafiei", "gender": "M", "mobile": "0912000007", 
     "payment": "Insurance", "insurance": 6, "treatment": "T11", "lifetime": "6-12m"},
    {"name": "Leila", "family": "Abbasi", "gender": "F", "mobile": "0912000008", 
     "payment": "Insurance", "insurance": 20, "treatment": "T19", "lifetime": "6-12m"},
    {"name": "Mehdi", "family": "Ghorbani", "gender": "M", "mobile": "0912000009", 
     "payment": "Cash", "insurance": None, "treatment": "T3", "lifetime": ">2y"},
    {"name": "Zahra", "family": "Rahimi", "gender": "F", "mobile": "0912000010", 
     "payment": "Insurance", "insurance": 14, "treatment": "T9", "lifetime": "1-2y"},
    {"name": "Mostafa", "family": "Ebrahimi", "gender": "M", "mobile": "0912000011", 
     "payment": "Insurance", "insurance": 2, "treatment": "T7", "lifetime": ">2y"},
    {"name": "Elham", "family": "Yazdani", "gender": "F", "mobile": "0912000012", 
     "payment": "Insurance", "insurance": 16, "treatment": "T15", "lifetime": "6-12m"},
    {"name": "Saeed", "family": "Moradi", "gender": "M", "mobile": "0912000013", 
     "payment": "Cash", "insurance": None, "treatment": "T5", "lifetime": ">2y"},
    {"name": "Parisa", "family": "Safari", "gender": "F", "mobile": "0912000014", 
     "payment": "Insurance", "insurance": 10, "treatment": "T12", "lifetime": "1-2y"},
    {"name": "Mohammad", "family": "Kazemi", "gender": "M", "mobile": "0912000015", 
     "payment": "Insurance", "insurance": 5, "treatment": "T6", "lifetime": ">2y"},
    {"name": "Shirin", "family": "Ansari", "gender": "F", "mobile": "0912000016", 
     "payment": "Insurance", "insurance": 17, "treatment": "T18", "lifetime": "6-12m"},
    {"name": "Arash", "family": "Bahrami", "gender": "M", "mobile": "0912000017", 
     "payment": "Cash", "insurance": None, "treatment": "T4", "lifetime": "1-2y"},
    {"name": "Fatemeh", "family": "Najafi", "gender": "F", "mobile": "0912000018", 
     "payment": "Insurance", "insurance": 8, "treatment": "T10", "lifetime": "1-2y"},
    {"name": "Peyman", "family": "Akbari", "gender": "M", "mobile": "0912000019", 
     "payment": "Insurance", "insurance": 13, "treatment": "T14", "lifetime": "6-12m"},
    {"name": "Samira", "family": "Taghavi", "gender": "F", "mobile": "0912000020", 
     "payment": "Insurance", "insurance": 1, "treatment": "T2", "lifetime": ">2y"},
]


def calculate_first_visit_date(lifetime: str) -> datetime:
    """محاسبه تاریخ اولین مراجعه بر اساس طول عمر"""
    now = datetime.now(timezone.utc)
    
    if lifetime == ">2y":
        # بیش از 2 سال: بین 2 تا 3 سال پیش
        days_ago = random.randint(730, 1095)  # 2-3 سال
    elif lifetime == "1-2y":
        # 1 تا 2 سال: بین 365 تا 730 روز پیش
        days_ago = random.randint(365, 730)
    elif lifetime == "6-12m":
        # 6 تا 12 ماه: بین 180 تا 365 روز پیش
        days_ago = random.randint(180, 365)
    else:  # <6m
        # کمتر از 6 ماه: بین 30 تا 180 روز پیش
        days_ago = random.randint(30, 180)
    
    return now - timedelta(days=days_ago)


def get_payment_type(payment: str, insurance: int = None) -> PaymentType:
    """تبدیل نوع پرداخت به enum"""
    if payment == "Cash":
        return PaymentType.CASH
    else:
        return PaymentType[f"INSURANCE_{insurance}"]


def get_treatment_type(treatment: str) -> TreatmentType:
    """تبدیل نوع درمان به enum"""
    # T2 -> TREATMENT_2
    treatment_num = treatment.replace("T", "")
    return TreatmentType[f"TREATMENT_{treatment_num}"]


def add_sample_data():
    """افزودن داده‌های نمونه به دیتابیس"""
    # ایجاد جداول
    init_db()
    
    db: Session = SessionLocal()
    
    try:
        # بررسی وجود داده‌های قبلی
        existing_patients = db.query(Patient).count()
        if existing_patients > 0:
            print(f"Warning: {existing_patients} patients already exist in database.")
            print("Deleting existing data...")
            # حذف نوبت‌های موجود
            db.query(Appointment).delete()
            # حذف بیماران موجود
            db.query(Patient).delete()
            db.commit()
            print("Existing data deleted.")
        
        print("Adding sample data...")
        
        for i, data in enumerate(SAMPLE_DATA, 1):
            # محاسبه تاریخ اولین مراجعه
            first_visit_date = calculate_first_visit_date(data["lifetime"])
            
            # تبدیل نوع پرداخت و درمان
            payment_type = get_payment_type(data["payment"], data["insurance"])
            treatment_type = get_treatment_type(data["treatment"])
            
            # ایجاد بیمار
            # Use sanitize_patient_data to filter out invalid fields like 'family' and 'mobile'
            patient_data = {
                'name': f"{data['name']} {data['family']}",  # Merge name and family into full name
                'phone': data["mobile"],  # mobile -> phone
                'national_id': None,
                'payment_type': payment_type,
                'first_visit_date': first_visit_date
            }
            # Sanitize to remove any invalid fields
            patient_data = sanitize_patient_data(patient_data)
            patient = Patient(**patient_data)
            
            db.add(patient)
            db.flush()  # برای دریافت ID
            
            # محاسبه مدت زمان بر اساس نوع درمان
            duration_minutes = TreatmentDuration.get_duration(treatment_type)
            
            # محاسبه امتیاز اولویت
            from scoring_algorithm import AppointmentScoringAlgorithm
            priority_score = AppointmentScoringAlgorithm.calculate_priority_score(
                payment_type=payment_type,
                treatment_type=treatment_type,
                patient=patient
            )
            
            # ایجاد نوبت (تاریخ نوبت را در آینده نزدیک قرار می‌دهیم)
            appointment_date = datetime.now(timezone.utc) + timedelta(days=random.randint(1, 30))
            
            appointment = Appointment(
                patient_id=patient.id,
                appointment_date=appointment_date,
                duration_minutes=duration_minutes,
                payment_type=payment_type,
                treatment_type=treatment_type,
                priority_score=priority_score,
                status="pending",
                notes=None
            )
            
            db.add(appointment)
            
            print(f"Patient {i}/20: {patient.name} - Score: {priority_score:.2f}")
        
        db.commit()
        print("\nAll data added successfully!")
        print(f"Total patients: {db.query(Patient).count()}")
        print(f"Total appointments: {db.query(Appointment).count()}")
        
    except Exception as e:
        db.rollback()
        print(f"Error adding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_sample_data()

