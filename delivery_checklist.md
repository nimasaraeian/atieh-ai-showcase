# Atieh AI — Delivery Checklist

Use this checklist before handing off the system for local use.

## Pre-delivery

- [ ] **API starts successfully** — Run `run_api.bat` or:
  ```
  python -m uvicorn main:app --host 127.0.0.1 --port 8000
  ```
  No import/runtime errors; API responds at http://127.0.0.1:8000

- [ ] **Watcher starts successfully** — Run `run_watcher.bat` (with API running) or:
  ```
  python watchers/folder_watcher.py
  ```
  No errors; prints "Watching: C:\AtiehAI\incoming"

- [ ] **Incoming folder exists** — `C:\AtiehAI\incoming` is present (create if missing)

- [ ] **Processed folder exists** — `C:\AtiehAI\processed` is present (or will be created by import)

- [ ] **Failed folder** — Optional: `C:\AtiehAI\failed` for failed imports

## Import flow

- [ ] **Import runs** — Drop a test .csv or .xlsx file in `C:\AtiehAI\incoming`; watcher triggers import

- [ ] **Refresh runs** — Check API response for `"refresh": { "ok": true, ... }` (or at least `"refresh"` present)

- [ ] **Decision log is written** — Query DB:
  ```
  sqlite3 atieh_clinic_working.db "SELECT * FROM decision_logs ORDER BY id DESC LIMIT 5"
  ```

- [ ] **Test file moved to processed** — File no longer in incoming; appears in `C:\AtiehAI\processed`

## Database and dependencies

- [ ] **SQLite DB present** — `atieh_clinic_working.db` exists in project root

- [ ] **No broken runtime dependency** — Run:
  ```
  pip install -r requirements.txt
  python -c "import main; import watchers.folder_watcher; print('OK')"
  ```

## Optional

- [ ] **Health check** — `curl http://127.0.0.1:8000/health` returns `{"ok": true, ...}`

- [ ] **start_atieh_ai.bat** — Run once; both API and watcher start in separate windows
