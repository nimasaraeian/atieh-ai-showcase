# Route Collision Fix - Quick Reference

## Problem
`/appointments/suggestions` was returning 422 (validation error) instead of 200.

## Root Cause
Dynamic route `/appointments/{appointment_id}` was defined **before** static route `/appointments/suggestions`, causing FastAPI to try parsing "suggestions" as an integer.

## Solution
✅ Reordered routes in `main.py` - all static routes now come before dynamic routes

## Verification

### Quick Test
```bash
# Run regression tests
pytest tests/test_routes_order.py -v

# Expected: 4/4 tests PASSED
```

### Manual Test (if server is running)
```bash
# Should return 200 (not 422)
curl "http://localhost:8000/appointments/suggestions?days_ahead=60&max_suggestions=10"

# Should still work
curl "http://localhost:8000/appointments/1"
```

## New Route Order

**Static routes (always first):**
1. `/appointments/suggest-time`
2. `/appointments/next-available`
3. `/appointments/suggestions` ← **NOW WORKS**
4. `/appointments/available-slots`

**Dynamic routes (always last):**
5. `/appointments/{appointment_id}`
6. `/appointments/{appointment_id}/status`
7. `/appointments/{appointment_id}/assign-suggestion`
8. `/appointments/{appointment_id}/outcome`

## Files Changed
- `main.py` - Routes reordered (no logic changes)
- `tests/test_routes_order.py` - New regression test (prevents future issues)

## Status
✅ **FIXED** - All tests passing, no breaking changes
