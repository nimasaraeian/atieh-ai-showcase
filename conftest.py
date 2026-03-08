"""
Root-level conftest: prevents the Windows crash
"ValueError: I/O operation on closed file" that occurs when the ASGI
TestClient's asyncio teardown closes sys.stdout before pytest finishes
writing its session-finish summary.

Two-pronged fix:
1. Wrap sys.stdout / sys.stderr at import time (catches early writes).
2. Re-wrap inside pytest_sessionfinish (catches the sys.stdout.flush()
   call in console_main that happens after capture teardown restores
   the original – now closed – file handle).
"""
import sys
import io


class _SafeIO:
    """Transparent proxy for a text stream; silently absorbs closed-file errors."""

    def __init__(self, wrapped):
        object.__setattr__(self, "_w", wrapped)

    def write(self, data):
        try:
            return object.__getattribute__(self, "_w").write(data)
        except (ValueError, OSError):
            return 0

    def flush(self):
        try:
            object.__getattribute__(self, "_w").flush()
        except (ValueError, OSError):
            pass

    def isatty(self):
        try:
            return object.__getattribute__(self, "_w").isatty()
        except (ValueError, OSError):
            return False

    def readable(self):
        return False

    def writable(self):
        return True

    def seekable(self):
        return False

    def fileno(self):
        return object.__getattribute__(self, "_w").fileno()

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_w"), name)

    def __setattr__(self, name, value):
        if name == "_w":
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, "_w"), name, value)


def _safe_wrap_std():
    """Replace sys.stdout/stderr with _SafeIO unless already wrapped."""
    if not isinstance(sys.stdout, _SafeIO):
        sys.stdout = _SafeIO(sys.stdout)
    if not isinstance(sys.stderr, _SafeIO):
        sys.stderr = _SafeIO(sys.stderr)


# Wrap at import time (before pytest terminal plugin captures sys.stdout).
_safe_wrap_std()


# Re-wrap at session finish: pytest's capture teardown may have restored
# the original (now potentially closed) handles just before console_main
# calls sys.stdout.flush().
def pytest_sessionfinish(session, exitstatus):
    _safe_wrap_std()
