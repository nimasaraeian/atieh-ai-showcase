# -*- coding: utf-8 -*-
"""
اسکریپت تولید 100 بیمار نمونه با نام، کد ملی و شماره موبایل
"""

import sys
import io
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# تنظیم encoding برای Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# لیست نام‌های رایج ایرانی
first_names = [
    "محمد", "علی", "حسن", "حسین", "رضا", "احمد", "مهدی", "امیر", "سعید", "رضوان",
    "فاطمه", "زهرا", "مریم", "سارا", "نرگس", "زینب", "فریبا", "لیلا", "سمیرا", "نیلوفر",
    "امیرحسین", "محمدعلی", "محمدحسین", "علی‌رضا", "حسین‌رضا", "مهدی‌رضا", "امیرمحمد", "سیدعلی", "سیدمحمد", "سیدحسین",
    "محمدامین", "محمدجواد", "محمدباقر", "محمدتقی", "محمدصادق", "علی‌اکبر", "علی‌اصغر", "حسین‌علی", "حسن‌علی", "رضا‌علی",
    "زهرا", "فاطمه‌زهرا", "مریم‌سادات", "زینب‌سادات", "فاطمه‌سادات", "معصومه", "خدیجه", "عایشه", "رقیه", "طاهره",
    "پریسا", "پریا", "پگاه", "پردیس", "پری", "پریچهر", "پریس", "پریزاد", "پریوش", "پریا",
    "آرمان", "آرین", "آریا", "آراد", "آرتا", "آرینا", "آرزو", "آرمانا", "آرینا", "آرتا",
    "دانیال", "دانیا", "دانی", "دانیالا", "دانی", "دانیا", "دانیال", "دانی", "دانیا", "دانیال",
    "کامران", "کامبیز", "کامران", "کامبیز", "کامران", "کامبیز", "کامران", "کامبیز", "کامران", "کامبیز"
]

last_names = [
    "احمدی", "محمدی", "حسینی", "رضایی", "کریمی", "موسوی", "صادقی", "نوری", "جعفری", "عباسی",
    "زاده", "پور", "نژاد", "فر", "پور", "زاده", "نژاد", "فر", "پور", "زاده",
    "خانی", "یاری", "بختیاری", "کردی", "لری", "ترک", "عرب", "بلوچ", "گیلانی", "مازندرانی",
    "تهرانی", "اصفهانی", "شیرازی", "مشهدی", "تبریزی", "یزدی", "کرمانی", "اهوازی", "رشتی", "قمیمی",
    "سادات", "سید", "سیدزاده", "سیدمحمدی", "سیدحسینی", "سیدرضایی", "سیداحمدی", "سیدکریمی", "سیدموسوی", "سیدصادقی",
    "امینی", "باقری", "جعفری", "حسنی", "حیدری", "خالدی", "داوودی", "رستمی", "سلیمانی", "شریفی",
    "طاهری", "عزیزی", "غلامی", "فارسی", "قاسمی", "کاظمی", "لطفی", "محمودی", "نظری", "هاشمی",
    "یوسفی", "یعقوبی", "یوسفی", "یعقوبی", "یوسفی", "یعقوبی", "یوسفی", "یعقوبی", "یوسفی", "یعقوبی"
]

def generate_national_id():
    """تولید کد ملی 10 رقمی معتبر"""
    # کد ملی باید 10 رقم باشد و رقم آخر چک‌سام داشته باشد
    digits = [random.randint(0, 9) for _ in range(9)]
    
    # محاسبه رقم کنترل (ساده‌سازی شده)
    check_digit = sum((10 - i) * digits[i] for i in range(9)) % 11
    if check_digit >= 2:
        check_digit = 11 - check_digit
    else:
        check_digit = check_digit
    
    digits.append(check_digit)
    return ''.join(map(str, digits))

def generate_mobile():
    """تولید شماره موبایل معتبر ایرانی"""
    # شماره موبایل باید با 09 شروع شود
    prefixes = ["0912", "0913", "0914", "0915", "0916", "0917", "0918", "0919", 
                "0920", "0921", "0922", "0923", "0930", "0931", "0932", "0933", 
                "0934", "0935", "0936", "0937", "0938", "0939", "0941", "0942",
                "0990", "0991", "0992", "0993", "0994"]
    prefix = random.choice(prefixes)
    number = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return prefix + number

def generate_sample_patients(count=100):
    """تولید لیست بیماران نمونه"""
    patients = []
    used_national_ids = set()
    used_mobiles = set()
    
    for i in range(count):
        # انتخاب نام و نام خانوادگی تصادفی
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name}"
        
        # تولید کد ملی یکتا
        national_id = generate_national_id()
        while national_id in used_national_ids:
            national_id = generate_national_id()
        used_national_ids.add(national_id)
        
        # تولید شماره موبایل یکتا
        mobile = generate_mobile()
        while mobile in used_mobiles:
            mobile = generate_mobile()
        used_mobiles.add(mobile)
        
        patients.append({
            "id": i + 1,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "national_id": national_id,
            "mobile": mobile
        })
    
    return patients

def save_to_file(patients, filename="sample_patients.txt"):
    """ذخیره لیست در فایل متنی"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("لیست 100 بیمار نمونه\n")
        f.write("=" * 80 + "\n\n")
        
        for patient in patients:
            f.write(f"شماره: {patient['id']}\n")
            f.write(f"نام و نام خانوادگی: {patient['full_name']}\n")
            f.write(f"کد ملی: {patient['national_id']}\n")
            f.write(f"شماره موبایل: {patient['mobile']}\n")
            f.write("-" * 80 + "\n")
    
    print(f"[OK] ليست در فايل '{filename}' ذخيره شد.")

def save_to_csv(patients, filename="sample_patients.csv"):
    """ذخیره لیست در فایل CSV"""
    import csv
    
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["شماره", "نام", "نام خانوادگی", "نام کامل", "کد ملی", "شماره موبایل"])
        
        for patient in patients:
            writer.writerow([
                patient['id'],
                patient['first_name'],
                patient['last_name'],
                patient['full_name'],
                patient['national_id'],
                patient['mobile']
            ])
    
    print(f"[OK] ليست در فايل CSV '{filename}' ذخيره شد.")

def save_to_json(patients, filename="sample_patients.json"):
    """ذخیره لیست در فایل JSON"""
    import json
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(patients, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] ليست در فايل JSON '{filename}' ذخيره شد.")

if __name__ == "__main__":
    print("[*] در حال توليد 100 بيمار نمونه...")
    patients = generate_sample_patients(100)
    
    print(f"[OK] {len(patients)} بيمار نمونه توليد شد.\n")
    
    # ذخیره در examples/ (repo-relative)
    examples_dir = Path(__file__).resolve().parent.parent.parent / "examples"
    examples_dir.mkdir(exist_ok=True)
    save_to_file(patients, str(examples_dir / "sample_patients.txt"))
    save_to_csv(patients, str(examples_dir / "sample_patients.csv"))
    save_to_json(patients, str(examples_dir / "sample_patients.json"))
    
    print("\n" + "=" * 80)
    print("نمونه از 5 بيمار اول:")
    print("=" * 80)
    for patient in patients[:5]:
        print(f"نام: {patient['full_name']}")
        print(f"کد ملی: {patient['national_id']}")
        print(f"موبایل: {patient['mobile']}")
        print("-" * 40)

