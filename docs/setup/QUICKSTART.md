# Atieh Clinic Scheduling AI - Quick Start Guide

**Pre-CRM Phase - Mock Data Mode**

This guide helps you get the AI scheduling system running locally with mock data.

---

## Prerequisites

- Python 3.9+ installed
- Git (optional, for cloning)
- Terminal/PowerShell access

---

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI, Uvicorn (web server)
- SQLAlchemy, Pydantic (data models)
- PyYAML (configuration)
- Faker (mock data generation)
- Pytest (testing)
- And more...

### 2. Generate Mock CRM Data

```bash
python scripts/generate_mock_crm_data.py --patients 200 --appointments 1000
```

This creates realistic mock data in `data/mock/`:
- **patients.json** (200 patients with Persian names)
- **appointments.json** (1000 appointments)
- **payments.json** (800+ payment records)
- **doctors.json** (20 doctors)
- **schedules.json** (60 days of doctor schedules)
- **blocks.json** (50 blocking events)

---

## Running the Server

### Option 1: Using Run Script (Recommended)

**Windows (PowerShell):**
```powershell
.\scripts\run_local.ps1
```

**Linux/Mac:**
```bash
bash scripts/run_local.sh
```

**With Tests:**
```bash
bash scripts/run_local.sh --test
```

### Option 2: Using Makefile (Unix/Linux/Mac)

```bash
# Start server in mock mode
make run

# Or with all steps
make mock-data
make test
make run
```

### Option 3: Manual Start

```bash
# Set CRM mode to mock
export CRM_MODE=mock  # Linux/Mac
$env:CRM_MODE = "mock"  # Windows PowerShell

# Start server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

---

## Accessing the System

Once the server is running:

- **Web UI**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

---

## Testing New AI Endpoints

### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "crm_mode": "mock",
  "crm_healthy": true,
  "timestamp": "2026-02-05T..."
}
```

### 2. Score a Patient

```bash
curl -X POST "http://localhost:8000/ai/score-patient?patient_id=1"
```

**Expected Response:**
```json
{
  "patient_id": "1",
  "explain": {
    "priority_score": 75,
    "value_score": 80,
    "risk_no_show": 0.15,
    "risk_late_payment": 0.10,
    "reason_codes": ["HIGH_VALUE", "CASH_PAYMENT", "LOYAL_CUSTOMER"]
  },
  "insights": {
    "lifetime_months": 24,
    "total_appointments": 15,
    "completion_rate": 0.93,
    "payment_category": "عالی",
    "lifetime_category": "عالی"
  }
}
```

### 3. Get Slot Recommendations

```bash
curl -X POST "http://localhost:8000/ai/recommend-slot?patient_id=1&service_id=TREATMENT_5&days_ahead=30&max_slots=5"
```

**Expected Response:**
```json
{
  "patient_id": "1",
  "service_id": "TREATMENT_5",
  "urgency_level": "high",
  "explain": {
    "priority_score": 85,
    "value_score": 90,
    "risk_no_show": 0.05,
    "risk_late_payment": 0.03,
    "reason_codes": ["CASH_PAYMENT", "HIGH_VALUE", "URGENT_TREATMENT"]
  },
  "recommended_slots": [
    {
      "start_datetime": "2026-02-10T09:00:00Z",
      "end_datetime": "2026-02-10T09:45:00Z",
      "doctor_id": "AUTO",
      "doctor_name": null,
      "confidence": 0.92,
      "reason_codes": ["BEST_MATCH", "MORNING_SLOT", "AVAILABLE_SOON"]
    }
    // ... 4 more slots
  ]
}
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Contract validation tests
pytest tests/test_scoring_contract.py -v

# Scheduling overlap tests
pytest tests/test_scheduling_no_overlap.py -v

# API endpoint tests
pytest tests/test_api_recommend_slot.py -v
```

### Quick Test Run

```bash
pytest tests/ -q
```

---

## Configuration

### Weights Configuration

Edit `config/weights.yaml` to adjust AI scoring weights:

