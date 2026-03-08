# CRM-Ready Scheduling Engine - Integration Guide

## Overview

The Atieh scheduling engine has been refactored to be **CRM-ready**, with a clean separation between the scheduling logic and data sources. The engine now accepts a unified `CaseContext` object that can be populated from any CRM system.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   CRM System                         │
│            (Patient DB, Appointments, etc)           │
└─────────────────┬───────────────────────────────────┘
                  │
        ┌─────────▼──────────┐
        │   CRM Adapter      │  ← Bridges CRM to Engine
        │  (adapter.py)      │
        └─────────┬──────────┘
                  │
        ┌─────────▼──────────┐
        │   CaseContext      │  ← Normalized data model
        │  (PatientContext + │
        │  SchedulingRequest)│
        └─────────┬──────────┘
                  │
        ┌─────────▼──────────┐
        │ Scheduling Engine  │  ← Core decision logic
        │   (recommender)    │
        └─────────┬──────────┘
                  │
        ┌─────────▼──────────┐
        │    Results         │
        │ (Recommendations + │
        │  Draft Schedule)   │
        └────────────────────┘
```

## Key Components

### 1. Data Models (app/schemas/scheduling.py)

#### PatientContext
```python
PatientContext(
    patient_id="123",                           # Unique ID
    full_name="علی احمدی",                      # Patient name
    phone="09121234567",                        # Contact
    insurance_name="ایران",                     # Insurance
    payment_behavior_tag="good",                # Payment history
    unfinished_treatment_title="درمان ریشه",   # Pending treatments
    preferred_doctor="دکتر احمدی",              # Preferences
    preferred_weekday="شنبه",
    notes="Additional notes"
)
```

#### SchedulingRequest
```python
SchedulingRequest(
    service_name="کشیدن دندان",     # Required service
    desired_weekday="شنبه",          # Optional preference
    preferred_doctor="دکتر احمدی",   # Optional preference
    slot_minutes=30                  # Slot duration
)
```

#### CaseContext (Combined)
```python
CaseContext(
    patient=PatientContext(...),
    request=SchedulingRequest(...)
)
```

### 2. CRM Integration Layer (app/integrations/crm/)

#### CRMClient (client.py)
Interface definition for CRM integration. Methods include:
- `get_patient(patient_id)` - Basic patient info
- `get_patient_insurance(patient_id)` - Insurance details
- `get_patient_unfinished(patient_id)` - Pending treatments
- `get_patient_preferences(patient_id)` - Scheduling preferences
- `get_existing_appointments(date_range)` - Booked appointments
- `get_payment_behavior(patient_id)` - Payment reliability

**Status**: Interface defined with TODOs. Ready for implementation when CRM API details are available.

#### MockCRMClient (mock.py)
Test implementation with sample data:
- Patient 123: علی احمدی (ایران insurance, درمان ریشه unfinished)
- Patient 456: فاطمه محمدی (تامین اجتماعی insurance, multiple unfinished)
- Patient 789: محمد رضایی (no insurance, no unfinished)

#### CRM Adapter (adapter.py)
```python
build_case_context_from_crm(
    crm_client,
    patient_id="123",
    service_name="کشیدن دندان",
    desired_weekday=None,
    preferred_doctor=None
) -> CaseContext
```

Fetches data from CRM and constructs normalized CaseContext.

### 3. Engine Entry Points (app/engine/run_engine.py)

#### run_case(case_context, data_store=None)
**Direct engine execution** with CaseContext:
```python
from app.schemas.scheduling import PatientContext, SchedulingRequest, CaseContext
from app.engine.run_engine import run_case

patient = PatientContext(patient_id="123", ...)
request = SchedulingRequest(service_name="کشیدن دندان")
case_context = CaseContext(patient=patient, request=request)

result = run_case(case_context)
```

#### run_from_crm(patient_id, service_name, ...)
**CRM-integrated execution**:
```python
from app.engine.run_engine import run_from_crm

result = run_from_crm(
    patient_id="123",
    service_name="کشیدن دندان",
    desired_weekday="شنبه",      # Optional
    preferred_doctor="نعمتی",     # Optional
    use_mock=True                 # True for testing, False for real CRM
)
```

#### run(payload)
**Legacy entry point** (backward compatible):
```python
result = run({
    'service_name': 'کشیدن دندان',
    'insurance_name': 'ایران',
    'backlog_title': 'درمان ریشه'
})
```

## Usage Examples

### Example 1: Using Mock CRM (Testing)
```python
from app.engine.run_engine import run_from_crm

# Uses MockCRMClient automatically
result = run_from_crm(
    patient_id="123",
    service_name="کشیدن دندان",
    use_mock=True
)

print(f"Patient: {result['patient_name']}")
print(f"Recommendations: {result['total_recommendations']}")
print(f"Best slot: {result['draft']}")
```

### Example 2: Building CaseContext Manually
```python
from app.schemas.scheduling import PatientContext, SchedulingRequest, CaseContext
from app.engine.run_engine import run_case

# Construct patient context from your own data source
patient = PatientContext(
    patient_id="123",
    full_name="علی احمدی",
    insurance_name="ایران",
    unfinished_treatment_title="درمان ریشه",
    preferred_weekday="شنبه"
)

