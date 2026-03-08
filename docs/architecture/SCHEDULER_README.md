# Schedule Draft Builder

## Overview

The schedule draft builder automatically selects the best appointment slot from recommendations and provides a clear explanation for the choice.

## Features

### Smart Selection Logic
1. **Preferred Doctor Filtering**: If a preferred doctor is specified, the system filters recommendations to that doctor first
2. **Best Score Selection**: Chooses the highest scoring slot from available options
3. **Fallback Strategy**: If preferred doctor not available, selects best overall slot
4. **Reasoning**: Generates human-readable explanation for the choice

### Output Format

#### ScheduleDraft Schema
```python
{
    "chosen_weekday": "شنبه",
    "shift_code": "D",
    "start_time": "09:00",
    "end_time": "09:30",
    "doctor": "دکتر احمدی",
    "score": 0.85,
    "reason": "Excellent match (score: 0.85); preferred doctor available; 
               doctor confirmed available; high urgency treatment; morning shift"
}
```

## Usage

### Automatic (via run_engine)
```python
from app.engine.run_engine import run

result = run({
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران',
    'preferred_doctor': 'دکتر احمدی'  # Optional
})

# Access draft
draft = result['draft']
print(f"Chosen slot: {draft['weekday']} {draft['time']}")
print(f"Reason: {draft['reason']}")
```

### Manual (direct API)
```python
from app.engine.recommender import recommend_slots
from app.engine.scheduler import build_and_save_draft
from app.engine.scoring import DataStore
from app.schemas.scheduling import SchedulingRequest

# Load data and generate recommendations
data_store = DataStore()
data_store.load_from_csv()

request = SchedulingRequest(
    service_name='کشیدن دندان',
    preferred_doctor='دکتر احمدی'
)

result = recommend_slots(request, data_store)

# Build draft
draft = build_and_save_draft(
    result.top_recommendations,
    request,
    "data/outputs/schedule_draft.csv"
)
```

## Reasoning System

The draft builder generates contextual reasons based on multiple factors:

### Score Quality
- **score ≥ 0.8**: "Excellent match"
- **score ≥ 0.6**: "Good match"  
- **score < 0.6**: "Best available"

### Doctor Preference
- **Preferred doctor available**: "preferred doctor available"
- **Not available**: "preferred doctor not available, selected from N options"

### Availability
- **availability_score = 1.0**: "doctor confirmed available"

### Urgency
- **urgency_score ≥ 0.8**: "high urgency treatment"

### Financial Priority
- **financial_score ≥ 0.8**: "priority insurance"

### Shift Timing
- **D shift**: "morning shift"
- **E shift**: "evening shift"
- **N shift**: "night shift"

### Complexity Consideration
- **complexity > 0.8 and shift ≠ N**: "complex procedure scheduled in optimal shift"

## Example Reasons

### Example 1: High Score with Preferences Met
```
Excellent match (score: 0.87); preferred doctor available; 
doctor confirmed available; high urgency treatment; 
priority insurance; morning shift
```

### Example 2: Good Score, Preferred Doctor Not Available
```
Good match (score: 0.68); preferred doctor not available, 
selected from 10 options; doctor confirmed available; 
evening shift
```

### Example 3: Complex Procedure
```
Good match (score: 0.72); doctor confirmed available; 
complex procedure scheduled in optimal shift; morning shift
```

## Output Files

### schedule_draft.csv
**Location**: `data/outputs/schedule_draft.csv`

**Format**:
```csv
chosen_weekday,shift_code,start_time,end_time,doctor,score,reason
شنبه,D,09:00,09:30,دکتر احمدی,0.850,"Excellent match (score: 0.85); preferred doctor available; doctor confirmed available; morning shift"
```

**Characteristics**:
- Single row (one draft per request)
- UTF-8 with BOM encoding (Excel-compatible)
- Comma-separated values
- Quoted reason field (may contain commas)

## Integration with run_engine

The `run()` function now returns both recommendations and draft:

```python
result = {
    'success': True,
    'total_recommendations': 10,
    'total_slots_evaluated': 224,
    'generated_at': '2026-02-03T12:00:00',
    'top_recommendations': [...],  # All recommendations
    'draft': {                     # Single best choice
        'weekday': 'شنبه',
        'shift_code': 'D',
        'time': '09:00-09:30',
        'doctor': 'دکتر احمدی',
        'score': 0.85,
        'reason': '...'
    }
}
```

## CSV Files Generated

When you run the engine, it now generates **TWO** CSV files:

1. **slot_recommendations.csv** - All top 10 recommendations with detailed scores
2. **schedule_draft.csv** - Single chosen slot with reasoning

## Preferred Doctor Behavior

### Scenario 1: Preferred Doctor Available
```python
request = SchedulingRequest(
    service_name='ترمیم',
    preferred_doctor='دکتر احمدی'
)
# Result: Selects highest scoring slot with Dr. Ahmadi
# Reason includes: "preferred doctor available"
```

### Scenario 2: Preferred Doctor Not Available
```python
request = SchedulingRequest(
    service_name='ترمیم',
    preferred_doctor='دکتر غیر موجود'  # Non-existent doctor
)
# Result: Selects highest scoring slot from all doctors
# Reason includes: "preferred doctor not available, selected from 10 options"
```

### Scenario 3: No Preference
```python
request = SchedulingRequest(
    service_name='ترمیم'
)
# Result: Selects highest scoring slot regardless of doctor
# Reason does not mention doctor preference
```

## Testing

### Run Complete Flow Test
```bash
python test_complete_flow.py
```

Tests verify:
- ✅ Draft is created
- ✅ Reason is provided
- ✅ Preferred doctor filtering works
- ✅ CSV files are generated
- ✅ Score ranges are valid
- ✅ All required fields present

### Run Unit Tests
```bash
pytest tests/test_scoring.py -v
```

All original tests still pass (10/10).

## API Reference

### build_schedule_draft()
```python
def build_schedule_draft(
    recommendations: List[SlotRecommendation],
    request: SchedulingRequest
) -> Optional[ScheduleDraft]
```

Builds a schedule draft from recommendations.

**Returns**: `ScheduleDraft` or `None` if no recommendations

### save_draft_to_csv()
```python
def save_draft_to_csv(
    draft: ScheduleDraft,
    output_path: str
)
```

Saves draft to CSV file.

### build_and_save_draft()
```python
def build_and_save_draft(
    recommendations: List[SlotRecommendation],
    request: SchedulingRequest,
    output_path: str = "data/outputs/schedule_draft.csv"
) -> Optional[ScheduleDraft]
```

Convenience function that builds draft and saves to CSV in one step.

## Error Handling

- **No recommendations**: Returns `None`, logs warning, no CSV created
- **Preferred doctor not found**: Falls back to all recommendations, logs warning
- **Empty recommendation list**: Returns `None`, logs warning

## Future Enhancements

1. Multiple draft options (top 3 choices)
2. Alternative draft if first choice unavailable
3. Conflict detection with existing appointments
4. Patient preference history
5. Seasonal/holiday considerations
6. Room and equipment availability
7. Multi-appointment series

---

**Status**: ✅ Production Ready
**Integration**: Complete with run_engine
**Tests**: All Passing
**Date**: February 3, 2026
