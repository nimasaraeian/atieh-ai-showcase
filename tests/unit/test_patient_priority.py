# -*- coding: utf-8 -*-
"""Tests for patient priority config and scoring (tier, scheduling window, score computation)."""
import pytest

from app.engine.patient_priority_config import (
    get_scheduling_window_days,
    get_tier_for_score,
    get_tier_label,
    TIER_BANDS,
    SCHEDULING_WINDOWS,
)
from app.engine.patient_priority import compute_priority_profile


def test_tier_for_score():
    assert get_tier_for_score(90) == "P1"
    assert get_tier_for_score(85) == "P1"
    assert get_tier_for_score(72) == "P2"
    assert get_tier_for_score(60) == "P3"
    assert get_tier_for_score(48) == "P4"
    assert get_tier_for_score(35) == "P5"
    assert get_tier_for_score(20) == "P6"
    assert get_tier_for_score(10) == "P7"
    assert get_tier_for_score(0) == "P7"
    assert get_tier_for_score(None) == "P7"
    assert get_tier_for_score("x") == "P7"


def test_scheduling_window_days():
    assert get_scheduling_window_days("P1") == (0, 3)
    assert get_scheduling_window_days("P3") == (0, 7)
    assert get_scheduling_window_days("P7") == (14, 365)
    assert get_scheduling_window_days("unknown") == (0, 14)  # default P5


def test_tier_label():
    assert get_tier_label("P1") == "Elite"
    assert get_tier_label("P7") == "Low"
    assert get_tier_label("") == "Low"


def test_compute_priority_profile():
    raw = {
        "patient_id": 1,
        "record_no": "80123",
        "crm_patient_code": "80123",
        "patient_name": "Test",
        "insurance_name": "CASH",
        "visit_count": 20,
        "first_visit_year": 1398,
        "relationship_years": 6,
        "payment_count": 20,
        "lifetime_net_received": 50_000_000.0,
        "last_payment_date": "1403/05/01",
    }
    out = compute_priority_profile(raw, insurance_conn=None)
    assert out["patient_id"] == 1
    assert out["crm_patient_code"] == "80123"
    assert out["insurance_score"] == 100.0  # CASH
    assert 0 <= out["patient_priority_score"] <= 100
    assert out["patient_priority_tier"] in ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]
    assert out["scheduling_window_min_days"] >= 0
    assert out["scheduling_window_max_days"] >= out["scheduling_window_min_days"]
    assert "explanation_json" in out
