"""Test the complete scheduling flow with draft builder."""
import json
from pathlib import Path
from app.engine.run_engine import run

print("="*80)
print("TESTING COMPLETE SCHEDULING FLOW")
print("="*80)

# Test 1: Basic request
print("\n[TEST 1] Basic service request")
result = run({
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران'
})

assert result['success'], "Request failed"
assert result['total_recommendations'] > 0, "No recommendations generated"
assert result['draft'] is not None, "No draft created"
print(f"✓ Generated {result['total_recommendations']} recommendations")
print(f"✓ Draft created: {result['draft']['weekday']} {result['draft']['shift_code']} {result['draft']['time']}")
print(f"✓ Draft reason: {result['draft']['reason']}")

# Test 2: Preferred doctor request
print("\n[TEST 2] With preferred doctor")
result = run({
    'service_name': 'ترمیم',
    'preferred_doctor': 'نعمتی'
})

assert result['draft'] is not None, "No draft with preferred doctor"
assert 'نعمتی' in result['draft']['doctor'], "Preferred doctor not selected"
print(f"✓ Preferred doctor selected: {result['draft']['doctor']}")
print(f"✓ Draft reason mentions preference: {'preferred' in result['draft']['reason'].lower()}")

# Test 3: Verify CSV files exist
print("\n[TEST 3] Verify CSV outputs")
recommendations_csv = Path("data/outputs/slot_recommendations.csv")
draft_csv = Path("data/outputs/schedule_draft.csv")

assert recommendations_csv.exists(), "slot_recommendations.csv not created"
assert draft_csv.exists(), "schedule_draft.csv not created"
print(f"✓ slot_recommendations.csv exists ({recommendations_csv.stat().st_size} bytes)")
print(f"✓ schedule_draft.csv exists ({draft_csv.stat().st_size} bytes)")

# Test 4: Read and validate draft CSV
print("\n[TEST 4] Validate draft CSV content")
import csv
with open(draft_csv, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
assert len(rows) == 1, f"Expected 1 draft row, got {len(rows)}"
draft_row = rows[0]

required_columns = ['chosen_weekday', 'shift_code', 'start_time', 'end_time', 'doctor', 'score', 'reason']
for col in required_columns:
    assert col in draft_row, f"Missing column: {col}"
    assert draft_row[col], f"Empty value in column: {col}"

print(f"✓ Draft CSV has all required columns")
print(f"✓ Draft details: {draft_row['chosen_weekday']} {draft_row['shift_code']} "
      f"{draft_row['start_time']}-{draft_row['end_time']}")
print(f"✓ Doctor: {draft_row['doctor']}")
print(f"✓ Score: {draft_row['score']}")

# Test 5: Validate scores in result
print("\n[TEST 5] Validate score ranges")
result = run({'service_name': 'جرمگیری'})

for rec in result['top_recommendations']:
    assert 0.0 <= rec['score'] <= 1.0, f"Score {rec['score']} out of range"
    for key, value in rec['breakdown'].items():
        assert 0.0 <= value <= 1.0, f"{key} score {value} out of range"

assert 0.0 <= result['draft']['score'] <= 1.0, "Draft score out of range"
print(f"✓ All recommendation scores in valid range (0-1)")
print(f"✓ Draft score in valid range: {result['draft']['score']}")

print("\n" + "="*80)
print("ALL TESTS PASSED ✓")
print("="*80)
print("\nSummary:")
print(f"- Recommendations generated: ✓")
print(f"- Draft created with reasoning: ✓")
print(f"- Preferred doctor filtering: ✓")
print(f"- CSV files created: ✓")
print(f"- Score validation: ✓")
