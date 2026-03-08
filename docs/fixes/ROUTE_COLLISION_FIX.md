# FastAPI Route Collision Fix - Summary

## Problem

FastAPI routes are matched in the order they are defined. Dynamic routes like `/appointments/{appointment_id}` will capture **all** requests starting with `/appointments/` if defined before static routes.

### Original Route Order (INCORRECT)
```
1. /appointments/suggest-time           ✓ static
2. /appointments/{appointment_id}       ❌ dynamic (TOO EARLY)
3. /appointments/{appointment_id}/status ❌ dynamic (TOO EARLY)  
4. /appointments/next-available         ✗ SHADOWED
5. /appointments/suggestions            ✗ SHADOWED
6. /appointments/{appointment_id}/assign-suggestion ❌ dynamic
7. /appointments/available-slots        ✗ SHADOWED
8. /appointments/{appointment_id}/outcome ❌ dynamic
```

### Symptoms
- Requests to `/appointments/suggestions` → captured by `/{appointment_id}`
- FastAPI tries to parse "suggestions" as an integer → **422 Validation Error**
- Error message: `value is not a valid integer`

## Solution

Reordered routes in `main.py` so **all static routes come before any dynamic routes**.

### Fixed Route Order (CORRECT)
```
1. /appointments/suggest-time           ✓ static
2. /appointments/next-available         ✓ static
3. /appointments/suggestions            ✓ static
4. /appointments/available-slots        ✓ static
───────────────────────────────────────────────────
5. /appointments/{appointment_id}       ✓ dynamic
6. /appointments/{appointment_id}/status ✓ dynamic
7. /appointments/{appointment_id}/assign-suggestion ✓ dynamic
8. /appointments/{appointment_id}/outcome ✓ dynamic
```

## Changes Made

### 1. Reordered Routes in `main.py`

**Moved routes:**
- `/appointments/{appointment_id}` - moved from line 864 → 1003
- `/appointments/{appointment_id}/status` - moved from line 887 → 1026
- `/appointments/{appointment_id}/assign-suggestion` - moved from line 972 → 1047

**Result:** All 4 static routes now come before all 4 dynamic routes.

### 2. Created Regression Test

Created `tests/test_routes_order.py` with 4 tests:

1. **`test_appointments_suggestions_not_shadowed`**
   - Verifies `/appointments/suggestions` returns 200 (not 422)
   - Checks for absence of integer parsing errors

2. **`test_appointments_static_routes_reachable`**
   - Tests all 4 static routes are reachable
   - Verifies they return valid status codes (not 422)

3. **`test_appointments_dynamic_routes_still_work`**
   - Ensures `/appointments/{appointment_id}` still works correctly
   - Confirms no regression in existing functionality

4. **`test_route_order_correct`**
   - Programmatically verifies route order in FastAPI app
   - Ensures all static routes come before dynamic routes
   - Prevents future regressions

## Test Results

```bash
pytest tests/test_routes_order.py -v
```

**Result:** ✅ **4/4 tests PASSED**

```
tests/test_routes_order.py::test_appointments_suggestions_not_shadowed PASSED
tests/test_routes_order.py::test_appointments_static_routes_reachable PASSED
tests/test_routes_order.py::test_appointments_dynamic_routes_still_work PASSED
tests/test_routes_order.py::test_route_order_correct PASSED
```

### Key Verifications
- `/appointments/suggestions?days_ahead=60&max_suggestions=2` → **HTTP 200** ✓
- `/appointments/next-available?treatment_type=T1` → **HTTP 200** ✓
- `/appointments/available-slots?days_ahead=7` → **HTTP 200** ✓
- `/appointments/1` → **HTTP 200** ✓ (dynamic route still works)

## Manual Verification (Optional)

To manually verify in a running server:

```bash
# Start server
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Test static route (should return 200, not 422)
curl "http://127.0.0.1:8000/appointments/suggestions?days_ahead=60&max_suggestions=10"

# Test dynamic route (should still work)
curl "http://127.0.0.1:8000/appointments/1"
```

## Impact Assessment

### What Changed
- Route definition order in `main.py`
- Added regression test suite

### What Stayed the Same
- ✅ All endpoint logic unchanged
- ✅ All API contracts unchanged
- ✅ All request/response formats unchanged
- ✅ Dynamic routes still fully functional

### Breaking Changes
- ❌ **None** - This is purely a bug fix

## Technical Details

### Why Order Matters in FastAPI

FastAPI (Starlette) uses path pattern matching:
1. Routes are checked in definition order
2. First matching route wins
3. `/{param}` matches ANY path segment
4. Static paths must be defined first

### Route Pattern Matching Priority

```python
# WRONG ORDER (causes shadowing):
@app.get("/appointments/{appointment_id}")  # Matches EVERYTHING
@app.get("/appointments/suggestions")       # NEVER REACHED

# CORRECT ORDER:
@app.get("/appointments/suggestions")       # Matches "suggestions" exactly
@app.get("/appointments/{appointment_id}")  # Matches everything else
```

## Prevention

The regression test `test_route_order_correct()` programmatically verifies route order at runtime, preventing this issue from reoccurring in the future.

## Files Modified

1. **`main.py`** - Reordered routes (3 routes moved)
2. **`tests/test_routes_order.py`** - New regression test suite (137 lines)

## Related Documentation

- [FastAPI Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/)
- [Starlette Routing](https://www.starlette.io/routing/)

---

**Status:** ✅ **FIXED & TESTED**  
**Test Coverage:** 4/4 tests passing  
**Regression Prevention:** ✅ Automated test added
