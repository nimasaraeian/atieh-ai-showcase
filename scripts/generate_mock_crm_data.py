#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mock CRM Data Generator
=======================
Generates realistic mock data for testing the AI scheduling system.
Creates JSON files that mimic real CRM data structures.

Usage:
    python scripts/generate_mock_crm_data.py [--patients N] [--appointments N]
"""
import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from faker import Faker
    faker = Faker(['fa_IR'])  # Persian locale
except ImportError:
    print("Warning: Faker not installed, using simple name generation")
    faker = None

# Persian names fallback
PERSIAN_FIRST_NAMES = [
    "علی", "محمد", "حسین", "رضا", "احمد", "مهدی", "فاطمه", "زهرا", "مریم", "سارا",
    "نرگس", "پریسا", "امیر", "حسن", "عباس", "مجید", "سمیرا", "نازنین", "لیلا", "نیلوفر",
    "کیانوش", "پوریا", "سهیل", "بهناز", "شیدا", "پروین", "رویا", "مینا", "هانیه", "سمانه"
]
PERSIAN_LAST_NAMES = [
    "احمدی", "محمدی", "رضایی", "علیزاده", "حسینی", "کریمی", "جعفری", "صادقی", "ابراهیمی", "خانی",
    "نوری", "مرادی", "یوسفی", "باقری", "اسدی", "ملکی", "قاسمی", "شریفی", "موسوی", "حیدری"
]

DOCTOR_NAMES = [
    "دکتر احمدی", "دکتر نعمتی", "دکتر صادقی", "دکتر کریمی", "دکتر محمدی",
    "دکتر رضایی", "دکتر علیزاده", "دکتر حسینی", "دکتر جعفری", "دکتر مرادی",
    "دکتر باقری", "دکتر یوسفی", "دکتر اسدی", "دکتر ملکی", "دکتر قاسمی",
    "دکتر شریفی", "دکتر موسوی", "دکتر حیدری", "دکتر نوری", "دکتر خانی"
]

SERVICES = [
    {"id": "treatment_1", "name": "کشیدن دندان", "duration": 20, "complexity": 0.6},
    {"id": "treatment_2", "name": "عصب کشی", "duration": 60, "complexity": 0.9},
    {"id": "treatment_3", "name": "ترمیم دندان", "duration": 30, "complexity": 0.5},
    {"id": "treatment_4", "name": "ایمپلنت", "duration": 90, "complexity": 1.0},
    {"id": "treatment_5", "name": "بلیچینگ", "duration": 45, "complexity": 0.4},
    {"id": "treatment_6", "name": "جرم گیری", "duration": 30, "complexity": 0.3},
    {"id": "treatment_7", "name": "روکش دندان", "duration": 45, "complexity": 0.7},
    {"id": "treatment_8", "name": "ارتودنسی", "duration": 30, "complexity": 0.8},
    {"id": "treatment_9", "name": "کامپوزیت", "duration": 30, "complexity": 0.5},
    {"id": "treatment_10", "name": "ونیر", "duration": 60, "complexity": 0.8},
    {"id": "treatment_11", "name": "پروتز", "duration": 45, "complexity": 0.7},
    {"id": "treatment_12", "name": "لثه درمانی", "duration": 40, "complexity": 0.6},
    {"id": "treatment_13", "name": "درمان کانال", "duration": 60, "complexity": 0.9},
    {"id": "treatment_14", "name": "دندان عقل", "duration": 30, "complexity": 0.7},
    {"id": "treatment_15", "name": "پر کردن دندان", "duration": 25, "complexity": 0.4},
    {"id": "treatment_16", "name": "جراحی لثه", "duration": 90, "complexity": 0.9},
    {"id": "treatment_17", "name": "فلوراید تراپی", "duration": 20, "complexity": 0.2},
    {"id": "treatment_18", "name": "سفید کردن دندان", "duration": 50, "complexity": 0.4},
    {"id": "treatment_19", "name": "ترمیم دندان شکسته", "duration": 40, "complexity": 0.6},
    {"id": "treatment_20", "name": "کشیدن دندان شیری", "duration": 15, "complexity": 0.3},
]

PAYMENT_TYPES = ["cash"] + [f"insurance_{i}" for i in range(1, 21)]

STATUSES = ["booked", "confirmed", "completed", "cancelled", "no_show", "rescheduled"]
PAYMENT_STATUSES = ["paid", "partial", "pending", "refunded"]


def generate_persian_name() -> str:
    """Generate a realistic Persian name."""
    if faker:
        return faker.name()
    first = random.choice(PERSIAN_FIRST_NAMES)
    last = random.choice(PERSIAN_LAST_NAMES)
    return f"{first} {last}"


def generate_phone() -> str:
    """Generate a realistic Iranian phone number."""
    if faker:
        return faker.phone_number()
    return f"09{random.randint(100000000, 999999999)}"


def generate_national_id() -> str:
    """Generate a 10-digit national ID."""
    return str(random.randint(1000000000, 9999999999))


def generate_patients(n: int = 200) -> List[Dict[str, Any]]:
    """Generate realistic patient data."""
    print(f"Generating {n} patients...")
    patients = []
    
    for i in range(1, n + 1):
        # Create first visit date (6 months to 5 years ago)
        days_ago = random.randint(180, 1825)
        first_visit = datetime.now() - timedelta(days=days_ago)
        
        # Assign payment type with realistic distribution
        payment_type = random.choices(
            PAYMENT_TYPES,
            weights=[20] + [80 / 20] * 20,  # 20% cash, 80% insurance
            k=1
        )[0]
        
        patient = {
            "id": f"P{i:05d}",
            "name": generate_persian_name(),
            "phone": generate_phone(),
            "national_id": generate_national_id(),
            "payment_type": payment_type,
            "first_visit_date": first_visit.isoformat(),
            "created_at": first_visit.isoformat(),
            "updated_at": datetime.now().isoformat(),
            "notes": None,
            # Metadata for testing
            "_meta": {
                "lifetime_days": days_ago,
                "expected_category": (
                    "عالی" if days_ago > 730 else
                    "خیلی خوب" if days_ago > 365 else
                    "خوب" if days_ago > 180 else
                    "متوسط"
                )
            }
        }
        patients.append(patient)
    
    print(f"✓ Generated {len(patients)} patients")
    return patients


def generate_appointments(patients: List[Dict], n: int = 1000) -> List[Dict[str, Any]]:
    """Generate realistic appointment data."""
    print(f"Generating {n} appointments...")
    appointments = []
    
    # Date range: 90 days ago to 90 days future
    start_date = datetime.now() - timedelta(days=90)
    end_date = datetime.now() + timedelta(days=90)
    
    for i in range(1, n + 1):
        patient = random.choice(patients)
        service = random.choice(SERVICES)
        
        # Random date within range
        random_days = random.randint(0, (end_date - start_date).days)
        appt_date = start_date + timedelta(days=random_days)
        
        # Random time during working hours (9-18)
        hour = random.randint(9, 17)
        minute = random.choice([0, 15, 30, 45])
        appt_date = appt_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Status based on date
        if appt_date < datetime.now() - timedelta(days=1):
            # Past appointments
            status = random.choices(
                ["completed", "cancelled", "no_show"],
                weights=[85, 10, 5],
                k=1
            )[0]
        elif appt_date < datetime.now():
            status = "confirmed"
        else:
            # Future appointments
            status = random.choices(
                ["booked", "confirmed"],
                weights=[30, 70],
                k=1
            )[0]
        
        # Calculate priority score (simplified)
        payment_score = 100 if patient["payment_type"] == "cash" else random.randint(30, 90)
        treatment_score = (21 - int(service["id"].split("_")[1])) * 5
        lifetime_score = min(100, (patient["_meta"]["lifetime_days"] / 730) * 100)
        priority = (payment_score * 0.4 + treatment_score * 0.35 + lifetime_score * 0.25)
        
        appointment = {
            "id": f"A{i:05d}",
            "patient_id": patient["id"],
            "service_id": service["id"],
            "service_name": service["name"],
            "appointment_date": appt_date.isoformat(),
            "duration_minutes": service["duration"],
            "payment_type": patient["payment_type"],
            "status": status,
            "priority_score": round(priority, 2),
            "notes": None,
            "created_at": (appt_date - timedelta(days=random.randint(1, 30))).isoformat(),
            "updated_at": datetime.now().isoformat(),
            # Outcome data (only for completed appointments)
            "did_patient_show_up": True if status == "completed" else (False if status == "no_show" else None),
            "cancellation_reason": "تغییر برنامه" if status == "cancelled" else None
        }
        appointments.append(appointment)
    
    print(f"✓ Generated {len(appointments)} appointments")
    return appointments


def generate_payments(appointments: List[Dict], coverage: float = 0.8) -> List[Dict[str, Any]]:
    """Generate payment data for appointments."""
    n = int(len(appointments) * coverage)
    print(f"Generating {n} payments...")
    payments = []
    
    # Only for past appointments
    past_appointments = [a for a in appointments if a["status"] in ["completed", "cancelled"]]
    sampled = random.sample(past_appointments, min(n, len(past_appointments)))
    
    for i, appt in enumerate(sampled, 1):
        appt_date = datetime.fromisoformat(appt["appointment_date"])
        
        # Payment status distribution
        if appt["status"] == "completed":
            payment_status = random.choices(
                PAYMENT_STATUSES,
                weights=[80, 5, 10, 5],  # mostly paid
                k=1
            )[0]
        else:
            payment_status = random.choices(
                ["refunded", "pending"],
                weights=[70, 30],
                k=1
            )[0]
        
        # Payment delay
        if payment_status == "paid":
            delay_days = max(0, random.randint(-5, 30))  # Some pay early, most on time or late
            paid_on_time = delay_days <= 7
        else:
            delay_days = None
            paid_on_time = False
        
        # Payment amount
        base_amount = 1000000 + (appt["duration_minutes"] * 10000)  # Simplified pricing
        if payment_status == "partial":
            amount = base_amount * random.uniform(0.3, 0.7)
        elif payment_status == "refunded":
            amount = base_amount * 0.9  # 10% cancellation fee
        elif payment_status == "paid":
            amount = base_amount
        else:
            amount = 0
        
        payment = {
            "id": f"PAY{i:05d}",
            "appointment_id": appt["id"],
            "patient_id": appt["patient_id"],
            "amount": round(amount, 0),
            "payment_type": appt["payment_type"],
            "payment_status": payment_status,
            "paid_on_time": paid_on_time if payment_status == "paid" else None,
            "payment_delay_days": delay_days,
            "payment_date": (appt_date + timedelta(days=delay_days)).isoformat() if delay_days is not None else None,
            "created_at": datetime.now().isoformat()
        }
        payments.append(payment)
    
    print(f"✓ Generated {len(payments)} payments")
    return payments


def generate_doctors(names: List[str] = DOCTOR_NAMES) -> List[Dict[str, Any]]:
    """Generate doctor data."""
    print(f"Generating {len(names)} doctors...")
    doctors = []
    
    specialties = ["عمومی", "اطفال", "ارتودنسی", "ایمپلنت", "جراحی", "زیبایی"]
    
    for i, name in enumerate(names, 1):
        doctor = {
            "id": f"D{i:03d}",
            "name": name,
            "specialty": random.choice(specialties),
            "years_of_experience": random.randint(3, 25),
            "rating": round(random.uniform(4.0, 5.0), 1),
            "is_active": random.random() > 0.05,  # 95% active
            "created_at": datetime.now().isoformat()
        }
        doctors.append(doctor)
    
    print(f"✓ Generated {len(doctors)} doctors")
    return doctors


def generate_schedules(doctors: List[Dict], days: int = 60) -> List[Dict[str, Any]]:
    """Generate doctor schedule/shift data."""
    print(f"Generating schedules for {days} days...")
    schedules = []
    
    shifts = [
        {"code": "D", "start": "08:00", "end": "14:00", "name": "صبح"},
        {"code": "E", "start": "14:00", "end": "20:00", "name": "عصر"},
    ]
    
    start_date = datetime.now() - timedelta(days=30)
    schedule_id = 1
    
    for day_offset in range(days):
        date = start_date + timedelta(days=day_offset)
        weekday = date.weekday()  # 0=Monday, 6=Sunday
        
        # Skip Fridays (weekday=4 in ISO, but we consider Friday as day off)
        if weekday == 4:
            continue
        
        # Each doctor works ~5 days a week, random shifts
        for doctor in doctors:
            if not doctor["is_active"]:
                continue
            
            # ~70% chance doctor works this day
            if random.random() > 0.7:
                continue
            
            # Random shift
            shift = random.choice(shifts)
            
            schedule = {
                "id": f"SCH{schedule_id:05d}",
                "doctor_id": doctor["id"],
                "doctor_name": doctor["name"],
                "date": date.strftime("%Y-%m-%d"),
                "weekday": date.strftime("%A"),
                "shift_code": shift["code"],
                "shift_name": shift["name"],
                "start_time": shift["start"],
                "end_time": shift["end"],
                "is_available": random.random() > 0.05,  # 95% available
                "created_at": datetime.now().isoformat()
            }
            schedules.append(schedule)
            schedule_id += 1
    
    print(f"✓ Generated {len(schedules)} schedule entries")
    return schedules


def generate_blocks(doctors: List[Dict], schedules: List[Dict]) -> List[Dict[str, Any]]:
    """Generate blocking events (vacations, meetings, etc.)."""
    print("Generating blocking events...")
    blocks = []
    
    block_types = [
        {"type": "vacation", "name": "مرخصی"},
        {"type": "meeting", "name": "جلسه"},
        {"type": "conference", "name": "کنفرانس"},
        {"type": "emergency", "name": "اضطراری"},
    ]
    
    # Create ~50 random blocks
    for i in range(1, 51):
        doctor = random.choice(doctors)
        block_type = random.choice(block_types)
        
        # Random date within schedule range
        if schedules:
            schedule = random.choice(schedules)
            date_str = schedule["date"]
            date = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            date = datetime.now() + timedelta(days=random.randint(0, 60))
        
        # Random time block during working hours
        start_hour = random.randint(9, 16)
        duration = random.choice([30, 60, 120, 240])  # minutes
        
        start_time = date.replace(hour=start_hour, minute=0)
        end_time = start_time + timedelta(minutes=duration)
        
        block = {
            "id": f"BLK{i:05d}",
            "doctor_id": doctor["id"],
            "doctor_name": doctor["name"],
            "block_type": block_type["type"],
            "block_name": block_type["name"],
            "start_datetime": start_time.isoformat(),
            "end_datetime": end_time.isoformat(),
            "reason": f"{block_type['name']} - {doctor['name']}",
            "created_at": datetime.now().isoformat()
        }
        blocks.append(block)
    
    print(f"✓ Generated {len(blocks)} blocking events")
    return blocks


def save_json(data: List[Dict], filename: str, output_dir: Path):
    """Save data to JSON file with proper encoding."""
    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved {filepath}")


def generate_readme(output_dir: Path):
    """Generate README for mock data."""
    readme_content = """# Mock CRM Data

