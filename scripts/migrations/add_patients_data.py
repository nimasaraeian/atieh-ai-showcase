# -*- coding: utf-8 -*-
"""
اسکریپت افزودن کد ملی و شماره موبایل به بیماران موجود و افزودن بیماران نمونه
"""

import sys
import io
import json
import random
from datetime import datetime, timezone

# تنظیم encoding برای Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Patient, PaymentType
from pathlib import Path
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
from app.utils.patient_helpers import sanitize_patient_data

def generate_national_id():
    """تولید کد ملی 10 رقمی معتبر"""
    digits = [random.randint(0, 9) for _ in range(9)]
    check_digit = sum((10 - i) * digits[i] for i in range(9)) % 11
    if check_digit >= 2:
        check_digit = 11 - check_digit
    else:
        check_digit = check_digit
    digits.append(check_digit)
    return ''.join(map(str, digits))

def generate_mobile():
    """تولید شماره موبایل معتبر ایرانی"""
    prefixes = ["0912", "0913", "0914", "0915", "0916", "0917", "0918", "0919", 
                "0920", "0921", "0922", "0923", "0930", "0931", "0932", "0933", 
                "0934", "0935", "0936", "0937", "0938", "0939", "0941", "0942",
                "0990", "0991", "0992", "0993", "0994"]
    prefix = random.choice(prefixes)
    number = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return prefix + number

def update_existing_patients(db: Session):
    """به‌روزرسانی بیماران موجود با کد ملی و شماره موبایل"""
    patients = db.query(Patient).all()
    updated_count = 0
    used_national_ids = set()
    used_mobiles = set()
    
    # جمع‌آوری کدهای ملی و موبایل‌های موجود
    for p in patients:
        if p.national_id:
            used_national_ids.add(p.national_id)
        if p.phone:
            used_mobiles.add(p.phone)
    
    print(f"[*] در حال بررسي {len(patients)} بيمار موجود...")
    
    for patient in patients:
        updated = False
        
        # اگر کد ملی ندارد، اضافه کن
        if not patient.national_id:
            national_id = generate_national_id()
            while national_id in used_national_ids:
                national_id = generate_national_id()
            patient.national_id = national_id
            used_national_ids.add(national_id)
            updated = True
        
        # اگر شماره موبایل ندارد یا خالی است، اضافه کن
        if not patient.phone or patient.phone.strip() == "":
            mobile = generate_mobile()
            while mobile in used_mobiles:
                mobile = generate_mobile()
            patient.phone = mobile
            used_mobiles.add(mobile)
            updated = True
        
        if updated:
            updated_count += 1
            db.add(patient)
    
    if updated_count > 0:
        db.commit()
        print(f"[OK] {updated_count} بيمار موجود به‌روزرساني شدند.")
    else:
        print("[*] همه بيماران موجود قبلاً کد ملي و شماره موبایل دارند.")
    
    return updated_count

def add_sample_patients(db: Session):
    """افزودن بیماران نمونه از فایل JSON به دیتابیس"""
    repo_root = Path(__file__).resolve().parent.parent.parent
    samples_path = repo_root / "examples" / "sample_patients.json"
    try:
        with open(samples_path, "r", encoding="utf-8") as f:
            sample_patients = json.load(f)
    except FileNotFoundError:
        print("[!] فايل examples/sample_patients.json يافت نشد. ابتدا scripts/demos/generate_sample_patients.py را اجرا کنيد.")
        return 0
    
    # جمع‌آوری کدهای ملی و موبایل‌های موجود
    existing_patients = db.query(Patient).all()
    used_national_ids = {p.national_id for p in existing_patients if p.national_id}
    used_mobiles = {p.phone for p in existing_patients if p.phone}
    
    added_count = 0
    skipped_count = 0
    
    print(f"[*] در حال افزودن {len(sample_patients)} بيمار نمونه...")
    
    for sample in sample_patients:
        # بررسی تکراری نبودن
        if sample['national_id'] in used_national_ids or sample['mobile'] in used_mobiles:
            skipped_count += 1
            continue
        
        # ایجاد بیمار جدید
        # Sanitize data to remove invalid fields like 'mobile'
        patient_data = {
            'name': sample['full_name'],
            'phone': sample['mobile'],  # mobile -> phone
            'national_id': sample['national_id'],
            'payment_type': random.choice(list(PaymentType)),
            'first_visit_date': datetime.now(timezone.utc),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        patient_data = sanitize_patient_data(patient_data)
        new_patient = Patient(**patient_data)
        
        db.add(new_patient)
        used_national_ids.add(sample['national_id'])
        used_mobiles.add(sample['mobile'])
        added_count += 1
    
    if added_count > 0:
        db.commit()
        print(f"[OK] {added_count} بيمار نمونه به ديتابيس اضافه شدند.")
    
    if skipped_count > 0:
        print(f"[*] {skipped_count} بيمار نمونه به دليل تکراري بودن رد شدند.")
    
    return added_count

def main():
    """تابع اصلی"""
    print("=" * 80)
    print("افزودن کد ملي و شماره موبایل به بيماران")
    print("=" * 80)
    print()
    
    # اطمینان از وجود جداول
    init_db()
    
    db = SessionLocal()
    try:
        # به‌روزرسانی بیماران موجود
        updated = update_existing_patients(db)
        print()
        
        # افزودن بیماران نمونه
        added = add_sample_patients(db)
        print()
        
        # نمایش آمار نهایی
        total_patients = db.query(Patient).count()
        patients_with_national_id = db.query(Patient).filter(Patient.national_id.isnot(None)).count()
        patients_with_phone = db.query(Patient).filter(Patient.phone.isnot(None)).count()
        
        print("=" * 80)
        print("آمار نهايي:")
        print("=" * 80)
        print(f"تعداد کل بيماران: {total_patients}")
        print(f"بيماران با کد ملي: {patients_with_national_id}")
        print(f"بيماران با شماره موبایل: {patients_with_phone}")
        print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"[!] خطا: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()





