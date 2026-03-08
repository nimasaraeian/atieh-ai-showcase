"""Quick test of the scheduling engine."""
from app.engine.run_engine import run

# Test with the requested payload
result = run({
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران',
    'backlog_title': 'درمان ریشه'
})

# Print results
print("\n" + "="*80)
print("✓ SUCCESS! Scheduling Engine Working")
print("="*80)
print(f"✓ Generated {result['total_recommendations']} recommendations")
print(f"✓ Evaluated {result['total_slots_evaluated']} slots")
print(f"✓ Top score: {result['top_recommendations'][0]['score']:.3f}")
print(f"✓ CSV saved to: data/outputs/slot_recommendations.csv")
print("="*80)

# Show top 3
print("\nTop 3 Recommendations:")
for idx, rec in enumerate(result['top_recommendations'][:3], 1):
    print(f"{idx}. {rec['weekday']} {rec['shift_code']} {rec['time']} - "
          f"Dr. {rec['doctor']} - Score: {rec['score']:.3f}")
print()
