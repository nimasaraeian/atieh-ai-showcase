# Payments CRM Code All-Years Report

Identity signal: numeric code inside **final parentheses** in `patient_name_raw` (e.g. `محمودي معصومه(101674)`).
This report validates extraction across all years in `payments_unified_staging` and whether extracted code equals `record_no`.

---

## 1. Overall Summary

| Metric | Value |
|--------|-------|
| Total payment rows (staging) | 876,054 |
| Total rows in CRM layer | 876,054 |
| Rows with embedded CRM code | 876,054 |
| Coverage (with code / all payment rows) | 100.00% |
| Distinct extracted CRM codes | 128,266 |
| Rows where extracted code = record_no | 723,133 |
| Exact match rate (among rows with code) | 82.54% |
| Rows with code but record_no null | 152,921 |
| Rows with code where extracted ≠ record_no | 0 |

---

## 2. Per-Year Metrics

### Shamsi year 1395

| Metric | Value |
|--------|-------|
| Total payment rows | 43,257 |
| Rows with embedded CRM code | 43,257 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 17,758 |
| Rows where extracted = record_no | 43,257 |
| Exact match rate % | 100.00% |
| Rows with code but record_no null | 0 |
| Rows where extracted ≠ record_no | 0 |

### Shamsi year 1396

| Metric | Value |
|--------|-------|
| Total payment rows | 57,151 |
| Rows with embedded CRM code | 57,151 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 16,901 |
| Rows where extracted = record_no | 57,151 |
| Exact match rate % | 100.00% |
| Rows with code but record_no null | 0 |
| Rows where extracted ≠ record_no | 0 |

### Shamsi year 1397

| Metric | Value |
|--------|-------|
| Total payment rows | 71,809 |
| Rows with embedded CRM code | 71,809 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 17,520 |
| Rows where extracted = record_no | 71,809 |
| Exact match rate % | 100.00% |
| Rows with code but record_no null | 0 |
| Rows where extracted ≠ record_no | 0 |

### Shamsi year 1398

| Metric | Value |
|--------|-------|
| Total payment rows | 80,713 |
| Rows with embedded CRM code | 80,713 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 19,561 |
| Rows where extracted = record_no | 80,713 |
| Exact match rate % | 100.00% |
| Rows with code but record_no null | 0 |
| Rows where extracted ≠ record_no | 0 |

### Shamsi year 1399

| Metric | Value |
|--------|-------|
| Total payment rows | 93,836 |
| Rows with embedded CRM code | 93,836 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 18,286 |
| Rows where extracted = record_no | 93,836 |
| Exact match rate % | 100.00% |
| Rows with code but record_no null | 0 |
| Rows where extracted ≠ record_no | 0 |

### Shamsi year 1400

| Metric | Value |
|--------|-------|
| Total payment rows | 101,753 |
| Rows with embedded CRM code | 101,753 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 18,536 |
| Rows where extracted = record_no | 101,753 |
| Exact match rate % | 100.00% |
| Rows with code but record_no null | 0 |
| Rows where extracted ≠ record_no | 0 |

### Shamsi year 1402

| Metric | Value |
|--------|-------|
| Total payment rows | 137,954 |
| Rows with embedded CRM code | 137,954 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 22,557 |
| Rows where extracted = record_no | 137,954 |
| Exact match rate % | 100.00% |
| Rows with code but record_no null | 0 |
| Rows where extracted ≠ record_no | 0 |

### Shamsi year 1403

| Metric | Value |
|--------|-------|
| Total payment rows | 152,921 |
| Rows with embedded CRM code | 152,921 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 23,239 |
| Rows where extracted = record_no | 0 |
| Exact match rate % | 0.00% |
| Rows with code but record_no null | 152,921 |
| Rows where extracted ≠ record_no | 0 |

### Shamsi year 1404

| Metric | Value |
|--------|-------|
| Total payment rows | 136,660 |
| Rows with embedded CRM code | 136,660 |
| Coverage % | 100.00% |
| Distinct extracted CRM codes | 21,528 |
| Rows where extracted = record_no | 136,660 |
| Exact match rate % | 100.00% |
| Rows with code but record_no null | 0 |
| Rows where extracted ≠ record_no | 0 |

---

## 3. Top Mismatched Examples (extracted code ≠ record_no)

| patient_name_raw | extracted_crm_code | record_no | shamsi_year |
|------------------|--------------------|-----------|-------------|

---

## 4. Assessment

- **CRM code as identity key:** High agreement between extracted code and `record_no`. Suitable as a major resolution signal with validation for mismatches.

- **Resolution layer:** Usable as a supporting resolution layer; consider combining with record_no and other identity signals.
