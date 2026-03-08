# Decision Engine V2: Value-Based Scheduling (TVS)

## Overview

Decision Engine V2 implements **Value-Based Scheduling** by combining **Patient Total Value Score (TVS)** with **Slot Fit Score** to optimize scheduling decisions. This approach prioritizes patients based on their total value to the practice while maintaining slot compatibility.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Engine V2 Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Compute Patient TVS (once per request)                  │
│     ├─ CIS  (Cash Impact Score)                             │
│     ├─ LTVS (Lifetime Value Score)                          │
│     ├─ RISK (Risk Score)                                    │
│     ├─ FAIR (Fairness Score)                                │
│     └─ URG  (Urgency Score)                                 │
│                                                              │
│  2. For each slot: Compute Slot Fit Score (from V1)        │
│     ├─ Urgency score                                        │
│     ├─ Financial score (insurance)                          │
│     ├─ Availability score                                   │
│     └─ Complexity fit score                                 │
│                                                              │
│  3. Combine: Final Score = f(Patient TVS, Slot Fit)        │
│                                                              │
│  4. Rank slots by Final Score → Return top K with trace    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Core Formulas

### 1. Patient Total Value Score (TVS)

Computed once per scheduling request:

```
patient_tvs = clamp01(
    α × CIS +        # Cash Impact (revenue potential)
    β × LTVS +       # Lifetime Value (loyalty)
    -γ × RISK +      # Risk (negative impact)
    ε × FAIR +       # Fairness (waiting time)
    δ × URG          # Urgency (medical priority)
)
```

**Default weights:**
- α (alpha) = 0.55
- β (beta) = 0.35
- γ (gamma) = 0.25 (negative)
- ε (epsilon) = 0.20
- δ (delta) = 0.10

All components are in [0, 1] range.

### 2. Component Definitions

#### CIS (Cash Impact Score)
Measures revenue potential from the patient:
- Service price/revenue (log-normalized)
- Insurance priority score (from `insurance_priority.csv`)
- Payment type (cash=1.0, insurance=0.85-0.9)
- Collection probability heuristic

**Formula:**
```
CIS = clamp01(
    mean(price_score, insurance_priority) × payment_multiplier
)
```

#### LTVS (Lifetime Value Score)
Measures patient loyalty and historical value:
- Visit count (log-normalized: 1 visit=0.2, 20+ visits≈0.9)
- Total revenue from patient (log-normalized)
- Adherence/completion rate
- Cancellation rate (inverse penalty)

**Formula:**
```
LTVS = clamp01(
    mean(visit_score, revenue_score, adherence, 1-cancel_rate)
)
```

If no history available: LTVS = 0.5 (default for new patients)

#### RISK (Risk Score)
Measures financial and operational risk:
- No-show risk
- Late payment risk
- Open debt flag

**Formula:**
```
RISK = clamp01(
    mean(no_show_risk, late_payment_risk, debt_penalty)
)
```

Default: RISK = 0.25 (conservative for unknown patients)

#### FAIR (Fairness Score)
Rewards patients waiting longer in queue:
- Queue days or waiting days

**Formula:**
```
FAIR = log_normalize(queue_days, scale=20)
```

Scale: 1 day=0.1, 7 days=0.5, 30+ days≈0.9

#### URG (Urgency Score)
Medical urgency based on treatment type:
- Reuses V1's `calculate_urgency_score()`
- Matches `backlog_title` against `unfinished_treatments.csv`
- Returns `urgency_weight` from catalog

Default: URG = 0.5 if no match

### 3. Slot Fit Score

Wraps V1's existing `score_slot()` function:

```
slot_fit = 0.35 × urgency +
           0.30 × financial +
           0.20 × availability +
           0.15 × complexity_fit
```

All in [0, 1] range (unchanged from V1).

### 4. Final Score

Combines Patient TVS with Slot Fit Score:

**Weighted mode (default):**
```
final_score = clamp01(
    patient_weight × patient_tvs +
    slot_weight × slot_fit_score
)
```

