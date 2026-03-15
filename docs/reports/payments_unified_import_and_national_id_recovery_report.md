# گزارش: Unified Payments Import + National ID Recovery Preparation

**فاز:** یک importer مشترک برای همه سال‌ها + آماده‌سازی بازیابی کد ملی  
**تاریخ:** بر اساس audit همه سال‌ها  
**وضعیت:** اسکریپت‌ها و SQLها آماده؛ بدون به‌روزرسانی نهایی `patient_id` روی payments.

---

## ۱. هدف فاز

1. **یک importer مشترک** برای همه فایل‌های `payments_<YEAR>_full.xlsx`
2. **یک staging table مشترک** برای ذخیره خام با column mapping ثابت
3. **record_no اختیاری:** اگر ستون «شماره پرونده» وجود داشت خوانده شود، وگرنه `NULL`؛ استخراج از نام بیمار فقط به‌صورت helper جدا و غیراجباری
4. **سال و منبع** برای هر رکورد: `shamsi_year`, `source_file`
5. **جدول نرمال‌شده کد ملی** و **جدول میانی تطابق** با `patients.national_id`؛ خروجی فقط در جدول میانی، بدون update نهایی روی payments
6. **آمارهای مشخص‌شده** برای ارزیابی پوشش بازیابی کد ملی

---

## ۲. فایل‌های ایجادشده

| فایل | توضیح |
|------|--------|
| `sql/unified_payments_staging_schema.sql` | اسکیمای جدول‌های `payments_unified_staging`, `payments_national_id_normalized`, `payments_national_id_patient_match` |
| `scripts/unified_payments_import.py` | Importer مشترک: خواندن همه اکسل‌های سالانه و پر کردن `payments_unified_staging` |
| `scripts/national_id_recovery_prep.py` | نرمال‌سازی کد ملی، تطابق با `patients.national_id`، پر کردن جدول میانی و چاپ آمار |
| `sql/national_id_recovery_stats.sql` | کوئری‌های تأیید برای آمار (قابل اجرای دستی) |

---

## ۳. ساختار جدول‌ها

### ۳.۱ `payments_unified_staging`

- **id** (PK)
- **source_file**, **shamsi_year**, **row_number**, **sheet_name**, **loaded_at**
- **parse_status**, **parse_error**
- **patient_name_raw**, **phone_raw**, **national_id_raw**, **net_received_raw**
- **record_no** (nullable – برای سال‌هایی مثل ۱۴۰۳ که ستون جدا ندارند، `NULL`)
- **appointment_date_raw**, **insurer_raw**, **amount_patient_raw**, **amount_insurer_raw**

نقشه ستون‌ها ثابت است: موبايل، كد ملي، خالص دريافتي، نام بيمار، تاريخ پذيرش؛ شماره پرونده در صورت وجود.

### ۳.۲ `payments_national_id_normalized`

- **staging_id** (FK به `payments_unified_staging`)
- **national_id_raw**, **national_id_norm** (فقط رقم، ۱۰ کاراکتر)
- **is_valid** (۱ اگر طول ۱۰ رقم باشد)

### ۳.۳ `payments_national_id_patient_match` (جدول میانی)

- **staging_id**, **national_id_norm**
- **patient_id** (فقط برای `match_status = 'single'`؛ در حالت collision خالی)
- **match_status**: `'single'` | `'collision'` | `'no_match'`

هیچ به‌روزرسانی روی `payments_clean` یا جدول نهایی پرداخت انجام نمی‌شود.

---

## ۴. نحوه اجرا

### پیش‌نیاز

- مسیر دیتابیس: متغیر محیطی `ATIEH_DB_PATH` یا `DB_PATH` یا به‌طور پیش‌فرض `atieh_clinic.db` در ریشه ریپو
- اسکریپت‌ها اسکیمای مورد نیاز را در صورت وجود فایل `sql/unified_payments_staging_schema.sql` اعمال می‌کنند.

### مرحله ۱: Import یکپارچه

```bash
cd <repo>
set ATIEH_DB_PATH=atieh_clinic_recovery81_test.db
python scripts/unified_payments_import.py
```

- همه فایل‌های `data/inputs/payments/payments_*_full.xlsx` خوانده و در `payments_unified_staging` درج می‌شوند.
- برای هر فایل، در صورت وجود رکورد قبلی با همان `source_file`، ابتدا آن رکوردها حذف و دوباره بارگذاری می‌شوند (idempotent per file).
- **نکته:** به‌دلیل حجم زیاد اکسل‌ها (ده‌ها مگابایت)، اجرای کامل import ممکن است چند دقیقه تا بیش از ۱۰ دقیقه طول بکشد.

