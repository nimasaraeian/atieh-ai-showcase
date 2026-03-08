"""Test improved doctor matching and availability scoring."""
import sys
import os
import logging

# Set UTF-8 encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Enable INFO and WARNING logging to see the improvements
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

from app.engine.run_engine import run_from_crm

print("="*80)
print("TESTING IMPROVED DOCTOR MATCHING & AVAILABILITY SCORING")
print("="*80)

print("\n[TEST] Patient 123 with preferred doctor 'دکتر احمدی'")
print("-" * 80)

result = run_from_crm('123', 'کشیدن دندان')

print("\n[RESULTS]")
print("-" * 80)

if result['success']:
    print(f"✓ Total recommendations: {result['total_recommendations']}")
    
    print("\nTop 5 recommendations:")
    for i, rec in enumerate(result['top_recommendations'][:5], 1):
        print(f"\n{i}. {rec['weekday']} {rec['shift_code']} {rec['time']}")
        print(f"   Doctor: {rec['doctor']}")
        print(f"   Total score: {rec['score']:.3f}")
        print(f"   Breakdown:")
        print(f"     - Urgency:      {rec['breakdown']['urgency']:.3f}")
        print(f"     - Financial:    {rec['breakdown']['financial']:.3f}")
        print(f"     - Availability: {rec['breakdown']['availability']:.3f}")
        print(f"     - Complexity:   {rec['breakdown']['complexity_fit']:.3f}")
    
    # Check availability scores
    availability_scores = [r['breakdown']['availability'] for r in result['top_recommendations']]
    avg_availability = sum(availability_scores) / len(availability_scores)
    
    print("\n[ANALYSIS]")
    print("-" * 80)
    print(f"Average availability score: {avg_availability:.3f}")
    
    if avg_availability < 0.9:
        print("✗ ISSUE: Availability scores are too low (should be 1.0 for valid slots)")
    else:
        print("✓ GOOD: Availability scores are correct (1.0 for valid doctor slots)")
    
    # Check if preferred doctor appears
    doctors = [r['doctor'] for r in result['top_recommendations']]
    has_ahmadi = any('احمدی' in d for d in doctors)
    
    if has_ahmadi:
        print(f"✓ GOOD: Preferred doctor found in recommendations")
    else:
        print(f"⚠ NOTE: Preferred doctor not found (check logs for candidates)")
    
    print("\n[SCORE COMPARISON]")
    print("-" * 80)
    print("Before fixes (expected):")
    print("  - Availability: 0.5 (incorrect penalty for non-preferred doctor)")
    print("  - No doctor boost applied")
    print("\nAfter fixes (expected):")
    print("  - Availability: 1.0 (correct - any doctor available)")
    print("  - Preferred doctor boost: +0.15 applied to matching slots")
    
else:
    print(f"✗ FAILED: {result.get('error', 'Unknown error')}")

print("\n" + "="*80)
