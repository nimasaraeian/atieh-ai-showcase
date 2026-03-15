# گزارش: Phone Recovery Preparation

**فاز:** آماده‌سازی بازیابی تلفن (بدون به‌روزرسانی نهایی `patient_id`)  
**وابستگی:** وجود جدول `payments_unified_staging` (خروجی Unified Payments Import) و جدول `patients`.

---

## ۱. هدف

1. **Audit** روی `patients.phone`
2. ساخت جدول **patients_phone_normalized** و نرمال‌سازی به فرم **09xxxxxxxxx**
3. ساخت جدول **payments_phone_normalized** از `payments_unified_staging.phone_raw` و نرمال‌سازی به 09xxxxxxxxx
4. ساخت جدول **payments_phone_patient_match** با وضعیت‌های single / collision / no_match
5. خروجی **آمار** (۸ مورد) بدون اعمال به‌روزرسانی نهایی روی patient_id

---

## ۲. فایل‌های ایجادشده

| فایل | توضیح |
|------|--------|
| `sql/phone_recovery_prep_schema.sql` | اسکیمای `patients_phone_normalized`, `payments_phone_normalized`, `payments_phone_patient_match` |
| `scripts/phone_recovery_prep.py` | Audit بیماران، پر کردن دو جدول نرمال، ساخت جدول match و چاپ آمار |
| `sql/phone_recovery_prep_stats.sql` | کوئری‌های تأیید آمار |
| `docs/reports/payments_phone_recovery_prep_report.md` | این گزارش |

---

## ۳. ساختار جدول‌ها

### ۳.۱ patients_phone_normalized

| ستون | نوع | توضیح |
|------|-----|--------|
| id | INTEGER | PK |
| patient_id | INTEGER | FK → patients.id، یکتا |
| phone_raw | TEXT | مقدار خام patients.phone |
| phone_norm | TEXT | 09xxxxxxxxx (۱۱ رقم) یا NULL |
| is_valid | INTEGER | ۱ اگر phone_norm پر باشد |

### ۳.۲ payments_phone_normalized

| ستون | نوع | توضیح |
|------|-----|--------|
| id | INTEGER | PK |
| staging_id | INTEGER | FK → payments_unified_staging.id، یکتا |
| phone_raw | TEXT | از payments_unified_staging.phone_raw |
| phone_norm | TEXT | 09xxxxxxxxx یا NULL |
| is_valid | INTEGER | ۱ اگر phone_norm پر باشد |

### ۳.۳ payments_phone_patient_match

| ستون | نوع | توضیح |
|------|-----|--------|
| staging_id | INTEGER | FK → payments_unified_staging |
| phone_norm | TEXT | شماره نرمال‌شده |
| patient_id | INTEGER | فقط برای single؛ در collision و no_match مقدار NULL |
| match_status | TEXT | `'single'` \| `'collision'` \| `'no_match'` |

---

## ۴. نرمال‌سازی تلفن

- **خروجی معتبر:** فقط شماره‌های **۱۱ رقمی** با پیش‌وند **09** (09xxxxxxxxx).
- **ورودی‌های پشتیبانی‌شده:**
  - 9xxxxxxxxx → 09xxxxxxxxx
  - 09xxxxxxxxx → بدون تغییر
  - 98xxxxxxxxxx / +98... → 0 + ۹ رقم بعد از 98
- رقم‌های فارسی/عربی به انگلیسی تبدیل می‌شوند؛ در سلول‌های چندشماره‌ای فقط **اولین شماره معتبر** استفاده می‌شود.

---

## ۵. Audit بیماران (patients.phone)

اسکریپت قبل از پر کردن جدول‌ها این موارد را چاپ می‌کند:

- تعداد کل بیماران
- تعداد رکورد با phone پر (غیر خالی)
- تعداد شماره معتبر بعد از نرمال (09xxxxxxxxx)
- چند نمونه از مقادیر خام

---

## ۶. آمار خروجی (۸ مورد)

| # | توضیح | منبع |
|---|--------|------|
| 1 | تعداد کل سطرهای staging | COUNT(*) FROM payments_unified_staging |
| 2 | تعداد تلفن‌های نرمال معتبر در payments | payments_phone_normalized WHERE is_valid = 1 |
| 3 | تعداد تلفن‌های نرمال معتبر در patients | patients_phone_normalized WHERE is_valid = 1 |
| 4 | تعداد تطابق یک‌به‌یک (single) | match_status = 'single' |
| 5 | تعداد بیمار یکتای تطابق‌یافته | COUNT(DISTINCT patient_id) برای single |
| 6 | تعداد collision (یک شماره → چند بیمار) | match_status = 'collision' |
| 7 | تعداد بدون تطابق | match_status = 'no_match' |
| 8 | پوشش به‌دست‌آمده با تلفن | همان تعداد single |

---

## ۷. نحوه اجرا

**پیش‌نیاز:** اجرای Unified Payments Import تا جدول `payments_unified_staging` پر شده باشد.

```bash
set ATIEH_DB_PATH=atieh_clinic_recovery81_test.db
python scripts/phone_recovery_prep.py
```

تأیید دستی آمار:

```bash
sqlite3 atieh_clinic_recovery81_test.db < sql/phone_recovery_prep_stats.sql
```

---

## ۸. نمونه خروجی اجرا

خروجی نمونه اسکریپت (بسته به دیتابیس):

```
--- Audit: patients.phone ---
  Total patients:     140531
  Phone filled:       140531
  Valid (09xxxxxxxxx): 37970
  Sample raw:         '0017212682', '005755140', '009031366761', ...

--- Phone Recovery Prep Stats ---
  Total staging rows:              876054
  Valid normalized payment phones: ...
  Valid normalized patient phones: 37970
  Single matches:                  ...
  Unique patients matched:        ...
  Collisions:                      ...
  No match:                        ...
  Coverage gained by phone:       ... rows
```

تعداد **Valid normalized patient phones** کمتر از کل بیماران است چون فقط شماره‌های موبایل 09xxxxxxxxx معتبر شمرده می‌شوند؛ بقیه (مثلاً ثابت یا فرمت دیگر) در جدول نرمال با is_valid=0 ذخیره می‌شوند.

---

## ۹. جمع‌بندی

- **patient_id نهایی** روی هیچ جدول پرداخت یا staging به‌روزرسانی **نمی‌شود**؛ فقط جدول‌های میانی پر می‌شوند.
- خروجی فاز برای استفاده در مراحل بعدی (اتصال به record_no، ادغام با NID و غیره) آماده است.
- در صورت خالی بودن `payments_unified_staging`، آمار staging و payment phone صفر خواهد بود؛ آمار بیماران و جدول `patients_phone_normalized` همچنان معتبر است.
- اگر **Valid normalized payment phones** صفر باشد، بررسی کنید که `payments_unified_staging.phone_raw` از **Unified Payments Import** (ستون موبايل در اکسل) پر شده باشد؛ در غیر این صورت یا ستون خالی است یا فرمت دیگری دارد.
