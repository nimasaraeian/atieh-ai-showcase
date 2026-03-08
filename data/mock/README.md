# Mock CRM Data

This directory contains realistic mock data for testing the AI scheduling system.

## Files Generated:

- **patients.json** (200+ records): Patient information with Persian names
- **appointments.json** (1000+ records): Appointment history and future bookings
- **payments.json** (800+ records): Payment records with realistic delays
- **doctors.json** (20 records): Doctor profiles with specialties
- **schedules.json** (600+ records): Doctor shift schedules for 60 days
- **blocks.json** (50 records): Blocking events (vacations, meetings)

## Data Characteristics:

### Patients:
- Realistic Persian names (using Faker or fallback list)
- Iranian phone numbers (09XX format)
- 10-digit national IDs
- Payment type distribution: 20% cash, 80% insurance
- Lifetime range: 6 months to 5 years

### Appointments:
- Date range: 90 days past to 90 days future
- Working hours: 9 AM - 6 PM
- Status distribution:
  - Past: 85% completed, 10% cancelled, 5% no-show
  - Future: 30% booked, 70% confirmed
- Priority scores calculated based on payment, treatment, lifetime

### Payments:
- Coverage: ~80% of completed/cancelled appointments
- Status distribution: 80% paid, 5% partial, 10% pending, 5% refunded
- Realistic payment delays (some early, most on-time, some late)

### Doctors:
- 20 doctors with Persian names
- Specialties: عمومی, اطفال, ارتودنسی, ایمپلنت, جراحی, زیبایی
- Experience: 3-25 years
- Rating: 4.0-5.0
- 95% active

### Schedules:
- 60 days coverage (past and future)
- Two shifts: صبح (08:00-14:00), عصر (14:00-20:00)
- Fridays off
- ~70% doctor availability per day

### Blocks:
- Types: vacation, meeting, conference, emergency
- Random time blocks during working hours
- Duration: 30-240 minutes

## Regenerating Data:

```bash
python scripts/generate_mock_crm_data.py --patients 200 --appointments 1000
```

## Usage in Tests:

```python
from app.integrations.crm.mock_client import MockCRMClient

client = MockCRMClient()
patients = client.fetch_patients()
appointments = client.fetch_appointments()
```

## Notes:

- All datetimes are in ISO 8601 format
- Persian text is properly encoded (UTF-8)
- Data is internally consistent (patient IDs match, dates are logical)
- `_meta` fields in patients are for testing only (not returned by adapter)