**Default weights:**
- patient_weight = 0.70
- slot_weight = 0.30

**Alternative multiplicative mode:**
```
final_score = patient_tvs × slot_fit_score
```

## Configuration

### YAML Configuration (`config/weights.yaml`)

```yaml
# TVS Component Weights
tvs:
  alpha: 0.55      # CIS weight
  beta: 0.35       # LTVS weight
  gamma: 0.25      # RISK weight (negative)
  epsilon: 0.20    # FAIR weight
  delta: 0.10      # URG weight

# Final Score Weights
final:
  patient_weight: 0.70   # Patient TVS weight (70%)
  slot_weight: 0.30      # Slot Fit weight (30%)
```

### Environment/Code Configuration

**Enable V2:**
```python
# In app/config.py
Config.ENGINE_VERSION = "v2"

# Or via environment variable
os.environ['ENGINE_VERSION'] = "v2"
```

**Default:** `ENGINE_VERSION = "v1"` (backward compatible)

## Decision Trace

V2 provides full explainability through decision traces:

```python
trace = {
    # Patient Value Components
    'cis': 0.82,
    'cis_notes': 'service_price=5000000 -> price_score=0.71 | insurance_priority=0.9 (ایران) | ...',
    'ltvs': 0.65,
    'ltvs_notes': 'visit_count=5 -> visit_score=0.58 | total_revenue=10000000 -> revenue_score=0.72',
    'risk': 0.15,
    'risk_notes': 'no_show_risk=0.1 | late_payment_risk=0.05 | RISK=0.15',
    'fair': 0.40,
    'fair_notes': 'queue_days=7 -> FAIR=0.40',
    'urg': 0.70,
    'urg_notes': "backlog_title='درمان ریشه' -> URG=0.70",
    
    'patient_tvs': 0.68,
    
    # Slot Fit Components (from V1)
    'slot_fit_score': 0.72,
    'slot_urgency': 0.70,
    'slot_financial': 0.90,
    'slot_availability': 1.0,
    'slot_complexity_fit': 0.80,
    
    # Final Score
    'final_score': 0.692,  # = 0.70 × 0.68 + 0.30 × 0.72
    'patient_weight': 0.70,
    'slot_weight': 0.30,
    
    'engine_version': 'v2'
}
```

## API Usage

### Using V2 Directly

```python
from app.engine.tvs.allocator import recommend_slots_v2
from app.engine.scoring import DataStore
from app.config import weights_config

# Load data
data_store = DataStore()
data_store.load_from_csv("data/outputs")

# Request parameters
request_params = {
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران',
    'backlog_title': 'درمان ریشه',
    'visit_count': 5,
    'total_revenue': 10_000_000,
    'no_show_risk': 0.1,
    'queue_days': 7
}

# Get recommendations
result = recommend_slots_v2(
    slots=candidate_slots,
    request_params=request_params,
    data_store=data_store,
    top_k=5,
    weights_config=weights_config.get_v2_weights()
)

# Access recommendations
for rec in result['recommendations']:
    print(f"Rank {rec.rank}: Score={rec.final_score:.3f}")
    print(f"  Patient TVS={rec.patient_tvs:.3f}")
    print(f"  Slot Fit={rec.slot_fit_score:.3f}")
    print(f"  Trace: CIS={rec.trace.cis:.3f}, LTVS={rec.trace.ltvs:.3f}")
```

### Using Through Main Recommender (with V1 Compatibility)

```python
from app.engine.recommender import recommend_slots
from app.schemas.scheduling import SchedulingRequest

request = SchedulingRequest(
    service_name='کشیدن دندان',
    insurance_name='ایران',
    # ... other fields
)

# Force V2
result = recommend_slots(
    request=request,
    data_store=data_store,
    top_n=5,
    engine_version="v2"
)

# Result is V1-compatible SchedulingResult
# but internal scoring uses V2
for rec in result.top_recommendations:
    print(f"Score: {rec.score:.3f}")
    # V2 trace available in __dict__ if needed
    if '_v2_trace' in rec.__dict__:
        print(f"  Patient TVS: {rec.__dict__['_v2_trace']['patient_tvs']:.3f}")
```

