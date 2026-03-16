## Atieh AI deployment (Railway + Vercel)

### Backend (Railway)

- **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - A `Procfile` is included: `Procfile`

### Required environment variables

- **`ATIEH_DB_PATH`**: path to the SQLite DB file (recommended on Railway volume), e.g. `/data/atieh_clinic.db`
- **`FINANCIAL_DB_PATH`** (optional): override for financial DB; defaults to the same resolution chain as `ATIEH_DB_PATH`
- **`UPLOAD_BASE_DIR`**: base directory for uploads; defaults to `<repo_root>/data`
  - Files are stored under:
    - `inputs/history/`
    - `inputs/payments/`
    - `inputs/reference/`
    - `uploads_staging/`

### Persistent volume (recommended)

SQLite needs a persistent filesystem. On Railway, mount a volume (example path `/data`) and set:

- `ATIEH_DB_PATH=/data/atieh_clinic.db`
- `UPLOAD_BASE_DIR=/data` (optional, if you want uploads on the same volume)

### Health check

- `GET /health` returns a stable JSON payload for Railway health checks.

---

### Frontend (Vercel)

### Environment variables

- **`VITE_API_BASE`**: backend origin (Railway URL), e.g. `https://your-railway-app.up.railway.app`

### Build settings

- **Build command**: `npm run build`
- **Output directory**: `dist`

