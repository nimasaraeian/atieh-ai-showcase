# Manager Dashboard Metrics Audit

**Date:** 2025-03-10  
**Purpose:** Verify all displayed metrics against real SQLite database; ensure correct queries, units, and definitions.

---

## 1. Metric Verification Checklist

| Metric | Endpoint | SQL Source | Table(s) | Unit | Real/Mock | Filters |
|--------|----------|------------|----------|------|-----------|---------|
| **Total Patients** | `GET /api/manager/total-patients` | `SELECT COUNT(*) FROM patients` | patients | count | ✅ Real | None |
| **Total Revenue** | `GET /api/manager/total-revenue` | `SELECT COALESCE(SUM(net_received),0) FROM payments_clean` | payments_clean | تومان | ✅ Real | None |
| **Total Transactions** | `GET /api/manager/total-transactions` | `SELECT COUNT(*) FROM payments_clean` | payments_clean | count | ✅ Real | None |
| **Active Doctors** | `GET /api/manager/active-doctors` | `SELECT COUNT(*) FROM doctor_master` | doctor_master | count | ✅ Real | None |
| **VIP Patients** | `GET /api/manager/vip-patients` | `SELECT COUNT(*) FROM financial_identity_profile WHERE financial_tier='VIP'` | financial_identity_profile | count | ✅ Real | None |
| **No-Show Rate** | `GET /api/manager/no-show-rate` | `SUM(CASE status='no_show')*100/COUNT(*) FROM appointments` | appointments | % | ✅ Real | None |
| **Workload** | `GET /api/manager/doctor-utilization` | `SUM(CASE status='completed')*100/COUNT(*) FROM appointments` | appointments | % | ✅ Real | None |
| **Today Revenue** | — | — | — | تومان | ❌ Mock | N/A |
| **Weekly Revenue** | — | — | — | تومان | ❌ Mock | N/A |
| **Collected Amount** | Same as Total Revenue | Same | payments_clean | تومان | ✅ Real | None |
| **Outstanding Debt** | — | No debt table | — | تومان | ❌ Mock | N/A |
| **Successful Transactions** | — | payments_clean has no status | — | count | ❌ Mock | N/A |
| **Failed Transactions** | — | payments_clean has no status | — | count | ❌ Mock | N/A |
| **Avg Transaction Value** | Computed | total_revenue / total_transactions | Derived | تومان | ✅ Real | None |
| **Payment Distribution** | `GET /api/manager/payment-distribution` | `GROUP BY payer_source_norm FROM payments_clean` | payments_clean | % | ✅ Real | None |
| **Revenue Trend** | `GET /api/manager/revenue-trend` | `GROUP BY day, SUM(net_received) FROM payments_clean` | payments_clean | تومان | ✅ Real | limit=90 |
| **Top Value Patients** | `GET /api/manager/patients/top-value` | `SELECT ... FROM v_financial_identity_profile ORDER BY lifetime_net_received DESC` | financial_identity_profile | — | ✅ Real | limit |
| **Tier Distribution** | `GET /api/manager/dashboard/summary` | `COUNT(*) GROUP BY financial_tier` | financial_identity_profile | count | ✅ Real | None |
| **Revenue by Doctor** | — | payments_clean has NO doctor column | — | تومان | ❌ Mock | N/A |
| **Revenue by Service** | — | payments_clean has NO service column | — | تومان | ❌ Mock | N/A |
| **Patient Growth** | — | Not implemented | — | count | ❌ Mock | N/A |
| **Transaction Trend** | — | Not implemented | — | count | ❌ Mock | N/A |
| **Doctor Workload Chart** | — | Needs appointments + doctor; doctor in appointments unclear | — | % | ❌ Mock | N/A |
| **Appointment Trend** | — | Not implemented | — | count | ❌ Mock | N/A |
| **Peak Hours** | — | Not implemented | — | count | ❌ Mock | N/A |
| **Recent Transactions** | — | Not implemented | — | — | ❌ Mock | N/A |
| **Recent Appointments** | — | Not implemented | — | — | ❌ Mock | N/A |
| **Debtors** | — | No debt table in schema | — | تومان | ❌ Mock | N/A |
| **Inactive Patients** | — | Not implemented | — | — | ❌ Mock | N/A |

---

## 2. Inconsistencies Detected

### 2.1 Total Patients Definition Conflict
- **`/api/manager/total-patients`** → `patients` table (all patient records)
- **`/api/manager/dashboard/summary`** → `financial_identity_profile` (financially-tracked identities)
- **Risk:** Counts can differ significantly. Dashboard KPI uses total-patients (patients). Tier/VIP use financial_identity_profile.

