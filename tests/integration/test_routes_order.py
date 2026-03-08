"""
Regression test to ensure static routes under /appointments/ are not shadowed by dynamic routes.

This test prevents FastAPI route collision where /appointments/{appointment_id} would
capture requests meant for /appointments/suggestions and other static routes.
"""
import pytest
from fastapi.testclient import TestClient


def test_appointments_suggestions_not_shadowed(client):
    """
    Test that /appointments/suggestions is reachable and not captured by /appointments/{appointment_id}.
    
    Before fix: /appointments/suggestions would trigger integer parsing error (422)
    After fix: /appointments/suggestions returns proper response (200 or other valid status)
    """
    # Test with query parameters
    response = client.get("/appointments/suggestions?days_ahead=60&max_suggestions=2")
    
    # Should NOT return 422 (validation error from trying to parse "suggestions" as int)
    assert response.status_code != 422, \
        f"Route /appointments/suggestions is being shadowed by /appointments/{{appointment_id}}! " \
        f"Status: {response.status_code}, Response: {response.text[:200]}"
    
    # Should not contain integer parsing errors
    response_text = response.text.lower()
    assert "int" not in response_text or "parsing" not in response_text, \
        f"Response contains integer parsing error, indicating route shadowing: {response.text[:200]}"
    
    # Should be a valid status (200, 400, 500, etc. - just not 422)
    assert response.status_code in [200, 400, 404, 500], \
        f"Unexpected status code: {response.status_code}"


def test_appointments_static_routes_reachable(client):
    """
    Test that all static /appointments/* routes are reachable and not shadowed.
    """
    static_routes = [
        ("/appointments/suggest-time?treatment_type=T1&max_suggestions=5", [200, 400]),
        ("/appointments/next-available?treatment_type=T1", [200, 400, 404]),
        ("/appointments/suggestions?days_ahead=60&max_suggestions=10", [200, 400]),
        ("/appointments/available-slots?days_ahead=7&duration_minutes=30", [200]),
    ]
    
    for route, expected_statuses in static_routes:
        response = client.get(route)
        
        # None of these should return 422 (route shadowing error)
        assert response.status_code != 422, \
            f"Static route {route} is being shadowed! Status: {response.status_code}"
        
        # Should return one of the expected valid status codes
        assert response.status_code in expected_statuses, \
            f"Route {route} returned unexpected status {response.status_code}. " \
            f"Expected one of {expected_statuses}"


def test_appointments_dynamic_routes_still_work(client, seeded_db):
    """
    Test that dynamic /appointments/{appointment_id} routes still work after reordering.
    """
    # Test GET /appointments/{appointment_id}
    response = client.get("/appointments/1")
    assert response.status_code in [200, 404], \
        f"Dynamic route /appointments/1 returned unexpected status: {response.status_code}"
    
    # If appointment exists, verify response structure
    if response.status_code == 200:
        data = response.json()
        assert "id" in data or "appointment_id" in data, \
            "Response should contain appointment ID"


def test_route_order_correct():
    """
    Test that routes are defined in correct order in main.py.
    
    Static routes should come before dynamic routes to prevent shadowing.
    """
    import main
    from fastapi.routing import APIRoute
    
    appointments_routes = []
    for route in main.app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/appointments/"):
            appointments_routes.append(route.path)
    
    # Define expected order: all static routes before any dynamic routes
    static_patterns = [
        "/appointments/suggest-time",
        "/appointments/next-available", 
        "/appointments/suggestions",
        "/appointments/available-slots",
    ]
    
    dynamic_patterns = [
        "/appointments/{appointment_id}",
    ]
    
    # Find positions of first static and first dynamic route
    static_positions = []
    dynamic_positions = []
    
    for i, path in enumerate(appointments_routes):
        if any(pattern in path for pattern in static_patterns):
            static_positions.append(i)
        elif any(pattern in path for pattern in dynamic_patterns):
            dynamic_positions.append(i)
    
    # All static routes should come before all dynamic routes
    if static_positions and dynamic_positions:
        last_static = max(static_positions)
        first_dynamic = min(dynamic_positions)
        
        assert last_static < first_dynamic, \
            f"Route ordering error! Last static route is at position {last_static}, " \
            f"but first dynamic route is at position {first_dynamic}. " \
            f"All static routes must come before dynamic routes."


if __name__ == "__main__":
    # Allow running this test file standalone
    pytest.main([__file__, "-v"])
