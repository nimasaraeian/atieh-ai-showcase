#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
تست نمایش صحیح متن فارسی در API
"""
import sys
import io
import requests
import json

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Call API
print("🔄 Calling /ai/recommend-slot...")
response = requests.post(
    "http://127.0.0.1:8000/ai/recommend-slot",
    params={
        "patient_id": "1",
        "service_id": "TREATMENT_1",
        "days_ahead": 30,
        "max_slots": 3
    }
)

print(f"✅ Status: {response.status_code}\n")

# Parse JSON
data = response.json()

# Display with correct Persian
print("=" * 60)
print("نتایج به فارسی:")
print("=" * 60)

print(f"\nبیمار: {data['patient_id']}")
print(f"سرویس: {data['service_id']}")
print(f"امتیاز ارزش: {data['explain']['value_score']}")

print(f"\n{'─' * 60}")
print("نوبت‌های پیشنهادی:")
print('─' * 60)

for i, slot in enumerate(data['recommended_slots'], 1):
    print(f"\n🕐 نوبت {i}:")
    print(f"   زمان شروع: {slot['start_datetime']}")
    print(f"   دکتر: {slot['doctor_name']} ({slot['doctor_id']})")
    print(f"   اطمینان: {slot['confidence']}")
    print(f"   دلایل: {', '.join(slot['reason_codes'])}")

print("\n" + "=" * 60)
print("✅ متن فارسی به درستی نمایش داده شد!")
print("=" * 60)

# Also save to file
with open('api_response_correct.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\n📄 همچنین ذخیره شد در: api_response_correct.json")