```yaml
weights:
  payment: 0.40      # Payment type weight
  treatment: 0.35    # Treatment type weight
  lifetime: 0.25     # Customer lifetime weight

penalties:
  no_show: 25        # No-show risk penalty
  late_payment: 20   # Late payment risk penalty

boosts:
  high_value: 10     # High-value patient boost
```

Changes take effect immediately (no restart needed).

### CRM Mode Configuration

**Environment Variables:**

```bash
# Mock mode (default)
export CRM_MODE=mock

# Live mode (requires CRM credentials)
export CRM_MODE=live
export CRM_BASE_URL="https://crm.example.com/api"
export CRM_API_KEY="your-api-key"
export CRM_AUTH_TYPE="bearer"  # or "api_key" or "basic"
export CRM_TIMEOUT="30"
```

---

## Switching to Live CRM Mode

### Prerequisites

1. Get CRM API credentials from IT/CRM team
2. Get API documentation with endpoint details
3. Test credentials with CRM staging environment

### Steps

1. **Set Environment Variables:**

```bash
export CRM_MODE=live
export CRM_BASE_URL="https://your-crm-api.com/api"
export CRM_API_KEY="your-actual-api-key"
export CRM_AUTH_TYPE="bearer"
```

2. **Implement Live Client Methods:**

Edit `app/integrations/crm/live_client.py` and replace `TODO` sections with actual API calls.

3. **Test Connection:**

```bash
curl http://localhost:8000/health
```

Check that `crm_healthy` is `true`.

4. **Start Server:**

```bash
CRM_MODE=live uvicorn app:app --reload
```

---

## Troubleshooting

### Mock Data Not Found

**Error:** "Mock data file not found: ..."

**Solution:**
```bash
python scripts/generate_mock_crm_data.py
```

### Import Errors

**Error:** "ModuleNotFoundError: ..."

**Solution:**
```bash
pip install -r requirements.txt
```

### Port Already in Use

**Error:** "Address already in use"

**Solution:**
```bash
# Use different port
uvicorn app:app --port 8001

# Or kill process on port 8000
# Linux/Mac:
lsof -ti:8000 | xargs kill -9
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database Locked

**Error:** "database is locked"

**Solution:**
```bash
# Stop server
# Delete database file
rm atieh_clinic.db

# Restart server (will recreate DB)
```

---

## Project Structure

```
atieh/
├── app.py                      # FastAPI main app
├── config/
│   └── weights.yaml            # AI weights configuration
├── app/
│   ├── schemas/
│   │   ├── ai_contract.py      # AI output contracts
│   │   └── canonical.py        # Internal data models
│   └── integrations/crm/
│       ├── interface.py        # CRM client interface
│       ├── mock_client_new.py  # Mock CRM client
│       ├── live_client.py      # Live CRM client (skeleton)
│       ├── mapper.py           # CRM data mapper
│       └── factory.py          # CRM client factory
├── data/mock/                  # Mock CRM data (JSON files)
├── scripts/
│   ├── generate_mock_crm_data.py
│   ├── run_local.sh            # Unix run script
│   └── run_local.ps1           # Windows run script
├── tests/
│   ├── test_scoring_contract.py
│   ├── test_scheduling_no_overlap.py
│   └── test_api_recommend_slot.py
├── requirements.txt
├── Makefile
└── QUICKSTART.md              # This file
```

---

## Next Steps

1. **Explore API Docs**: Visit http://localhost:8000/docs
2. **Try Sample Requests**: Use curl or Postman with examples above
3. **Run Tests**: Ensure all tests pass with `pytest tests/ -v`
4. **Customize Weights**: Edit `config/weights.yaml` to tune AI scoring
5. **Integrate Real CRM**: When ready, implement `live_client.py` methods

---

## Support

For issues or questions:
- Check NOTES.md for implementation details
- Review API docs at /docs endpoint
- Check logs for error messages
- Ensure mock data is generated

---**Status**: ✅ Ready for Development & Testing (Mock Mode)  
**Next Milestone**: Real CRM Integration  
**Date**: February 2026
