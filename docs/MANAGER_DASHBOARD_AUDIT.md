# Manager Dashboard Audit — Pre-Implementation

## 1. REAL METRICS (SQLite-backed)

| Metric | Endpoint | Source | Filters |
|--------|----------|--------|---------|
| Total Patients | `/api/manager/total-patients` | patients / financial_identity_profile | tier |
| Total Revenue | `/api/manager/total-revenue` | payments_clean.net_received | start_date, end_date, payment |
| Total Transactions | `/api/manager/total-transactions` | payments_clean | start_date, end_date, payment |
| VIP Patients | `/api/manager/vip-patients` | financial_identity_profile | none |
| No-Show Rate | `/api/manager/no-show-rate` | appointments.status | start_date, end_date, doctor, service |
| Utilization | `/api/manager/doctor-utilization` | appointments.status=completed | start_date, end_date, doctor, service |
| Active Doctors | `/api/manager/active-doctors` | doctor_master | none |
| Financial Summary | `/api/manager/financial-summary` | payments_clean | start_date, end_date, payment |
| Payment Distribution | `/api/manager/payment-distribution` | payments_clean | start_date, end_date |
| Revenue Trend | `/api/manager/revenue-trend` | payments_clean | start_date, end_date, payment |
| Top Value Patients | `/api/manager/patients/top-value` | v_patients_financial_resolved | start_date, end_date, tier |
| Transaction Stats | `/api/manager/transaction-stats` | payments_clean | start_date, end_date, payment |
| Tier Distribution | `/api/manager/tier-distribution` | financial_identity_profile | tier |
| Transaction Trend | `/api/manager/transaction-trend` | payments_clean | start_date, end_date, payment |
| Top Services | `/api/manager/top-services` | appointments + service_dim | start_date, end_date |
| Revenue by Service | `/api/manager/revenue-by-service` | payments_clean + appointments | start_date, end_date, payment |

## 2. MOCK / INCONSISTENT METRICS

| Chart/Section | Current State | Backend | Action |
|---------------|---------------|---------|--------|
| Revenue by Doctor | MOCK_REVENUE_BY_DOCTOR | None | Add endpoint + doctor normalization |
| Doctor Workload (bar chart) | MOCK_DOCTOR_WORKLOAD | None | Add endpoint (appointments per doctor) |
| Doctor Revenue (inline) | MOCK_DOCTOR_WORKLOAD | None | Use revenue-by-doctor |
| Patient Growth | MOCK_PATIENT_GROWTH | None | Placeholder "در حال تکمیل" |
| Recent Transactions | MOCK_TRANSACTIONS | None | Placeholder or hide |
| Appointment Trend | MOCK_APPOINTMENTS_TREND | None | Placeholder or add endpoint |
| Peak Hours | MOCK_PEAK_HOURS | None | Placeholder |
| Debtors | MOCK_DEBTORS | None | Placeholder |
| Recent Appointments | MOCK_RECENT_APPOINTMENTS | None | Placeholder |
| Inactive Patients | MOCK_INACTIVE_PATIENTS | None | Placeholder |

## 3. DOCTOR NORMALIZATION NEEDED

- **Filter dropdown**: Uses `raw_text_doctor` — noisy (دکتر مهرناز صدیقی متخصص پریو, دکتر مهرداد سلامی عمومی, etc.)
- **Active doctors**: Uses `doctor_master` only — if empty, returns 0 even when appointments have doctors
- **Doctor analytics**: No revenue/workload by doctor; raw names unsuitable
- **Solution**: Add doctor normalizer (strip دکتر, specialty suffixes), doctor_dim or on-the-fly normalization, fallback active_doctors from appointments

## 4. SERVICE NORMALIZATION — DONE

- service_dim populated
- top-services, revenue-by-service use clean_service_category
- Filter dropdown uses clean categories

## 5. FILTER BEHAVIOR

| Filter | Populates From | Applied To | Status |
|--------|----------------|------------|--------|
| Date range | Presets (today, week, month, all) | Revenue, transactions, no-show, utilization, etc. | OK |
| Doctor | appointments.raw_text_doctor | no-show, utilization | Works (noisy values) |
| Service | service_dim.clean_service_category | no-show, utilization, top-services | OK |
| Payment | payments_clean.payer_source_norm | Revenue, transactions | OK |
| Tier | financial_identity_profile | total-patients | OK |

**Gaps**: getVipPatientsCount does not accept filters. total-patients accepts tier. Active doctors has no filters. ManagerFilters passes date_range="all" → no start/end; backend returns unfiltered. OK.

## 6. KPI CARD / OVERFLOW

- KPIStatCard uses formatNumberShort, formatCurrencyShort
- formatNumberShort supports K/M/B/T
- Persian mode: digits use fa-IR; suffixes still K, M, B, T (not هزار, میلیون)
- Need: Persian suffixes for compact display; ensure no overflow