This directory contains realistic mock data for testing the AI scheduling system.

## Files Generated:

- **patients.json** (200+ records): Patient information with Persian names
- **appointments.json** (1000+ records): Appointment history and future bookings
- **payments.json** (800+ records): Payment records with realistic delays
- **doctors.json** (20 records): Doctor profiles with specialties
- **schedules.json** (600+ records): Doctor shift schedules for 60 days
- **blocks.json** (50 records): Blocking events (vacations, meetings)

## Data Characteristics:

### Patients:
- Realistic Persian names (using Faker or fallback list)
- Iranian phone numbers (09XX format)
- 10-digit national IDs
- Payment type distribution: 20% cash, 80% insurance
- Lifetime range: 6 months to 5 years

### Appointments:
- Date range: 90 days past to 90 days future
- Working hours: 9 AM - 6 PM
- Status distribution:
  - Past: 85% completed, 10% cancelled, 5% no-show
  - Future: 30% booked, 70% confirmed
- Priority scores calculated based on payment, treatment, lifetime

### Payments:
- Coverage: ~80% of completed/cancelled appointments
- Status distribution: 80% paid, 5% partial, 10% pending, 5% refunded
- Realistic payment delays (some early, most on-time, some late)

### Doctors:
- 20 doctors with Persian names
- Specialties: عمومی, اطفال, ارتودنسی, ایمپلنت, جراحی, زیبایی
- Experience: 3-25 years
- Rating: 4.0-5.0
- 95% active

