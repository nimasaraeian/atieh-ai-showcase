# Reception panel – production refinement pass

## 1. Review / warning logic

- **Rule:** Show "این پیوند نیاز به بررسی دارد" **only** when `review_flag === 1` **or** `review_reason` is non-empty.
- **Do not** derive review state from: financial level, link tier, identity strength tier, payment amount.
- **Applied in:** search result row badges, selected patient profile card, backend `_needs_review()` and `review_warning` in API.

## 2. Financial amounts = IRR / Rial

- All monetary values in reception (total_net_received, positive/negative sums, patient value) are **ریال (IRR)**.
- **No "تومان"** in reception UI; use **"ریال"**.
- Frontend: `formatCurrencyRial()` in `formatters.js`; used for financial summary card. Thousand separators; negatives shown with minus.
- Subtitle/tooltip: "مبالغ بر حسب ریال" on the financial card.

## 3. Empty-state labels

- Replaced raw "ثبت نشده" with:
  - **نامشخص** for optional/unknown (e.g. priority band, scheduling score).
  - **موجود نیست** for missing options.
  - **هنوز ثبت نشده** for dates/not-yet-recorded.
  - **—** for IDs and simple empty fields.
- Helper: `emptyLabel(value, t, kind)` with `kind`: `'unknown' | 'dash' | 'notAvailable' | 'notYetRecorded'`.

## 4. Profile UI layout

- **A) Profile header:** Name, CRM code, phone, internal ID; identity/link tier badge; **review badge only if** `review_flag === 1` (via `showReviewWarning`).
- **B) Badge row:** Tier, review status, financial level, years covered, payment rows count (compact chips).
- **C) Financial summary card:** Total patient value, positive sum, negative sum, payment rows, years; all amounts as **ریال**; "مبالغ بر حسب ریال" caption.
- **D) Visit / follow-up:** First visit, last payment, follow-up queue, follow-up type, priority band, scheduling score; clean placeholders (نامشخص / هنوز ثبت نشده / —).
- **E) Empty state:** "هنوز بیماری انتخاب نشده است" + "برای مشاهده جزئیات، یک بیمار را از لیست انتخاب کنید" when no patient selected.

## 5. Search results table

- Columns: name, شماره پرونده (CRM code), mobile, tier (link tier). Tier column title = identity tier.
- **Review badge:** Shown **only** when `showReviewWarning(p)` (i.e. `review_flag === 1` or non-empty `review_reason`). No badge when `review_flag === 0` and reason empty.
- Financial level and review state are kept separate.

## 6. API response (selected profile / search row)

- Includes: `patient_id`, `crm_patient_code`, `patient_name_canonical`, `primary_phone`, `identity_strength_tier`, `link_tier`, `review_flag`, `review_reason`, `payment_rows_count`, `total_net_received`, `positive_net_received_sum`, `negative_net_received_sum`, `first_year`, `last_year`, `multi_crm_for_same_patient_flag`.
- Optional display helpers: `display_total_net_received_irr`, `display_positive_sum_irr`, `display_negative_sum_irr` (formatted for Rial); `amounts_unit`: `"IRR"`.

## 7. No DB changes

- Only frontend rendering, backend response mapping, formatters, labels, and profile structure were changed. No core identity tables or views modified.

---

## Sample JSON (search result row)

```json
{
  "patient_id": 12345,
  "crm_patient_code": "80123",
  "patient_name_canonical": "علی محمدی",
  "primary_phone": "09121234567",
  "identity_strength_tier": "strong",
  "link_tier": "A",
  "review_flag": 0,
  "review_reason": null,
  "review_warning": false,
  "payment_rows_count": 45,
  "total_net_received": 12500000.0,
  "positive_net_received_sum": 13000000.0,
  "negative_net_received_sum": -500000.0,
  "first_year": 1398,
  "last_year": 1403,
  "multi_crm_for_same_patient_flag": false,
  "amounts_unit": "IRR",
  "display_total_net_received_irr": "12٬500٬000",
  "display_positive_sum_irr": "13٬000٬000",
  "display_negative_sum_irr": "-500٬000"
}
```

---

## Run order (from repo root)

```bash
# Backend
uvicorn main:app --reload

# Frontend
cd frontend && npm run dev
```

No DB or view migration required for this pass.