### مرحله ۲: آماده‌سازی بازیابی کد ملی

```bash
python scripts/national_id_recovery_prep.py
```

- از `payments_unified_staging` جدول `payments_national_id_normalized` پر می‌شود (نرمال‌سازی فقط رقم، ۱۰ رقمی).
- تطابق با `patients.national_id` (با نرمال یکسان) انجام و نتیجه در `payments_national_id_patient_match` ذخیره می‌شود.
- آمارهای زیر در خروجی چاپ می‌شوند.

### مرحله ۳: تأیید دستی آمار (اختیاری)

```bash
sqlite3 atieh_clinic_recovery81_test.db < sql/national_id_recovery_stats.sql
```

---

## ۵. آمارهای خروجی (۱۰ مورد)

پس از اجرای `national_id_recovery_prep.py` این مقادیر گزارش می‌شوند:

| # | توضیح | منبع |
|---|--------|------|
| 1 | تعداد کل سطرهای staging | `COUNT(*) FROM payments_unified_staging` |
| 2 | تعداد national_id معتبر (۱۰ رقمی نرمال) | `payments_national_id_normalized WHERE is_valid = 1` |
| 3 | تعداد تطابق با patients (فقط single) | `payments_national_id_patient_match WHERE match_status = 'single'` |
| 4 | تعداد بیمار یکتای تطابق‌یافته | `COUNT(DISTINCT patient_id)` برای single |
| 5 | تعداد collision (یک کد ملی → چند بیمار) | `match_status = 'collision'` |
| 6 | تعداد بدون تطابق | `match_status = 'no_match'` |
| 7 | پوشش به‌دست‌آمده با کد ملی (تعداد سطر با single match) | همان تعداد single |

در اسکریپت به‌صورت زیر چاپ می‌شود:

- **Total staging rows**
- **Valid national_id (10-digit)**
- **Match with patients (single)**
- **Unique patients matched**
- **Collision (nid→multiple)**
- **No match**
- **Coverage gained by NID**

---

## ۶. record_no و استخراج از نام بیمار

- در importer اگر ستون «شماره پرونده» در فایل وجود نداشته باشد (مثل ۱۴۰۳)، مقدار `record_no` در staging به‌صورت `NULL` ذخیره می‌شود.
- تابع کمکی **غیراجباری** در کد: `extract_record_no_from_patient_name(patient_name_raw)` برای استخراج عدد داخل پرانتز انتهای نام (مثلاً `نام(12345)` → `12345`). این تابع در خط لوله import فراخوانی نمی‌شود و فقط برای استفاده اختیاری در مراحل بعد (مثلاً برای سال ۱۴۰۳) آماده است.

---

## ۷. جمع‌بندی

- **Importer مشترک:** یک اسکریپت با نقشه ستون ثابت برای همه سال‌ها.
- **Staging مشترک:** یک جدول با `source_file` و `shamsi_year` برای هر رکورد.
- **record_no:** اختیاری؛ در صورت نبود ستون، `NULL`؛ استخراج از نام فقط به‌صورت helper جدا.
- **بازیابی کد ملی:** نرمال‌سازی ۱۰ رقمی، تطابق با `patients.national_id`، ذخیره فقط در جدول میانی؛ **بدون update نهایی patient_id روی payments**.
- با اجرای اسکریپت‌ها و (در صورت تمایل) `sql/national_id_recovery_stats.sql` می‌توان همان ۱۰ آمار را مشاهده و در گزارش نهایی جایگذاری کرد.

---

## ۸. نمونه خروجی آمار (پس از اجرا)

پس از اجرای واقعی، خروجی اسکریپت شبیه زیر خواهد بود (اعداد بسته به دیتابیس و فایل‌های اکسل متفاوت است):

```
─── National ID Recovery Prep Stats ───
  Total staging rows:            XXXXX
  Valid national_id (10-digit):  XXXXX
  Match with patients (single): XXXXX
  Unique patients matched:      XXXXX
  Collision (nid→multiple):     XXXXX
  No match:                     XXXXX
  Coverage gained by NID:       XXXXX rows
```

این اعداد را می‌توان در همین گزارش در بخش «نمونه خروجی آمار» درج کرد.