## Backward Compatibility

V2 maintains full backward compatibility with V1:

1. **API Outputs:** V1 clients see identical response structure
2. **Default Behavior:** `ENGINE_VERSION="v1"` by default
3. **Score Fields:** V1's `total_score` remains; V2 uses `final_score` internally
4. **Breakdown:** V1 breakdown fields preserved in V2 responses
5. **No Breaking Changes:** Existing code continues to work without modification

## Testing

Three test suites verify correctness:

### 1. Component Range Tests (`test_tvs_components_in_range.py`)
Validates all scores in [0, 1]:
```bash
pytest tests/test_tvs_components_in_range.py -v
```

### 2. Trace Presence Tests (`test_v2_has_trace.py`)
Ensures V2 includes full decision trace:
```bash
pytest tests/test_v2_has_trace.py -v
```

### 3. V1 Unchanged Tests (`test_v1_unchanged.py`)
Verifies V1 behavior unchanged:
```bash
pytest tests/test_v1_unchanged.py -v
```

## Performance Characteristics

- **Patient TVS:** Computed once per request (O(1) per request)
- **Slot Fit:** Computed per slot (O(N) for N slots)
- **Total Complexity:** O(N) + sort = O(N log N)

Same complexity as V1, with minimal overhead (~5-10% additional computation).

## Migration Path

### Phase 1: Testing (Current)
- V1 remains default
- V2 available via explicit flag
- Side-by-side comparison

### Phase 2: Gradual Rollout
- A/B testing with select patients
- Monitor metrics: revenue per slot, no-show rates, patient satisfaction
- Adjust weights based on outcomes

### Phase 3: V2 Default
- Switch `Config.ENGINE_VERSION = "v2"`
- Keep V1 available as fallback
- Continue monitoring

### Phase 4: V1 Deprecation
- Remove V1 code path (optional, after extended V2 validation)
- Keep V1 tests as regression suite

## Tuning Guidelines

### Increase Revenue Focus
```yaml
tvs:
  alpha: 0.70    # ↑ CIS weight
  beta: 0.20     # ↓ LTVS weight
```

### Increase Patient Fairness
```yaml
tvs:
  epsilon: 0.35  # ↑ FAIR weight
  alpha: 0.45    # ↓ CIS weight
```

### Prioritize Urgency
```yaml
tvs:
  delta: 0.25    # ↑ URG weight
  beta: 0.20     # ↓ LTVS weight
```

### Balance Patient vs Slot Constraints
```yaml
final:
  patient_weight: 0.50   # Equal weight
  slot_weight: 0.50
```

## Troubleshooting

### Issue: All scores near 0.5
**Cause:** Missing patient data (defaults to 0.5)
**Solution:** Ensure request includes `visit_count`, `total_revenue`, `queue_days`

### Issue: V2 scores identical to V1
**Cause:** `ENGINE_VERSION` not set to "v2"
**Solution:** Check `Config.ENGINE_VERSION` or `os.environ['ENGINE_VERSION']`

### Issue: No trace in response
**Cause:** Using V1 mode
**Solution:** Set `engine_version="v2"` explicitly

### Issue: Scores out of range
**Cause:** Invalid input data (negative values, etc.)
**Solution:** Validate inputs; check `clamp01()` applied correctly

## References

- **V1 Scoring:** `app/engine/scoring.py` - `score_slot()`
- **V2 TVS Module:** `app/engine/tvs/`
- **Config:** `config/weights.yaml`, `app/config.py`
- **Tests:** `tests/test_tvs_*.py`, `tests/test_v1_unchanged.py`

## Contact

For questions or tuning assistance, refer to:
- Implementation: `app/engine/tvs/`
- Configuration: `config/weights.yaml`
- Documentation: This file

---

**Version:** 2.0.0  
**Last Updated:** 2026-02-22  
**Status:** Production-ready with V1 fallback
