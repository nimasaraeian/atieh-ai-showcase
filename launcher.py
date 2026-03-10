from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

import requests
import webview

# --------------------------------------------------
# Runtime mode
# --------------------------------------------------
FROZEN = getattr(sys, "frozen", False)

# In packaged mode, sys.executable points to desktop_app.exe
BASE_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent

# Runtime project root:
# - Packaged mode: use the folder containing desktop_app.exe
# - Script mode:   use the folder containing this launcher.py file
PROJECT_ROOT = BASE_DIR if FROZEN else Path(__file__).resolve().parent

API_HOST = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"
HEALTH_URL = f"{API_URL}/health"

STARTUP_LOG = BASE_DIR / "desktop_app_startup.log"
ERROR_LOG = BASE_DIR / "desktop_app_error.log"

PYTHON_EXE = sys.executable

api_process = None
watcher_process = None


# --------------------------------------------------
# Logging helpers
# --------------------------------------------------
def _log_startup(msg: str) -> None:
    try:
        with open(STARTUP_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
    except Exception:
        pass


def _log_error(msg: str) -> None:
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
    except Exception:
        pass


# --------------------------------------------------
# Environment / directories
# --------------------------------------------------
def ensure_directories() -> None:
    dirs = [
        r"C:\AtiehAI\incoming",
        r"C:\AtiehAI\processed",
        r"C:\AtiehAI\failed",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def configure_environment() -> None:
    """
    Force absolute paths so packaged mode does not accidentally use dist\desktop_app
    as the working project directory or a wrong SQLite database.
    """
    db_path = (PROJECT_ROOT / "atieh_clinic.db").resolve()
    financial_db_path = (PROJECT_ROOT / "atieh_clinic_working.db").resolve()

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["FINANCIAL_DB_PATH"] = str(financial_db_path)

    os.chdir(str(PROJECT_ROOT))

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    _log_startup(f"FROZEN={FROZEN}")
    _log_startup(f"BASE_DIR={BASE_DIR}")
    _log_startup(f"PROJECT_ROOT={PROJECT_ROOT}")
    _log_startup(f"DATABASE_URL={os.environ.get('DATABASE_URL', '')}")
    _log_startup(f"FINANCIAL_DB_PATH={os.environ.get('FINANCIAL_DB_PATH', '')}")
    _log_startup(f"CWD={os.getcwd()}")


# --------------------------------------------------
# Health check
# --------------------------------------------------
def api_running() -> bool:
    try:
        r = requests.get(HEALTH_URL, timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def wait_for_api(timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if api_running():
            return True
        time.sleep(1)
    return False


# --------------------------------------------------
# API startup
# --------------------------------------------------
def _run_uvicorn_in_thread() -> None:
    """
    Packaged mode:
    sys.executable points to desktop_app.exe, so subprocess([sys.executable, "-m", "uvicorn", ...])
    would fail. We run uvicorn in-process inside a daemon thread instead.
    """
    try:
        configure_environment()

        import uvicorn
        from main import app

        _log_startup("Starting uvicorn in packaged mode thread")
        uvicorn.run(
            app,
            host=API_HOST,
            port=API_PORT,
            reload=False,
            log_level="info",
        )
    except Exception as e:
        _log_error(f"API thread exception: {e}\n{traceback.format_exc()}")


def start_api() -> None:
    global api_process

    if api_running():
        _log_startup("API already running")
        return

    if FROZEN:
        _log_startup("Packaged mode detected - starting API in background thread")
        t = threading.Thread(target=_run_uvicorn_in_thread, daemon=True)
        t.start()
    else:
        _log_startup("Script mode detected - starting API via subprocess")
        api_process = subprocess.Popen(
            [
                PYTHON_EXE,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                API_HOST,
                "--port",
                str(API_PORT),
            ],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )


# --------------------------------------------------
# Watcher startup
# --------------------------------------------------
def _run_watcher_in_thread() -> None:
    try:
        configure_environment()

        import watchers.folder_watcher as fw

        _log_startup("Starting watcher in packaged mode thread")
        fw.start_watcher()
    except Exception as e:
        _log_error(f"Watcher thread exception: {e}\n{traceback.format_exc()}")


def start_watcher() -> None:
    global watcher_process

    if FROZEN:
        _log_startup("Packaged mode detected - starting watcher in background thread")
        t = threading.Thread(target=_run_watcher_in_thread, daemon=True)
        t.start()
    else:
        _log_startup("Script mode detected - starting watcher via subprocess")
        watcher_process = subprocess.Popen(
            [
                PYTHON_EXE,
                str(PROJECT_ROOT / "watchers" / "folder_watcher.py"),
            ],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )


# --------------------------------------------------
# Main app
# --------------------------------------------------
def main() -> None:
    print("Starting Atieh AI...")
    _log_startup("Application startup initiated")

    ensure_directories()
    configure_environment()

    start_api()

    _log_startup("Waiting for API health check")
    if not wait_for_api():
        _log_startup("API failed to start within timeout")
        print("API failed to start")
        sys.exit(1)

    _log_startup("API health check passed")

    start_watcher()
    _log_startup("Watcher startup requested")

    # Give watcher a brief moment to attach
    time.sleep(2)

    try:
        _log_startup("Creating desktop webview window")
        webview.create_window(
            title="Atieh AI",
            url=API_URL,
            width=1400,
            height=900,
            min_size=(1100, 700),
        )
        _log_startup("Starting webview")
        # Final production mode: no DevTools
        webview.start()
        _log_startup("Webview exited normally")
    except Exception as e:
        _log_error(f"Webview exception: {e}\n{traceback.format_exc()}")
        raise

    print("Atieh AI is ready")


if __name__ == "__main__":
    main()