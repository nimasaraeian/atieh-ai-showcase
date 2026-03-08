# Running Tests

## Quick start (Windows)

```powershell
.\scripts\run_tests.ps1
```

Full output is saved to `pytest_run.txt` in the repo root.
The last 120 lines are also printed to the terminal after the run.

## Targeting a specific test file

```powershell
# Safe on all platforms once conftest.py patch is in place
python -m pytest tests/test_smoke_all_get_endpoints.py --tb=short
```

## Why the script + conftest patch are needed on Windows

On Windows, the ASGI `TestClient` (Starlette/FastAPI) shuts down an asyncio
event loop during test teardown. As a side-effect this closes `sys.stdout`.
When pytest then tries to write its session-finish summary it hits:

```
ValueError: I/O operation on closed file
```

### How the fix works

**`conftest.py` (repo root)** – loaded by pytest before any plugin writes to
the terminal:

- Wraps `sys.stdout` / `sys.stderr` with a `_SafeIO` proxy at import time,
  so early writes are safe.
- Registers a `pytest_sessionfinish` hook that re-wraps `sys.stdout` /
  `sys.stderr` after pytest's own capture teardown may have restored the
  original closed handle – this covers the final `sys.stdout.flush()` call
  in `console_main`.

**`scripts/run_tests.ps1`** – captures stdout + stderr into a PowerShell
variable **before** writing to `pytest_run.txt`. This keeps the pipe open for
the full duration of the subprocess and avoids `$ErrorActionPreference = Stop`
treating Python's stderr log lines as terminating errors.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |
| 2 | Session interrupted (pre-existing asyncio teardown issue in some test files) |
| 3 | Internal pytest error |
| 5 | No tests collected |

Exit code 2 from the full test suite is a pre-existing Windows/asyncio
interaction in tests unrelated to this project's API code.
The smoke test (`test_smoke_all_get_endpoints.py`) exits cleanly with code 0.

## Viewing results

```powershell
# Full log
Get-Content pytest_run.txt

# Last 120 lines (same as what the script prints)
Get-Content pytest_run.txt -Tail 120
```
