# Patient Scoring - Quick Reference

## Quick Queries

### Find Today's High-Value Appointments
```sql
SELECT 
    a.id, p.name, p.phone, 
    a.appointment_date,
    a.treatment_type,
    a.patient_priority_score
FROM appointments a
JOIN patients p ON a.patient_id = p.id
WHERE DATE(a.appointment_date) = DATE('now')
  AND a.patient_priority_score >= 60
ORDER BY a.patient_priority_score DESC;
```

### Top 20 Most Valuable Patients
```sql
SELECT 
    p.id, p.name, p.phone,
    p.lifetime_value_score,
    COUNT(a.id) as total_appointments
FROM patients p
JOIN appointments a ON p.id = a.patient_id
WHERE p.lifetime_value_score IS NOT NULL
GROUP BY p.id
ORDER BY p.lifetime_value_score DESC
LIMIT 20;
```

### This Month's High-Value Appointments
```sql
SELECT 
    COUNT(*) as count,
    AVG(patient_priority_score) as avg_score,
    SUM(CASE WHEN patient_priority_score >= 80 THEN 1 ELSE 0 END) as excellent
FROM appointments
WHERE strftime('%Y-%m', appointment_date) = strftime('%Y-%m', 'now')
  AND patient_priority_score IS NOT NULL;
```

## Command Line Tools

### Show Top Patients
```bash
python scripts/query_high_value_patients.py --top 10
```

### High Priority Appointments
```bash
python scripts/query_high_value_patients.py --min-score 70
```

### Treatment Analysis
```bash
# Endo treatments
python scripts/query_high_value_patients.py --treatment endo

# Restorations
python scripts/query_high_value_patients.py --treatment restoration
```

### Refresh Scores
```bash
# After importing new data
python scripts/backfill_patient_scores.py
```

### Validate System
```bash
python scripts/validate_scoring.py
```

## Score Interpretation

| Score | Priority | Action |
|-------|----------|--------|
| 80-100 | **HIGHEST** | VIP treatment, dedicated time slots, follow-up |
| 60-79 | **High** | Priority scheduling, quality care |
| 40-59 | **Medium** | Standard service |
| 20-39 | **Low** | Basic service |
| 0-19 | **Very Low** | Minimal engagement |

## Score Breakdown

- **Insurance** (0-25): Payment type value
  - Cash = 25 (best)
  - Premium insurance = 22-24
  - Standard insurance = 14-21
  
- **Treatment** (0-35): Procedure complexity
  - Endo = 35 (highest)
  - Crown/Prosthetic = 32
  - Surgery = 30
  - Restoration = 24
  - Extraction = 22
  
- **Tenure** (0-25): Patient loyalty
  - New patient = 0
  - 1+ years = 25 (max)
  
- **Frequency** (0-15): Engagement
  - 1 visit = 1.5
  - 10+ visits = 15 (max)

## Common Tasks

### Identify VIP Patients for Special Campaign
```bash
python scripts/query_high_value_patients.py --min-score 75 --limit 100
```

### Weekly High-Value Report
```sql
SELECT 
    strftime('%Y-%W', appointment_date) as week,
    COUNT(*) as total,
    AVG(patient_priority_score) as avg_score,
    COUNT(CASE WHEN patient_priority_score >= 70 THEN 1 END) as high_value
FROM appointments
WHERE appointment_date >= DATE('now', '-8 weeks')
GROUP BY week
ORDER BY week DESC;
```

### Patient Retention Analysis
```sql
SELECT 
    CASE 
        WHEN tenure_score < 5 THEN 'New (0-3mo)'
        WHEN tenure_score < 12.5 THEN 'Growing (3-6mo)'
        WHEN tenure_score < 25 THEN 'Established (6-12mo)'
        ELSE 'Loyal (1y+)'
    END as patient_segment,
    COUNT(*) as appointments,
    AVG(patient_priority_score) as avg_score
FROM appointments
WHERE patient_priority_score IS NOT NULL
GROUP BY patient_segment;
```

## Files Location

- **Migration**: `app/db/migrations/002_patient_scoring.sql`
- **Backfill**: `scripts/backfill_patient_scores.py`
- **Query Tool**: `scripts/query_high_value_patients.py`
- **Validation**: `scripts/validate_scoring.py`
- **Full Docs**: `docs/PATIENT_SCORING.md`
- **Summary**: `IMPLEMENTATION_SUMMARY.md`

## Need Help?

1. Read full documentation: `docs/PATIENT_SCORING.md`
2. Run validation: `python scripts/validate_scoring.py`
3. Check implementation summary: `IMPLEMENTATION_SUMMARY.md`
