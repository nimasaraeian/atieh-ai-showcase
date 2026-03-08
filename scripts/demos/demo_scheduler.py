"""Demo script showing scheduler functionality."""
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.engine.run_engine import run
import json

print("="*80)
print("ATIEH SCHEDULING ENGINE - DRAFT BUILDER DEMO")
print("="*80)

# Example 1: Basic request
print("\n[EXAMPLE 1] Basic Service Request")
print("-" * 80)
result = run({
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران'
})

print(f"\n✓ Evaluated {result['total_slots_evaluated']} slots")
print(f"✓ Generated {result['total_recommendations']} recommendations")

if result['draft']:
    draft = result['draft']
    print(f"\n📋 SCHEDULE DRAFT:")
    print(f"   Date: {draft['weekday']} ({draft['shift_code']} shift)")
    print(f"   Time: {draft['time']}")
    print(f"   Doctor: {draft['doctor']}")
    print(f"   Score: {draft['score']:.3f}")
    print(f"   Reason: {draft['reason']}")

# Example 2: With preferred doctor
print("\n" + "="*80)
print("[EXAMPLE 2] With Preferred Doctor")
print("-" * 80)
result = run({
    'service_name': 'ترمیم',
    'preferred_doctor': 'نعمتی',
    'insurance_name': 'تامین اجتماعی'
})

if result['draft']:
    draft = result['draft']
    print(f"\n📋 SCHEDULE DRAFT:")
    print(f"   Date: {draft['weekday']} ({draft['shift_code']} shift)")
    print(f"   Time: {draft['time']}")
    print(f"   Doctor: {draft['doctor']}")
    print(f"   Score: {draft['score']:.3f}")
    print(f"   Reason: {draft['reason']}")

# Example 3: High urgency treatment
print("\n" + "="*80)
print("[EXAMPLE 3] High Urgency Treatment")
print("-" * 80)
result = run({
    'service_name': 'ایمپلنت',
    'backlog_title': 'جراحی',
    'insurance_name': 'ایران'
})

if result['draft']:
    draft = result['draft']
    print(f"\n📋 SCHEDULE DRAFT:")
    print(f"   Date: {draft['weekday']} ({draft['shift_code']} shift)")
    print(f"   Time: {draft['time']}")
    print(f"   Doctor: {draft['doctor']}")
    print(f"   Score: {draft['score']:.3f}")
    print(f"   Reason: {draft['reason']}")

print("\n" + "="*80)
print("OUTPUT FILES")
print("="*80)
print("✓ data/outputs/slot_recommendations.csv - All 10 recommendations")
print("✓ data/outputs/schedule_draft.csv - Single chosen slot with reasoning")
print("="*80)
