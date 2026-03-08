# Patient Priority Scoring System

## Overview

The Patient Priority Scoring System calculates a comprehensive 0-100 point score for each appointment and patient based on multiple value factors. This enables the clinic to:

- Identify high-value patients
- Prioritize appointment scheduling
- Optimize resource allocation
- Analyze revenue patterns by treatment and insurance type

## Scoring Components

Each appointment receives a **patient_priority_score** (0-100) composed of four factors:

### 1. Insurance Score (0-25 points)

Reflects the value and reliability of different payment types:

- **CASH**: 25 points (highest value, immediate payment)
- **INSURANCE_18**: 24 points (premium insurance)
- **INSURANCE_3**: 23 points (high-value insurance)
- **INSURANCE_1**: 22 points
- **Default**: 10 points (unknown insurance types)

### 2. Treatment Score (0-35 points)

Based on treatment complexity and value:

- **endo** (endodontic/root canal): 35 points
- **crown_prosthetic**: 32 points
- **surgery**: 30 points
- **restoration**: 24 points
- **extraction**: 22 points
- **scaling**: 18 points
- **dental_care**: 12 points (general)
- **consultation**: 10 points

### 3. Tenure Score (0-25 points)

Rewards patient loyalty based on relationship length:

```
tenure_days = (appointment_date - first_appointment_date).days
tenure_score = min(25, (tenure_days / 365) * 25)
```

- New patients: 0 points
- 1+ year patients: 25 points (maximum)
- Linear scale in between

### 4. Frequency Score (0-15 points)

Rewards patient engagement:

```
frequency_score = min(15, total_appointments * 1.5)
```

- 1 appointment: 1.5 points
- 10 appointments: 15 points (maximum)

## Database Schema

### Appointments Table - New Columns

```sql
patient_priority_score REAL    -- Total score (0-100)
insurance_score REAL            -- Insurance component (0-25)
treatment_score REAL            -- Treatment component (0-35)
tenure_score REAL               -- Tenure component (0-25)
frequency_score REAL            -- Frequency component (0-15)
```

### Patients Table - New Column

```sql
lifetime_value_score REAL       -- Average of appointment scores (weighted 70% avg, 30% max)
```

## Usage

### Initial Setup

1. **Run Migration**:
```bash
sqlite3 atieh_clinic.db < app/db/migrations/002_patient_scoring.sql
```

2. **Backfill Existing Data**:
```bash
python scripts/backfill_patient_scores.py
```

Expected output:
- Total appointments scored
- Score distribution
- Top 10 highest value patients
- Sample score breakdowns

### Query High-Value Patients

Use the query utility script for various analyses:

**Default Report** (top 10 patients + high-score appointments):
```bash
python scripts/query_high_value_patients.py
```

**Top N Patients**:
```bash
python scripts/query_high_value_patients.py --top 20
```

**Appointments Above Threshold**:
```bash
python scripts/query_high_value_patients.py --min-score 80 --limit 50
```

**By Treatment Type**:
```bash
python scripts/query_high_value_patients.py --treatment endo --limit 30
python scripts/query_high_value_patients.py --treatment restoration
```

### SQL Queries

**Find high-priority appointments needing attention**:
```sql
SELECT 
    a.id, 
    p.name, 
    a.appointment_date, 
    a.patient_priority_score
FROM appointments a
JOIN patients p ON a.patient_id = p.id
WHERE a.patient_priority_score >= 80
ORDER BY a.patient_priority_score DESC;
```

**Top value patients with contact info**:
```sql
SELECT 
    p.id,
    p.name,
    p.phone,
    p.lifetime_value_score,
    COUNT(a.id) as total_appointments
FROM patients p
JOIN appointments a ON p.id = a.patient_id
GROUP BY p.id
ORDER BY p.lifetime_value_score DESC
LIMIT 20;
```

**Score distribution by treatment type**:
```sql
SELECT 
    treatment_type,
    COUNT(*) as count,
    AVG(patient_priority_score) as avg_score,
    MIN(patient_priority_score) as min_score,
    MAX(patient_priority_score) as max_score
FROM appointments
WHERE patient_priority_score IS NOT NULL
GROUP BY treatment_type
ORDER BY avg_score DESC;
```

**Monthly high-value appointment trends**:
```sql
SELECT 
    strftime('%Y-%m', appointment_date) as month,
    COUNT(*) as high_value_appointments,
    AVG(patient_priority_score) as avg_score
FROM appointments
WHERE patient_priority_score >= 70
GROUP BY month
ORDER BY month;
```

## Configuration

All scoring weights are configurable in `scripts/backfill_patient_scores.py`:

```python
CONFIG = {
    "insurance_scores": {
        "CASH": 25,
        "INSURANCE_3": 23,
        # ... customize as needed
        "default": 10,
    },
    
    "treatment_scores": {
        "endo": 35,
        "crown_prosthetic": 32,
        # ... customize as needed
        "default": 12,
    },
    
    "tenure": {
        "max_points": 25,
        "years_for_max": 1.0,
    },
    
    "frequency": {
        "max_points": 15,
        "points_per_appointment": 1.5,
    },
}
```

To update scoring:
1. Modify CONFIG values
2. Re-run `python scripts/backfill_patient_scores.py`

## Score Interpretation

| Score Range | Category | Description |
|-------------|----------|-------------|
| 80-100 | Excellent | Highest priority, premium treatments, loyal patients |
| 60-79 | High | Valuable patients, good treatments, established relationship |
| 40-59 | Medium | Standard patients, routine treatments |
| 20-39 | Low | Basic treatments, new/infrequent patients |
| 0-19 | Very Low | Minimal engagement |

## Statistics (Current Data)

Based on 25,808 appointments:

- **Average Score**: 46.6
- **Score Range**: 27.5 - 90.8
- **Distribution**:
  - Excellent (80-100): 0.1%
  - High (60-79): 8.1%
  - Medium (40-59): 72.5%
  - Low (20-39): 19.3%

**Top Treatment Types by Score**:
- Endo: 68.4 avg (370 appointments)
- Surgery: 64.4 avg (1 appointment)
- Restoration: 59.8 avg (41 appointments)
- Crown/Prosthetic: 58.5 avg (1 appointment)

## Files

- `app/db/migrations/002_patient_scoring.sql` - Database schema changes
- `scripts/backfill_patient_scores.py` - Main scoring calculation script
- `scripts/query_high_value_patients.py` - Query utility for analysis
- `docs/PATIENT_SCORING.md` - This documentation

## Future Enhancements

Potential improvements to consider:

1. **Dynamic Scoring**: Recalculate scores automatically on new appointments
2. **Predictive Modeling**: Use historical scores to predict patient lifetime value
3. **Segmentation**: Create patient segments for targeted marketing
4. **Revenue Integration**: Factor in actual payment amounts when available
5. **Cancellation Impact**: Adjust scores based on no-show history
6. **Seasonal Adjustments**: Account for appointment timing patterns

## Support

For questions or issues:
- Review score breakdown samples in backfill output
- Check component scores (insurance_score, treatment_score, etc.)
- Verify configuration matches business rules
- Run queries to validate data integrity
