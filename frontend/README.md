# Atieh AI Frontend

Premium, production-style clinic operations UI for Atieh AI dental software.

## Stack

- React 19
- Vite 7
- Tailwind CSS 3
- Lucide React
- Recharts
- React Router

## Quick Start

**Option A – با بکند (فقط یک سرور)**  
1. `npm run build:backend`  
2. بکند را اجرا کنید: `uvicorn main:app`  
3. بروید به: **http://localhost:8000/app**  
4. وارد شوید (فقط نام کاربری کافی است) و نقش Receptionist را انتخاب کنید.

**Option B – حالت development (دو سرور)**  
1. `npm install && npm run dev`  
2. بکند را هم اجرا کنید.  
3. بروید به: **http://localhost:5173**

## API Proxy

In development, requests to `/api`, `/ai`, `/patients`, `/financial`, `/appointments` are proxied to the backend at `http://127.0.0.1:8000`. Start the FastAPI backend before using the frontend.

## Build

```bash
npm run build
npm run preview   # serve production build
```

## Encoding check

Before commit, run to detect mojibake in `frontend/src`:

```bash
npm run check:encoding
# or from repo root:
python scripts/check_encoding.py
```

## Routes

| Path | Page |
|------|------|
| `/login` | Login (role: Receptionist, Doctor, Manager) |
| `/receptionist` | Receptionist Panel (patient search, AI slots) |
| `/doctor` | Doctor Panel (schedule, patients) |
| `/manager` | Manager Dashboard (KPIs, charts) |

## API Integration

- `POST /ai/engine/recommend-slot` – AI slot recommendations
- `GET /api/staff/patients/search` – Patient search
- `GET /api/manager/dashboard/summary` – Dashboard summary
- `GET /api/manager/patients/top-value` – Top patients
- `GET /ai/engine/catalog/services` – Services list
- `GET /ai/engine/catalog/insurances` – Insurances list