### Schedules:
- 60 days coverage (past and future)
- Two shifts: صبح (08:00-14:00), عصر (14:00-20:00)
- Fridays off
- ~70% doctor availability per day

### Blocks:
- Types: vacation, meeting, conference, emergency
- Random time blocks during working hours
- Duration: 30-240 minutes

## Regenerating Data:

```bash
python scripts/generate_mock_crm_data.py --patients 200 --appointments 1000
```

## Usage in Tests:

```python
from app.integrations.crm.mock_client import MockCRMClient

client = MockCRMClient()
patients = client.fetch_patients()
appointments = client.fetch_appointments()
```

## Notes:

- All datetimes are in ISO 8601 format
- Persian text is properly encoded (UTF-8)
- Data is internally consistent (patient IDs match, dates are logical)
- `_meta` fields in patients are for testing only (not returned by adapter)
"""
    
    readme_path = output_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✓ Saved {readme_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate mock CRM data')
    parser.add_argument('--patients', type=int, default=200, help='Number of patients to generate')
    parser.add_argument('--appointments', type=int, default=1000, help='Number of appointments to generate')
    parser.add_argument('--output', type=str, default='data/mock', help='Output directory')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("Mock CRM Data Generator")
    print("="*60 + "\n")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate data
    patients = generate_patients(args.patients)
    appointments = generate_appointments(patients, args.appointments)
    payments = generate_payments(appointments)
    doctors = generate_doctors()
    schedules = generate_schedules(doctors)
    blocks = generate_blocks(doctors, schedules)
    
    # Save to JSON files
    print("\nSaving files...")
    save_json(patients, "patients.json", output_dir)
    save_json(appointments, "appointments.json", output_dir)
    save_json(payments, "payments.json", output_dir)
    save_json(doctors, "doctors.json", output_dir)
    save_json(schedules, "schedules.json", output_dir)
    save_json(blocks, "blocks.json", output_dir)
    
    # Generate README
    generate_readme(output_dir)
    
    print("\n" + "="*60)
    print("✓ Mock data generation complete!")
    print(f"  Patients: {len(patients)}")
    print(f"  Appointments: {len(appointments)}")
    print(f"  Payments: {len(payments)}")
    print(f"  Doctors: {len(doctors)}")
    print(f"  Schedules: {len(schedules)}")
    print(f"  Blocks: {len(blocks)}")
    print(f"\n  Output: {output_dir.absolute()}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
