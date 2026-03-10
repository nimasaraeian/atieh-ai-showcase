# Atieh AI — Runtime Guide

## What it does

Atieh AI is a clinic management system that:

- Accepts CSV/Excel files dropped into an incoming folder
- Imports data and refreshes analytical layers automatically
- Provides a web dashboard and API for patient/financial insights
- Runs fully offline on a local desktop

## Required components

- Python 3.10+
- Dependencies from `requirements.txt`
- SQLite database: `atieh_clinic_working.db` (in project root)
- Folders: `C:\AtiehAI\incoming` and `C:\AtiehAI\processed` (and optionally `C:\AtiehAI\failed`)

## Startup steps

### Option 1 — Separate terminals (recommended for troubleshooting)

1. **Start the API** (run first):
   ```
   run_api.bat
   ```
   Or manually:
   ```
   python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```

2. **Start the watcher** (after API is up):
   ```
   run_watcher.bat
   ```
   Or manually:
   ```
   python watchers/folder_watcher.py
   ```

### Option 2 — All-in-one

```
start_atieh_ai.bat
```
Starts API and watcher in separate windows.

## Folder flow

| Folder | Purpose |
|--------|---------|
| `C:\AtiehAI\incoming` | Drop CSV, XLSX, or XLS files here |
| `C:\AtiehAI\processed` | Successfully processed files are moved here |
| `C:\AtiehAI\failed` | Files that failed processing are moved here |

## API and watcher behavior

- **Watcher** polls `C:\AtiehAI\incoming` every 5 seconds
- When files are present, it calls `POST http://127.0.0.1:8000/imports/run`
- **Import endpoint** scans incoming, moves files, creates `import_runs_v1` records, and runs the Post-Import Refresh Engine
- **Refresh engine** updates analytical layers and logs to `refresh_runs`, `refresh_run_steps`, and `decision_logs`

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Dashboard (requires login) |
| `/login` | GET/POST | Login form |
| `/health` | GET | Health check |
| `/imports/run` | POST | Run import (triggered by watcher) |
| `/imports/history` | GET | Import history |

## Where logs are stored

All in `atieh_clinic_working.db`:

| Table | Purpose |
|-------|---------|
| `refresh_runs` | Post-import refresh runs |
| `refresh_run_steps` | Per-step results (patient features, financial identity, tiers, etc.) |
| `decision_logs` | Decision events (e.g. financial tier refresh) |
| `import_runs_v1` | Import file processing history |

## Troubleshooting

- **API won't start**
  - Ensure port 8000 is free: `netstat -an | findstr :8000`
  - Check Python and dependencies: `pip install -r requirements.txt`

- **Watcher does nothing**
  - Confirm API is running on http://127.0.0.1:8000
  - Ensure `C:\AtiehAI\incoming` exists and contains supported files (.csv, .xlsx, .xls)

- **Database file not found**
  - Ensure `atieh_clinic_working.db` exists in the project root, or create it from migrations.

- **Import returns 0 processed**
  - Supported extensions: .csv, .xlsx, .xls
  - Check `C:\AtiehAI\incoming` path and permissions
