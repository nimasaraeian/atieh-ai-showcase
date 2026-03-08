# Quick Start: Decision Engine V2

## Enable V2

**Method 1: Environment Variable (Recommended for testing)**
```bash
# Windows
set ENGINE_VERSION=v2
python your_script.py

# Linux/Mac
export ENGINE_VERSION=v2
python your_script.py
```

**Method 2: Config File**
```python
# app/config.py line 56
ENGINE_VERSION = "v2"  # Change from "v1" to "v2"
```

**Method 3: Runtime**
```python
from app.engine.recommender import recommend_slots

result = recommend_slots(
    request=request,
    data_store=data_store,
    engine_version="v2"  # Explicitly use v2
)
```

## Basic Example

```python
from app.engine.recommender import recommend_slots
from app.engine.scoring import DataStore
from app.schemas.scheduling import SchedulingRequest

# Load data
data_store = DataStore()
data_store.load_from_csv("data/outputs")

# Create request (v1 format still works)
request = SchedulingRequest(
    service_name='کشیدن دندان',
    preferred_doctor='دکتر احمدی',
    insurance_name='ایران',
    backlog_title='درمان ریشه'
)

# Get recommendations with v2
result = recommend_slots(
    request=request,
    data_store=data_store,
    top_n=5,
    engine_version="v2"
)

# Use results (v1 compatible)
for i, rec in enumerate(result.top_recommendations, 1):
    print(f"{i}. {rec.weekday} {rec.shift_code} {rec.start_time}-{rec.end_time}")
    print(f"   Doctor: {rec.doctor}")
    print(f"   Score: {rec.score:.3f}")
    
    # Access v2 trace if available
    if '_v2_trace' in rec.__dict__:
        trace = rec.__dict__['_v2_trace']
        print(f"   Patient TVS: {trace['patient_tvs']:.3f}")
        print(f"   CIS: {trace['cis']:.3f}, LTVS: {trace['ltvs']:.3f}, RISK: {trace['risk']:.3f}")
```

## Advanced: Direct V2 Usage (Full Trace)

```python
from app.engine.tvs.allocator import recommend_slots_v2
from app.engine.time_blocks import generate_all_slots
from app.engine.scoring import DataStore
from app.config import weights_config

# Load data
data_store = DataStore()
data_store.load_from_csv("data/outputs")

# Generate slots
slots = generate_all_slots(slot_minutes=30)

# Request with patient data
request_params = {
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران',
    'backlog_title': 'درمان ریشه',
    
    # Patient history for better LTVS
    'visit_count': 5,
    'total_revenue': 10_000_000,
    'adherence_rate': 0.9,
    
    # Risk factors
    'no_show_risk': 0.1,
    'late_payment_risk': 0.05,
    
    # Queue fairness
    'queue_days': 7
}

# Get v2 recommendations
result = recommend_slots_v2(
    slots=slots,
    request_params=request_params,
    data_store=data_store,
    top_k=5,
    weights_config=weights_config.get_v2_weights()
)

# Full trace available
for rec in result['recommendations']:
    print(f"\nRank {rec.rank}: {rec.slot['weekday']} {rec.slot['start_time']}")
    print(f"Final Score: {rec.final_score:.3f}")
    print(f"Patient TVS: {rec.patient_tvs:.3f} (70% weight)")
    print(f"Slot Fit: {rec.slot_fit_score:.3f} (30% weight)")
    
    # Component breakdown
    t = rec.trace
    print(f"\nPatient Components:")
    print(f"  CIS (Cash Impact): {t.cis:.3f}")
    print(f"    → {t.cis_notes}")
    print(f"  LTVS (Lifetime Value): {t.ltvs:.3f}")
    print(f"    → {t.ltvs_notes}")
    print(f"  RISK: {t.risk:.3f}")
    print(f"    → {t.risk_notes}")
    print(f"  FAIR (Fairness): {t.fair:.3f}")
    print(f"    → {t.fair_notes}")
    print(f"  URG (Urgency): {t.urg:.3f}")
    print(f"    → {t.urg_notes}")
    
    print(f"\nSlot Components:")
    print(f"  Urgency: {t.slot_urgency:.3f}")
    print(f"  Financial: {t.slot_financial:.3f}")
    print(f"  Availability: {t.slot_availability:.3f}")
    print(f"  Complexity Fit: {t.slot_complexity_fit:.3f}")
```

## Tuning Weights

Edit `config/weights.yaml`:

```yaml
# Prioritize immediate revenue
tvs:
  alpha: 0.70    # ↑ Cash Impact
  beta: 0.20     # ↓ Lifetime Value
  
# Or prioritize patient fairness
tvs:
  epsilon: 0.40  # ↑ Fairness (waiting time)
  alpha: 0.40    # ↓ Cash Impact

# Balance patient vs slot constraints
final:
  patient_weight: 0.50   # Equal weight
  slot_weight: 0.50
```

## Run Tests

```bash
# Test all components are in [0, 1]
pytest tests/test_tvs_components_in_range.py -v

# Test v2 includes trace
pytest tests/test_v2_has_trace.py -v

# Test v1 unchanged
pytest tests/test_v1_unchanged.py -v

# Run all
pytest tests/test_*.py -v
```

## Switch Back to V1

```python
# Method 1: Environment
set ENGINE_VERSION=v1

# Method 2: Config
Config.ENGINE_VERSION = "v1"

# Method 3: Runtime
result = recommend_slots(request, data_store, engine_version="v1")
```

## Troubleshooting

**Q: Scores all around 0.5?**
A: V2 needs patient data. Add `visit_count`, `total_revenue`, `queue_days` to request_params.

**Q: Results same as V1?**
A: Check `ENGINE_VERSION` is set to "v2". Default is "v1".

**Q: No trace in results?**
A: Either use `recommend_slots_v2()` directly, or check `rec.__dict__['_v2_trace']` when using main recommender.

## Documentation

- **Full Documentation:** `ENGINE_V2_DECISION_LOGIC.md`
- **Implementation Summary:** `IMPLEMENTATION_SUMMARY.md`
- **Code:** `app/engine/tvs/`

## Status

✅ **Production Ready** with V1 fallback
- Default: V1 (safe, unchanged)
- V2: Opt-in via feature flag
- Fully backward compatible
