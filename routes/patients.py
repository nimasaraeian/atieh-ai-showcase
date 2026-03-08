"""
Routes مربوط به بیماران
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from models import Patient, Appointment
from models import PaymentType
from database import get_db
from scoring_algorithm import AppointmentScoringAlgorithm
from schemas.patient_schemas import PatientCreate, PatientResponse

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientResponse)
async def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    """ایجاد بیمار جدید"""
    # بررسی تلفن تکراری
    existing = db.query(Patient).filter(Patient.phone == patient.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="شماره تلفن تکراری است")
    
    # تبدیل نوع پرداخت به enum اگر ارائه شده باشد
    payment_type_enum = None
    if patient.payment_type:
        try:
            payment_type_enum = PaymentType[patient.payment_type.upper()]
        except KeyError:
            pass
    
    db_patient = Patient(
        name=patient.name,
        phone=patient.phone,
        national_id=patient.national_id,
        payment_type=payment_type_enum,
        first_visit_date=patient.first_visit_date or datetime.now(timezone.utc)
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    
    # محاسبه طول عمر
    lifetime = datetime.now(timezone.utc) - db_patient.first_visit_date
    lifetime_months = lifetime.days / 30.0
    
    return {
        "id": db_patient.id,
        "name": db_patient.name,
        "phone": db_patient.phone,
        "national_id": db_patient.national_id,
        "payment_type": db_patient.payment_type.value if db_patient.payment_type else None,
        "payment_category": AppointmentScoringAlgorithm.get_payment_category(db_patient.payment_type) if db_patient.payment_type else None,
        "first_visit_date": db_patient.first_visit_date,
        "lifetime_months": round(lifetime_months, 2),
        "lifetime_category": AppointmentScoringAlgorithm.get_lifetime_category(db_patient)
    }


@router.get("", response_model=List[PatientResponse])
async def get_patients(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """لیست بیماران"""
    try:
        query = db.query(Patient)
        
        if search:
            query = query.filter(
                (Patient.name.contains(search)) |
                (Patient.phone.contains(search)) |
                (Patient.national_id.contains(search))
            )
        
        patients = query.offset(skip).limit(limit).all()
        
        result = []
        for patient in patients:
            try:
                # محاسبه lifetime با مدیریت خطا
                now = datetime.now(timezone.utc)
                if patient.first_visit_date.tzinfo is None:
                    first_visit = patient.first_visit_date.replace(tzinfo=timezone.utc)
                else:
                    first_visit = patient.first_visit_date
                lifetime = now - first_visit
                lifetime_months = lifetime.days / 30.0
                
                # محاسبه payment_category با مدیریت خطا
                payment_category = None
                if patient.payment_type:
                    try:
                        payment_category = AppointmentScoringAlgorithm.get_payment_category(patient.payment_type)
                    except Exception as e:
                        print(f"Error getting payment category for patient {patient.id}: {e}")
                        payment_category = "مشخص نشده"
                
                # محاسبه lifetime_category با مدیریت خطا
                lifetime_category = "متوسط"
                try:
                    lifetime_category = AppointmentScoringAlgorithm.get_lifetime_category(patient)
                except Exception as e:
                    print(f"Error getting lifetime category for patient {patient.id}: {e}")
                    # استفاده از محاسبه ساده
                    if lifetime_months < 6:
                        lifetime_category = "متوسط"
                    elif lifetime_months < 12:
                        lifetime_category = "خوب"
                    elif lifetime_months < 24:
                        lifetime_category = "خیلی خوب"
                    else:
                        lifetime_category = "عالی"
                
                # محاسبه سابقه بیمار در کلینیک
                all_appointments = db.query(Appointment).filter(Appointment.patient_id == patient.id).all()
                total_appointments = len(all_appointments)
                completed_appointments = sum(1 for a in all_appointments if a.status == "completed")
                cancelled_appointments = sum(1 for a in all_appointments if a.status == "cancelled")
                no_show_count = sum(1 for a in all_appointments if a.did_patient_show_up is False)
                late_payment_count = sum(1 for a in all_appointments if a.paid_on_time is False)
                
                # تاریخ آخرین نوبت
                last_appointment = None
                if all_appointments:
                    last_appointment = max(all_appointments, key=lambda a: a.appointment_date if a.appointment_date else datetime.min.replace(tzinfo=timezone.utc))
                    last_appointment_date = last_appointment.appointment_date if last_appointment else None
                else:
                    last_appointment_date = None
                
                result.append({
                    "id": patient.id,
                    "name": patient.name,
                    "phone": patient.phone,
                    "national_id": patient.national_id,
                    "payment_type": patient.payment_type.value if patient.payment_type else None,
                    "payment_category": payment_category,
                    "first_visit_date": patient.first_visit_date,
                    "lifetime_months": round(lifetime_months, 2),
                    "lifetime_category": lifetime_category,
                    "total_appointments": total_appointments,
                    "completed_appointments": completed_appointments,
                    "cancelled_appointments": cancelled_appointments,
                    "no_show_count": no_show_count,
                    "late_payment_count": late_payment_count,
                    "last_appointment_date": last_appointment_date
                })
            except Exception as e:
                print(f"Error processing patient {patient.id if patient else 'unknown'}: {e}")
                # اضافه کردن بیمار با اطلاعات حداقلی
                result.append({
                    "id": patient.id if patient else 0,
                    "name": patient.name if patient else "نامشخص",
                    "phone": patient.phone if patient else "-",
                    "national_id": patient.national_id if patient else None,
                    "payment_type": patient.payment_type.value if patient and patient.payment_type else None,
                    "payment_category": "مشخص نشده",
                    "first_visit_date": patient.first_visit_date if patient else datetime.now(timezone.utc),
                    "lifetime_months": 0.0,
                    "lifetime_category": "متوسط"
                })
        
        return result
    except Exception as e:
        print(f"Error in get_patients endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"خطا در دریافت لیست بیماران: {str(e)}")


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, db: Session = Depends(get_db)):
    """دریافت اطلاعات یک بیمار"""
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="بیمار یافت نشد")
        
        # محاسبه lifetime با مدیریت خطا
        now = datetime.now(timezone.utc)
        if patient.first_visit_date.tzinfo is None:
            first_visit = patient.first_visit_date.replace(tzinfo=timezone.utc)
        else:
            first_visit = patient.first_visit_date
        lifetime = now - first_visit
        lifetime_months = lifetime.days / 30.0
        
        # محاسبه payment_category با مدیریت خطا
        payment_category = None
        if patient.payment_type:
            try:
                payment_category = AppointmentScoringAlgorithm.get_payment_category(patient.payment_type)
            except Exception as e:
                print(f"Error getting payment category for patient {patient_id}: {e}")
                payment_category = "مشخص نشده"
        
        # محاسبه lifetime_category با مدیریت خطا
        lifetime_category = "متوسط"
        try:
            lifetime_category = AppointmentScoringAlgorithm.get_lifetime_category(patient)
        except Exception as e:
            print(f"Error getting lifetime category for patient {patient_id}: {e}")
            # استفاده از محاسبه ساده
            if lifetime_months < 6:
                lifetime_category = "متوسط"
            elif lifetime_months < 12:
                lifetime_category = "خوب"
            elif lifetime_months < 24:
                lifetime_category = "خیلی خوب"
            else:
                lifetime_category = "عالی"
        
        return {
            "id": patient.id,
            "name": patient.name,
            "phone": patient.phone,
            "national_id": patient.national_id,
            "payment_type": patient.payment_type.value if patient.payment_type else None,
            "payment_category": payment_category,
            "first_visit_date": patient.first_visit_date,
            "lifetime_months": round(lifetime_months, 2),
            "lifetime_category": lifetime_category
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_patient endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"خطا در دریافت اطلاعات بیمار: {str(e)}")




