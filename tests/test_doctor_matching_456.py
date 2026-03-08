"""Test with patient 456 who prefers 'دکتر نعمتی' (who DOES exist in schedule)."""
import sys
import os
import logging
import pytest

# Set UTF-8 encoding
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul')
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# Enable INFO logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

from app.engine.run_engine import run_from_crm


def test_patient_456_preferred_doctor_matching():
    """Test that patient 456 with preferred doctor 'دکتر نعمتی' gets recommendations with fallback."""
    print("="*80)
    print("TESTING DOCTOR MATCHING - Patient 456")
    print("Patient 456 prefers 'دکتر نعمتی' (should exist in schedule)")
    print("="*80)
    
    result = run_from_crm('456', 'کشیدن دندان')
    
    print("\n[RESULTS]")
    print("-" * 80)
    
    # CRITICAL: Should NEVER return 0 recommendations (fallback should prevent this)
    assert result['success'], "Request should succeed"
    assert result['total_recommendations'] > 0, \
        "FAIL: No recommendations generated. Preferred doctor fallback should prevent empty list."
    
    print(f"✓ Recommendations: {result['total_recommendations']}")
    
    # Only proceed with detailed checks if we have recommendations
    if result['total_recommendations'] > 0:
        print("\nTop 5 recommendations:")
        for i, rec in enumerate(result['top_recommendations'][:5], 1):
            print(f"\n{i}. {rec['weekday']} {rec['shift_code']} {rec['time']} - {rec['doctor']}")
            print(f"   Score: {rec['score']:.3f} (availability: {rec['breakdown']['availability']:.3f})")
        
        # Check if نعمتی appears
        doctors = [r['doctor'] for r in result['top_recommendations']]
        has_nemati = any('نعمتی' in d for d in doctors)
        
        print("\n[ANALYSIS]")
        print("-" * 80)
        
        if has_nemati:
            print("✓ SUCCESS: Preferred doctor 'نعمتی' found in recommendations")
            
            # Check if boost was applied
            top_score = result['top_recommendations'][0]['score']
            if top_score > 0.94:  # Base score 0.935 + 0.15 boost would be > 1.0, capped at 1.0
                print("✓ SUCCESS: Preferred doctor boost appears to be applied")
            else:
                print(f"⚠ Note: Top score is {top_score:.3f} (expected boost to be applied)")
        else:
            print("⚠ WARNING: Preferred doctor 'نعمتی' not found (fallback mode active)")
        
        # Check availability scores (guard against division by zero)
        if len(result['top_recommendations']) > 0:
            avg_avail = sum(r['breakdown']['availability'] for r in result['top_recommendations']) / len(result['top_recommendations'])
            print(f"\nAverage availability score: {avg_avail:.3f}")
            
            if avg_avail >= 0.95:
                print("✓ SUCCESS: Availability scores are correct (≈1.0)")
            else:
                print(f"⚠ Note: Availability scores: {avg_avail:.3f} (expected ≈1.0)")
    
    print("\n" + "="*80)


# Allow running as standalone script for manual testing
if __name__ == "__main__":
    test_patient_456_preferred_doctor_matching()
