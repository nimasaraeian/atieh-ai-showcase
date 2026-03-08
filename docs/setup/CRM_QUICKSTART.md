# راهنمای سریع اتصال به CRM

## مراحل سریع

### 1. نصب وابستگی‌ها
```bash
pip install -r requirements.txt
```

### 2. تنظیم متغیرهای محیطی

#### Windows (PowerShell):
```powershell
$env:CRM_ENABLED="true"
$env:CRM_BASE_URL="https://crm.example.com/api"
$env:CRM_API_KEY="your-api-key-here"
$env:CRM_AUTH_TYPE="bearer"
```

#### Linux/Mac:
```bash
export CRM_ENABLED=true
export CRM_BASE_URL=https://crm.example.com/api
export CRM_API_KEY=your-api-key-here
export CRM_AUTH_TYPE=bearer
```

### 3. راه‌اندازی سرور
```bash
python run.py
```

### 4. تست اتصال
```bash
# بررسی وضعیت
curl http://localhost:8000/crm/status
```

یا در مرورگر:
```
http://localhost:8000/crm/status
```

### 5. همگام‌سازی داده‌ها

#### همگام‌سازی بیماران:
```bash
POST http://localhost:8000/crm/sync/patients
```

#### همگام‌سازی نوبت‌ها:
```bash
POST http://localhost:8000/crm/sync/appointments
```

## مثال کامل

### 1. تنظیمات در PowerShell (Windows):
```powershell
# تنظیم متغیرها
$env:CRM_ENABLED="true"
$env:CRM_BASE_URL="https://api.crm-clinic.com/v1"
$env:CRM_API_KEY="sk_live_abc123xyz789"
$env:CRM_AUTH_TYPE="bearer"

# راه‌اندازی سرور
python run.py
```

### 2. تست در Postman یا curl:
```bash
# بررسی وضعیت
curl http://localhost:8000/crm/status

# همگام‌سازی یک بیمار
curl -X POST http://localhost:8000/crm/sync/patient/1

# همگام‌سازی یک نوبت
curl -X POST http://localhost:8000/crm/sync/appointment/1
```

## نکات مهم

1. ✅ قبل از استفاده، مطمئن شوید که `CRM_ENABLED=true` است
2. ✅ URL و API Key را از مدیر CRM دریافت کنید
3. ✅ نوع احراز هویت را با CRM خود هماهنگ کنید
4. ✅ برای جزئیات بیشتر، فایل `CRM_SETUP.md` را مطالعه کنید

## عیب‌یابی

### مشکل: "CRM is not configured"
- بررسی کنید که `CRM_ENABLED=true` تنظیم شده باشد
- بررسی کنید که `CRM_BASE_URL` و `CRM_API_KEY` تنظیم شده باشند

### مشکل: "Error connecting to CRM"
- بررسی کنید که URL صحیح است
- بررسی کنید که API Key معتبر است
- بررسی کنید که CRM در دسترس است

### مشکل: "Timeout"
- مقدار `CRM_TIMEOUT` را افزایش دهید
- بررسی کنید که اتصال اینترنت برقرار است





