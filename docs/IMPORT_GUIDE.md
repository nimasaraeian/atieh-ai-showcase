# راهنمای Import فایل‌های تاریخی

## نصب Dependencies

```bash
pip install jdatetime openpyxl pandas
```

یا:

```bash
pip install -r requirements.txt
```

## ساختار پوشه‌ها

فایل‌های اکسل تاریخی را در پوشه‌های مربوط به سال قرار دهید:

```
data/
  inputs/
    history/
      1395/  
      1396/
      ...
      1404/
        نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx
```

## راه‌اندازی سرور

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

سرور به صورت خودکار migration ها را اجرا می‌کند.

## استفاده از API

### 1. Import فایل تاریخی

**Endpoint:** `POST /api/import/history`

**مثال با PowerShell:**

```powershell
$body = @{
    files = @(
        @{
            path = "data/inputs/history/1404/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx"
            year = 1404
            sheet = 0
        }
    )
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/history" `
    -Method POST `
    -Body $body `
    -ContentType "application/json; charset=utf-8"

$response | ConvertTo-Json
```

**مثال با curl (Git Bash/WSL):**

```bash
curl -X POST "http://127.0.0.1:8000/api/import/history" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{
    "files": [
      {
        "path": "data/inputs/history/1404/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx",
        "year": 1404,
        "sheet": 0
      }
    ]
  }'
```

**پاسخ نمونه:**

```json
{
  "import_run_id": 1,
  "status": "success",
  "stats": {
    "files_processed": 1,
    "files_success": 1,
    "files_failed": 0,
    "total_rows": 500,
    "total_success": 485,
    "total_errors": 15,
    "patients_created": 150,
    "appointments_created": 470
  },
  "error": null
}
```

### 2. لیست Import Runs

```bash
curl http://127.0.0.1:8000/api/import/runs
```

### 3. جزئیات یک Import Run

```bash
curl http://127.0.0.1:8000/api/import/runs/1
```

### 4. مشاهده خطاها

```bash
curl http://127.0.0.1:8000/api/import/runs/1/errors
```

### 5. آمار کلی

```bash
curl http://127.0.0.1:8000/api/import/stats
```

## ستون‌های پشتیبانی شده

سیستم به صورت خودکار ستون‌ها را با نام‌های مختلف تشخیص می‌دهد:

| فیلد | نام‌های ممکن در اکسل |
|------|---------------------|
| نام بیمار | نام بیمار، نام، بیمار، PatientName، نام و نام خانوادگی |
| موبایل | موبایل، تلفن، شماره تماس، Phone، شماره موبایل، تلفن همراه |
| کد ملی | کد ملی، NationalID، کدملی |
| تاریخ | تاریخ، تاریخ ویزیت، Date، تاریخ مراجعه |
| ساعت | ساعت، زمان، Time |
| پزشک | پزشک، دکتر، Doctor، نام پزشک |
| خدمات | خدمات، درمان، Service، نوع خدمت، خدمت |
| بیمه | بیمه، Insurance، نوع بیمه |
| وضعیت | وضعیت، Status |
| مدت زمان | مدت، Duration، مدت زمان |

## فرمت تاریخ و زمان

سیستم از فرمت‌های زیر پشتیبانی می‌کند:

**تاریخ شمسی:**
- `1404/01/15`
- `1404-01-15`
- `1404.01.15`
- با ارقام فارسی: `۱۴۰۴/۰۱/۱۵`

**زمان:**
- `14:30`
- `14.30`
- با ارقام فارسی: `۱۴:۳۰`

## Deduplication (جلوگیری از تکرار)

سیستم از hash برای جلوگیری از وارد کردن مجدد رکوردهای تکراری استفاده می‌کند.

Hash شامل این فیلدها است:
- نام بیمار (نرمال شده)
- شماره تلفن (نرمال شده)  
- کد ملی
- تاریخ و زمان
- نام پزشک
- نوع خدمت
- وضعیت

## Troubleshooting

### خطای فایل پیدا نشد

اطمینان حاصل کنید که:
1. مسیر فایل از `data/inputs/history/` شروع می‌شود
2. فایل در محل صحیح قرار دارد
3. نام فایل دقیقاً مطابق با نام واقعی است (حساس به حروف بزرگ/کوچک)

### خطای پارس تاریخ

اگر تاریخ‌ها پارس نمی‌شوند:
- بررسی کنید فرمت تاریخ درست است
- مطمئن شوید ستون تاریخ دارای مقدار است
- ارقام عربی/فارسی به صورت خودکار تبدیل می‌شوند

### بررسی خطاها

برای مشاهده دقیق خطاهای هر import:

```bash
curl http://127.0.0.1:8000/api/import/runs/[ID]/errors
```

## دیتابیس Tables

Import pipeline از جداول زیر استفاده می‌کند:

- `import_runs` - ثبت اجرای import ها
- `stg_appointments` - Staging برای رکوردهای خام
- `patients` - جدول نهایی بیماران
- `appointments` - جدول نهایی نوبت‌ها

## مثال کامل Import چند فایل

```powershell
$body = @{
    files = @(
        @{
            path = "data/inputs/history/1402/نوبت_دهی_1402.xlsx"
            year = 1402
            sheet = 0
        },
        @{
            path = "data/inputs/history/1403/نوبت_دهی_1403.xlsx"
            year = 1403
            sheet = 0
        },
        @{
            path = "data/inputs/history/1404/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx"
            year = 1404
            sheet = 0
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/import/history" `
    -Method POST `
    -Body $body `
    -ContentType "application/json; charset=utf-8"
```

## API Documentation

مستندات کامل API در این آدرس موجود است:

```
http://127.0.0.1:8000/docs
```

## لاگ‌ها

برای مشاهده لاگ‌های دقیق import، خروجی کنسول سرور را بررسی کنید.
