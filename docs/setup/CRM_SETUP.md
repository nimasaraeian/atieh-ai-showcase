# راهنمای اتصال به CRM کلینیک

این راهنما نحوه اتصال سیستم نوبت‌دهی به CRM کلینیک را توضیح می‌دهد.

## پیش‌نیازها

1. **اطلاعات اتصال CRM:**
   - URL پایه API CRM (مثال: `https://crm.example.com/api`)
   - API Key یا Token برای احراز هویت
   - نوع احراز هویت (Bearer Token، API Key، یا Basic Auth)

2. **نصب کتابخانه requests:**
   ```bash
   pip install requests
   ```

## تنظیمات

### روش 1: استفاده از متغیرهای محیطی (توصیه می‌شود)

متغیرهای محیطی را در سیستم عامل خود تنظیم کنید:

#### Windows (PowerShell):
```powershell
$env:CRM_ENABLED="true"
$env:CRM_BASE_URL="https://crm.example.com/api"
$env:CRM_API_KEY="your-api-key-here"
$env:CRM_AUTH_TYPE="bearer"
```

#### Windows (Command Prompt):
```cmd
set CRM_ENABLED=true
set CRM_BASE_URL=https://crm.example.com/api
set CRM_API_KEY=your-api-key-here
set CRM_AUTH_TYPE=bearer
```

#### Linux/Mac:
```bash
export CRM_ENABLED=true
export CRM_BASE_URL=https://crm.example.com/api
export CRM_API_KEY=your-api-key-here
export CRM_AUTH_TYPE=bearer
```

### روش 2: استفاده از فایل `.env`

1. فایل `.env` را در ریشه پروژه ایجاد کنید:
```env
CRM_ENABLED=true
CRM_BASE_URL=https://crm.example.com/api
CRM_API_KEY=your-api-key-here
CRM_AUTH_TYPE=bearer
CRM_USERNAME=your-username
CRM_PASSWORD=your-password
CRM_TIMEOUT=30
```

2. نصب کتابخانه `python-dotenv`:
```bash
pip install python-dotenv
```

3. در ابتدای `app.py` اضافه کنید:
```python
from dotenv import load_dotenv
load_dotenv()
```

## متغیرهای محیطی

| متغیر | توضیحات | مثال | الزامی |
|------|---------|------|--------|
| `CRM_ENABLED` | فعال/غیرفعال کردن همگام‌سازی | `true` یا `false` | بله |
| `CRM_BASE_URL` | URL پایه API CRM | `https://crm.example.com/api` | بله |
| `CRM_API_KEY` | کلید API یا Token | `abc123xyz...` | بله |
| `CRM_AUTH_TYPE` | نوع احراز هویت | `bearer`, `api_key`, `basic` | خیر (پیش‌فرض: `bearer`) |
| `CRM_USERNAME` | نام کاربری (برای Basic Auth) | `admin` | در صورت Basic Auth |
| `CRM_PASSWORD` | رمز عبور (برای Basic Auth) | `password123` | در صورت Basic Auth |
| `CRM_TIMEOUT` | Timeout برای درخواست‌ها (ثانیه) | `30` | خیر (پیش‌فرض: 30) |
| `CRM_ENDPOINT_PATIENTS` | Endpoint بیماران | `/patients` | خیر (پیش‌فرض: `/patients`) |
| `CRM_ENDPOINT_APPOINTMENTS` | Endpoint نوبت‌ها | `/appointments` | خیر (پیش‌فرض: `/appointments`) |

## انواع احراز هویت

### 1. Bearer Token (پیش‌فرض)
```env
CRM_AUTH_TYPE=bearer
CRM_API_KEY=your-token-here
```
Header: `Authorization: Bearer your-token-here`

### 2. API Key
```env
CRM_AUTH_TYPE=api_key
CRM_API_KEY=your-api-key-here
```
Header: `X-API-Key: your-api-key-here`

### 3. Basic Authentication
```env
CRM_AUTH_TYPE=basic
CRM_USERNAME=your-username
CRM_PASSWORD=your-password
```

## استفاده از API

### بررسی وضعیت اتصال
```bash
GET /crm/status
```

### همگام‌سازی بیماران
```bash
# همگام‌سازی تمام بیماران
POST /crm/sync/patients?limit=100

# همگام‌سازی یک بیمار خاص
POST /crm/sync/patient/1
```

### همگام‌سازی نوبت‌ها
```bash
# همگام‌سازی تمام نوبت‌ها
POST /crm/sync/appointments?limit=100

# همگام‌سازی نوبت‌های با وضعیت خاص
POST /crm/sync/appointments?limit=100&status=pending

# همگام‌سازی یک نوبت خاص
POST /crm/sync/appointment/1
```

### دریافت داده از CRM
```bash
# دریافت لیست بیماران از CRM
GET /crm/patients?limit=100

# دریافت لیست نوبت‌ها از CRM
GET /crm/appointments?start_date=2024-01-01&end_date=2024-12-31
```

## همگام‌سازی خودکار

برای فعال‌سازی همگام‌سازی خودکار هنگام ایجاد/به‌روزرسانی داده‌ها، می‌توانید در `app.py` hook اضافه کنید:

```python
# بعد از ایجاد بیمار
@app.post("/patients", response_model=PatientResponse)
async def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    # ... کد موجود ...
    
    # همگام‌سازی با CRM
    if crm_integration.config.is_configured():
        crm_integration.sync_patient(db_patient)
    
    return {...}
```

## فرمت داده‌های ارسالی

### فرمت Patient:
```json
{
    "id": 1,
    "name": "علی احمدی",
    "phone": "09123456789",
    "national_id": "1234567890",
    "payment_type": "cash",
    "first_visit_date": "2024-01-15T10:00:00",
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00"
}
```

### فرمت Appointment:
```json
{
    "id": 1,
    "patient_id": 1,
    "appointment_date": "2024-01-20T14:00:00",
    "duration_minutes": 30,
    "payment_type": "cash",
    "treatment_type": "treatment_1",
    "priority_score": 85.5,
    "ai_priority_score": 90.2,
    "status": "pending",
    "notes": "یادداشت اختیاری",
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00"
}
```

## عیب‌یابی

### بررسی لاگ‌ها
خطاهای اتصال به CRM در لاگ‌های سیستم ثبت می‌شوند. برای مشاهده:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### تست اتصال
```bash
# بررسی وضعیت
curl http://localhost:8000/crm/status

# تست همگام‌سازی یک بیمار
curl -X POST http://localhost:8000/crm/sync/patient/1
```

## نکات مهم

1. **امنیت:** هرگز API Key را در کد hard-code نکنید. همیشه از متغیرهای محیطی استفاده کنید.

2. **Rate Limiting:** برخی CRMها محدودیت تعداد درخواست دارند. در صورت نیاز، delay بین درخواست‌ها اضافه کنید.

3. **Error Handling:** سیستم به صورت خودکار خطاها را مدیریت می‌کند و در صورت عدم اتصال، عملیات ادامه می‌یابد.

4. **همگام‌سازی دوطرفه:** برای همگام‌سازی دوطرفه (دریافت داده از CRM)، باید endpointهای `/crm/patients` و `/crm/appointments` را استفاده کنید.

## پشتیبانی

در صورت بروز مشکل:
1. بررسی کنید که متغیرهای محیطی به درستی تنظیم شده‌اند
2. لاگ‌های سیستم را بررسی کنید
3. اتصال به CRM را با curl یا Postman تست کنید