request = SchedulingRequest(
    service_name="کشیدن دندان"
)

case_context = CaseContext(patient=patient, request=request)
result = run_case(case_context)
```

### Example 3: Real CRM Integration (Future)
```python
from app.integrations.crm.client import CRMClient
from app.integrations.crm.adapter import build_case_context_from_crm
from app.engine.run_engine import run_case

# Initialize real CRM client
crm_client = CRMClient(
    base_url="https://clinic-crm.example.com/api",
    api_key="your-api-key"
)

# Build case context from CRM
case_context = build_case_context_from_crm(
    crm_client=crm_client,
    patient_id="123",
    service_name="کشیدن دندان"
)

# Run engine
result = run_case(case_context)
```

## Test Results

All **10/10 tests passing**:

```bash
pytest tests/test_engine.py -v
```

Tests cover:
- ✅ PatientContext and CaseContext creation
- ✅ MockCRMClient functionality
- ✅ CRM Adapter building CaseContext
- ✅ Engine with CaseContext
- ✅ run_case() entry point
- ✅ run_from_crm() entry point
- ✅ Preference handling
- ✅ Score validation (all 0-1 range)
- ✅ Minimum 5 recommendations returned

## Output Format

```json
{
  "success": true,
  "patient_id": "123",
  "patient_name": "علی احمدی",
  "total_recommendations": 10,
  "total_slots_evaluated": 224,
  "generated_at": "2026-02-03T11:43:21",
  "case_context": {
    "patient_id": "123",
    "insurance": "ایران",
    "unfinished_treatment": "درمان ریشه",
    "service_requested": "کشیدن دندان"
  },
  "top_recommendations": [
    {
      "weekday": "شنبه",
      "shift_code": "D",
      "time": "08:00-08:30",
      "doctor": "نعمتی",
      "score": 0.645,
      "breakdown": {
        "urgency": 0.5,
        "financial": 0.5,
        "availability": 1.0,
        "complexity_fit": 0.8
      }
    }
    // ... 9 more recommendations
  ],
  "draft": {
    "weekday": "شنبه",
    "shift_code": "D",
    "time": "08:00-08:30",
    "doctor": "نعمتی",
    "score": 0.645,
    "reason": "Good match (score: 0.64); doctor confirmed available; morning shift"
  }
}
```

## CSV Outputs

### 1. slot_recommendations.csv
All recommendations with detailed scoring

### 2. schedule_draft.csv
Best single choice with reasoning

## Implementing Real CRM Integration

### Step 1: Implement CRMClient Methods
Edit `app/integrations/crm/client.py` and replace TODOs with actual API calls:

```python
def get_patient(self, patient_id: str | int) -> Dict[str, Any]:
    response = requests.get(
        f"{self.base_url}/patients/{patient_id}",
        headers={'Authorization': f'Bearer {self.api_key}'}
    )
    return response.json()
```

### Step 2: Configure CRM Settings
Edit `app/config.py`:

```python
CRM_BASE_URL = "https://your-crm.example.com/api"
CRM_API_KEY = "your-api-key"
USE_MOCK_CRM = False  # Switch to real CRM
```

### Step 3: Test Real CRM
```python
result = run_from_crm(
    patient_id="real-patient-id",
    service_name="کشیدن دندان",
    use_mock=False  # Use real CRM
)
```

## Key Benefits

1. **Decoupled Design**: Engine doesn't know about CRM structure
2. **Easy Testing**: MockCRMClient for development/testing
3. **Flexible Integration**: Adapter pattern allows any CRM
4. **Type Safety**: Pydantic validation for all data
5. **Backward Compatible**: Legacy `run()` still works
6. **Clear Interfaces**: Well-defined contracts between layers

## Migration Path

### Current State
- ✅ Engine accepts CaseContext
- ✅ Mock CRM working
- ✅ Adapter layer complete
- ✅ Tests passing
- ⏳ Real CRM client (TODOs in place)

### Next Steps
1. Obtain CRM API documentation
2. Implement CRMClient methods (replace TODOs)
3. Test with staging CRM
4. Deploy to production
5. Monitor and optimize

## Configuration (app/config.py)

```python
# CRM Settings
CRM_BASE_URL: Optional[str] = None
CRM_API_KEY: Optional[str] = None
CRM_TIMEOUT_SECONDS = 30
USE_MOCK_CRM = True  # Set to False for production

# Scoring Weights
WEIGHT_URGENCY = 0.35
WEIGHT_FINANCIAL = 0.30
WEIGHT_AVAILABILITY = 0.20
WEIGHT_COMPLEXITY_FIT = 0.15

# Time Blocks
SLOT_MINUTES = 30
SHIFT_D_START = "08:00"  # Day shift
SHIFT_E_START = "14:00"  # Evening shift
SHIFT_N_START = "20:00"  # Night shift
```

---

**Status**: ✅ **CRM-READY - Production Ready with Mock CRM**
**Real CRM Integration**: ⏳ **Ready for Implementation (TODOs in place)**
**Tests**: ✅ **10/10 Passing**
**Date**: February 3, 2026
