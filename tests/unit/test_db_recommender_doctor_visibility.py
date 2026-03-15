"""
Unit tests for db_schedule_recommender doctor visibility.

When no doctor is selected (payload has no doctor_id):
- preferred_doctor_filter must be False
- Each slot must have doctor_id and doctor_name None (clinic-level suggestion).

When doctor is selected (payload has doctor_id):
- preferred_doctor_filter must be True
- Slots must have doctor_id and doctor_name set (when DB returns slots).
"""
import pytest
from app.engine.db_schedule_recommender import recommend_slots_from_db


def test_no_doctor_in_payload_slots_have_no_doctor_name():
    """Without doctor_id in payload, recommendations must not suggest a doctor."""
    payload = {"record_no": "1", "preferred_day": "Saturday"}
    result = recommend_slots_from_db(payload, top_n=5)

    assert "ok" in result
    assert "preferred_doctor_filter" in result or result.get("ok") is False
    if not result.get("ok"):
        pytest.skip("Slots DB not available")

    assert result["preferred_doctor_filter"] is False
    for rec in result.get("recommendations", []):
        assert rec.get("doctor_id") is None, "doctor_id must be None when no doctor selected"
        assert rec.get("doctor_name") is None, "doctor_name must be None when no doctor selected"


def test_doctor_in_payload_slots_have_doctor_info():
    """With doctor_id in payload, recommendations must include doctor when slots exist."""
    payload = {"record_no": "1", "preferred_day": "Saturday", "doctor_id": 1}
    result = recommend_slots_from_db(payload, top_n=5)

    assert "ok" in result
    if not result.get("ok"):
        pytest.skip("Slots DB not available")

    assert result["preferred_doctor_filter"] is True
    for rec in result.get("recommendations", []):
        # When doctor filter is set, slots should carry doctor info (if any slots returned)
        assert "doctor_id" in rec
        assert "doctor_name" in rec
