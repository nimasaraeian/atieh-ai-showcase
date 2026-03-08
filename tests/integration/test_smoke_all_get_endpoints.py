"""
Smoke test: exercise every GET endpoint in the OpenAPI schema.

Rules:
- Acceptable status codes: 200, 404, 422  (any 5xx = test failure)
- Path params replaced with safe defaults
- Minimal query params added per endpoint to avoid 422 validation errors
- Does NOT override the database; financial endpoints hit atieh_clinic.db directly
"""

import os
import re
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("CRM_MODE", "mock")
os.environ.setdefault("ENGINE_VERSION", "v1")

from main import app  # noqa: E402  (must follow env setup)

# ---------------------------------------------------------------------------
# Per-endpoint query param overrides
# Keys are exact OpenAPI path strings (with curly-brace params still present).
# ---------------------------------------------------------------------------
QUERY_PARAMS: dict[str, dict] = {
    "/ai/financial/status": {
        "sample_limit": 2,
    },
    "/ai/financial/top-recordnos": {
        "limit": 5,
        "min_lifetime": 1,
    },
    "/ai/financial/top-recordnos-explain": {
        "limit": 5,
        "min_lifetime": 1,
    },
    "/ai/financial/top-recordnos-explain-mixed": {
        "vip": 1,
        "high": 1,
        "medium": 1,
        "low": 1,
        "min_lifetime": 1,
        "fill_shortage": "true",
    },
}

# Replacement values for path parameters
PATH_PARAM_DEFAULTS: dict[str, str] = {
    "run_id": "1",
    "record_no": "139990",
}

ACCEPTABLE_CODES = {200, 404, 422}


def _resolve_path(path: str) -> str:
    """Replace {param} placeholders with safe default values."""
    def replacer(match: re.Match) -> str:
        param = match.group(1)
        return PATH_PARAM_DEFAULTS.get(param, "1")

    return re.sub(r"\{(\w+)\}", replacer, path)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def smoke_client():
    """
    TestClient without any dependency override so that:
    - Financial endpoints (direct sqlite3) hit atieh_clinic.db as usual.
    - ORM endpoints use whatever database is configured (may return empty data,
      404, or 422 – all acceptable per smoke-test rules).

    Intentionally NOT used as a context manager: the `with TestClient(...) as c`
    pattern triggers Starlette's asyncio lifespan teardown at module cleanup
    time, which on Windows raises KeyboardInterrupt and causes pytest exit code 2
    (INTERRUPTED) when this test runs as part of a larger suite.
    """
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def all_get_routes(smoke_client):
    """Return list of (openapi_path, resolved_url, query_params) for every GET."""
    resp = smoke_client.get("/openapi.json")
    assert resp.status_code == 200, "Could not fetch /openapi.json"

    schema = resp.json()
    routes = []
    for path, methods in schema.get("paths", {}).items():
        if "get" in methods:
            resolved = _resolve_path(path)
            params = QUERY_PARAMS.get(path, {})
            routes.append((path, resolved, params))

    return routes


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_openapi_schema_is_reachable(smoke_client):
    resp = smoke_client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data
    assert len(data["paths"]) > 0


def test_all_get_endpoints_smoke(smoke_client, all_get_routes):
    """
    For every GET endpoint: assert status is 200, 404, or 422.
    Prints a summary table at the end.
    """
    results: list[dict] = []

    for openapi_path, url, params in all_get_routes:
        response = smoke_client.get(url, params=params)
        code = response.status_code
        ok = code in ACCEPTABLE_CODES
        results.append(
            {
                "path": openapi_path,
                "url": url,
                "params": params,
                "status": code,
                "ok": ok,
            }
        )

    # ── summary ──────────────────────────────────────────────────────────────
    total = len(results)
    passed_200 = sum(1 for r in results if r["status"] == 200)
    passed_4xx = sum(1 for r in results if r["status"] in {404, 422})
    failed = [r for r in results if not r["ok"]]

    print(f"\n{'='*60}")
    print(f"  Smoke test summary")
    print(f"{'='*60}")
    print(f"  Total GET endpoints : {total}")
    print(f"  Returned 200        : {passed_200}")
    print(f"  Returned 404/422    : {passed_4xx}")
    print(f"  Failures (5xx/other): {len(failed)}")
    if failed:
        print("\n  FAILED endpoints:")
        for r in failed:
            print(f"    [{r['status']}] {r['url']}  params={r['params']}")
    print(f"{'='*60}\n")

    # ── assertions ───────────────────────────────────────────────────────────
    failures_text = "\n".join(
        f"  [{r['status']}] {r['url']} (params={r['params']})" for r in failed
    )
    assert not failed, (
        f"{len(failed)} endpoint(s) returned unexpected status codes:\n"
        + failures_text
    )