### 2.2 Unit Consistency
- **Currency:** All monetary values in DB use same unit. Frontend formatters use **تومان** (Toman) – confirmed in `formatters.js`.
- **payments_clean.net_received** and **financial_identity_profile.lifetime_net_received** – source data unit is assumed تومان (from importers and clinic context).

### 2.3 Workload Metric Mislabeling
- **Backend:** Returns `utilization` = % of appointments with status='completed' (overall clinic utilization).
- **Frontend label:** "Workload" / "بهره‌وری" – implies per-doctor load. The backend metric is **clinic-wide completion rate**, not per-doctor workload.

### 2.4 Active Doctors = 0 While Doctor Charts Show Data
- If `doctor_master` is empty, `active_doctors` = 0.
- Revenue-by-doctor chart uses **MOCK_DOCTOR_WORKLOAD** – always shows 4 doctors.
- **Result:** Contradiction possible (0 active doctors vs chart with 4).

### 2.5 No Filters Applied
- **All endpoints** ignore date range, doctor, service, payment type, patient tier.
- Filter bar exists in UI but does not pass params to API.

---

## 3. Standardized Metric Definitions

| Term | Definition |
|------|------------|
| **Total Revenue** | Sum of `net_received` over all rows in `payments_clean`. Unit: تومان. |
| **Collected Amount** | Same as Total Revenue. |
| **Outstanding Debt** | Not computable from current schema. Requires separate debt/claims table. |
| **Successful Transaction** | In `payments_clean`, every row represents a payment received. No success/fail status. |
| **Active Doctor** | Count of rows in `doctor_master` table. |
| **Workload** | Currently: % of appointments with status='completed' (clinic-wide). Not per-doctor. |
| **No-Show** | % of appointments with status='no_show'. |

---

## 4. Schema Gaps

- **payments_clean:** No `doctor_id`, no `service`/treatment type. Cannot compute revenue by doctor/service from payments alone.
- ** appointments:** Has `status`; may have doctor info via raw text. Join to payments requires record_no + date bridge.
- **Debt:** No table for outstanding debt.
- **Transaction status:** payments_clean has no status; all rows are received payments.

---

## 5. Recommendations

1. **Add real endpoints** for today revenue, weekly revenue (filter payments_clean by date).
2. **Add tier distribution** from `financial_identity_profile` (dashboard/summary already returns it; use that for tier pie).
3. **Hide or mark** metrics with no backend: today, weekly, outstanding debt, successful/failed counts, revenue by doctor/service, patient growth, transaction trend, doctor workload chart, appointment trend, peak hours, recent transactions, recent appointments, debtors, inactive patients.
4. **Rename** "Workload" to "Completion Rate" or add subtitle: "کل نوبت‌های تکمیل شده" to avoid confusion.
5. **Standardize total_patients:** Choose one source (patients vs financial_identity_profile) and document.

---

## 6. Endpoint → SQL Quick Reference

```
GET /api/manager/total-patients       → SELECT COUNT(*) FROM patients
GET /api/manager/total-transactions   → SELECT COUNT(*) FROM payments_clean
GET /api/manager/total-revenue        → SELECT COALESCE(SUM(net_received),0) FROM payments_clean
GET /api/manager/vip-patients         → SELECT COUNT(*) FROM financial_identity_profile WHERE financial_tier='VIP'
GET /api/manager/no-show-rate         → appointments: SUM(CASE status='no_show')*100/COUNT(*)
GET /api/manager/active-doctors       → SELECT COUNT(*) FROM doctor_master
GET /api/manager/doctor-utilization   → appointments: SUM(CASE status='completed')*100/COUNT(*)
GET /api/manager/payment-distribution → payments_clean: GROUP BY payer_source_norm
GET /api/manager/revenue-trend        → payments_clean: GROUP BY day ORDER BY day DESC LIMIT ?
GET /api/manager/financial-summary    → payments_clean: today, weekly, total; outstanding_debt=0
GET /api/manager/transaction-stats    → payments_clean: total, successful=total, failed=0, cash/ins %, avg
GET /api/manager/transaction-trend    → payments_clean: GROUP BY day, COUNT(*)
GET /api/manager/tier-distribution    → financial_identity_profile: GROUP BY financial_tier
GET /api/manager/patients/top-value   → v_financial_identity_profile ORDER BY lifetime_net_received DESC
GET /api/manager/dashboard/summary    → financial_identity_profile: total_patients + tier counts
```
