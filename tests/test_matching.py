"""Test matching logic with improved normalization and fuzzy matching."""
import sys
import os
import logging

# Set UTF-8 encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Enable debug logging to see matching details
logging.basicConfig(level=logging.DEBUG)

from app.engine.run_engine import run

print("="*80)
print("TESTING IMPROVED MATCHING")
print("="*80)

# Test 1: Insurance matching
print("\n[TEST 1] Insurance Matching - 'ایران'")
print("-" * 80)
result = run({
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران',
})

print(f"\nFinancial score: {result['top_recommendations'][0]['breakdown']['financial']:.3f}")
if result['top_recommendations'][0]['breakdown']['financial'] > 0.5:
    print("✓ Insurance 'ایران' matched successfully!")
else:
    print("✗ Insurance 'ایران' not matched (still using default 0.5)")

# Test 2: Backlog matching
print("\n" + "="*80)
print("[TEST 2] Backlog Matching - 'درمان ریشه'")
print("-" * 80)
result = run({
    'service_name': 'کشیدن دندان',
    'backlog_title': 'درمان ریشه'
})

print(f"\nUrgency score: {result['top_recommendations'][0]['breakdown']['urgency']:.3f}")
if result['top_recommendations'][0]['breakdown']['urgency'] > 0.5:
    print("✓ Backlog 'درمان ریشه' matched successfully!")
else:
    print("✗ Backlog 'درمان ریشه' not matched (still using default 0.5)")

# Test 3: Combined matching
print("\n" + "="*80)
print("[TEST 3] Combined Matching")
print("-" * 80)
result = run({
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران',
    'backlog_title': 'درمان ریشه'
})

print(f"\nFinancial score: {result['top_recommendations'][0]['breakdown']['financial']:.3f}")
print(f"Urgency score: {result['top_recommendations'][0]['breakdown']['urgency']:.3f}")
print(f"Total score: {result['top_recommendations'][0]['score']:.3f}")

if (result['top_recommendations'][0]['breakdown']['financial'] > 0.5 and
    result['top_recommendations'][0]['breakdown']['urgency'] > 0.5):
    print("\n✓ BOTH matches working correctly!")
else:
    print("\n✗ One or both matches still failing")

print("\n" + "="*80)
