"""
Test TVS v2 Components Range Validation
========================================
Ensures all TVS components and final scores are in [0, 1] range.
"""
import pytest
from app.engine.tvs.patient_value import (
    compute_patient_tvs,
    compute_cis,
    compute_ltvs,
    compute_risk,
    compute_fair,
    compute_urg
)
from app.engine.tvs.slot_fit import compute_slot_fit
from app.engine.tvs.final_score import compute_final_score
from app.engine.scoring import DataStore


@pytest.fixture
def data_store():
    """Create a DataStore with loaded CSV data."""
    ds = DataStore()
    ds.load_from_csv("data/outputs")
    return ds


@pytest.fixture
def request_params():
    """Sample request parameters."""
    return {
        'service_name': 'کشیدن دندان',
        'insurance_name': 'ایران',
        'backlog_title': 'درمان ریشه',
        'visit_count': 5,
        'total_revenue': 10_000_000,
        'no_show_risk': 0.1,
        'late_payment_risk': 0.05,
        'queue_days': 7
    }


@pytest.fixture
def slot():
    """Sample slot."""
    return {
        'weekday': 'شنبه',
        'shift_code': 'D',
        'start_time': '09:00',
        'end_time': '09:30'
    }


def test_cis_in_range(request_params, data_store):
    """Test CIS is in [0, 1]."""
    cis, notes = compute_cis(request_params, None, data_store)
    assert 0.0 <= cis <= 1.0, f"CIS={cis} out of range [0, 1]"
    assert notes  # Should have trace notes


def test_ltvs_in_range(request_params):
    """Test LTVS is in [0, 1]."""
    ltvs, notes = compute_ltvs(request_params)
    assert 0.0 <= ltvs <= 1.0, f"LTVS={ltvs} out of range [0, 1]"
    assert notes


def test_risk_in_range(request_params):
    """Test RISK is in [0, 1]."""
    risk, notes = compute_risk(request_params)
    assert 0.0 <= risk <= 1.0, f"RISK={risk} out of range [0, 1]"
    assert notes


def test_fair_in_range(request_params):
    """Test FAIR is in [0, 1]."""
    fair, notes = compute_fair(request_params)
    assert 0.0 <= fair <= 1.0, f"FAIR={fair} out of range [0, 1]"
    assert notes


def test_urg_in_range(request_params, data_store):
    """Test URG is in [0, 1]."""
    urg, notes = compute_urg(request_params, data_store)
    assert 0.0 <= urg <= 1.0, f"URG={urg} out of range [0, 1]"
    assert notes


def test_patient_tvs_in_range(request_params, data_store):
    """Test Patient TVS is in [0, 1]."""
    result = compute_patient_tvs(request_params, None, data_store)
    
    assert 0.0 <= result.patient_tvs <= 1.0, f"patient_tvs={result.patient_tvs} out of range"
    assert 0.0 <= result.cis <= 1.0
    assert 0.0 <= result.ltvs <= 1.0
    assert 0.0 <= result.risk <= 1.0
    assert 0.0 <= result.fair <= 1.0
    assert 0.0 <= result.urg <= 1.0


def test_slot_fit_in_range(slot, request_params, data_store):
    """Test Slot Fit Score is in [0, 1]."""
    result = compute_slot_fit(slot, None, request_params, data_store)
    
    assert 0.0 <= result.slot_fit_score <= 1.0, f"slot_fit_score={result.slot_fit_score} out of range"
    assert 0.0 <= result.urgency_score <= 1.0
    assert 0.0 <= result.financial_score <= 1.0
    assert 0.0 <= result.availability_score <= 1.0
    assert 0.0 <= result.complexity_fit_score <= 1.0


def test_final_score_in_range():
    """Test Final Score is in [0, 1]."""
    # Test weighted mode
    result_weighted = compute_final_score(
        patient_tvs=0.7,
        slot_fit_score=0.6,
        mode="weighted",
        patient_weight=0.70,
        slot_weight=0.30
    )
    assert 0.0 <= result_weighted.final_score <= 1.0
    
    # Test multiplicative mode
    result_mult = compute_final_score(
        patient_tvs=0.7,
        slot_fit_score=0.6,
        mode="multiplicative"
    )
    assert 0.0 <= result_mult.final_score <= 1.0


def test_edge_cases():
    """Test edge cases with extreme values."""
    # Zero values
    result_zero = compute_final_score(
        patient_tvs=0.0,
        slot_fit_score=0.0,
        mode="weighted"
    )
    assert result_zero.final_score == 0.0
    
    # Max values
    result_max = compute_final_score(
        patient_tvs=1.0,
        slot_fit_score=1.0,
        mode="weighted"
    )
    assert result_max.final_score == 1.0
    
    # Mixed
    result_mixed = compute_final_score(
        patient_tvs=1.0,
        slot_fit_score=0.0,
        mode="weighted",
        patient_weight=0.7,
        slot_weight=0.3
    )
    assert 0.0 <= result_mixed.final_score <= 1.0


def test_default_values(data_store):
    """Test with minimal/default values."""
    # Minimal request params
    minimal_params = {
        'service_name': 'test'
    }
    
    result = compute_patient_tvs(minimal_params, None, data_store)
    
    # Should get defaults, all in range
    assert 0.0 <= result.patient_tvs <= 1.0
    assert 0.0 <= result.cis <= 1.0
    assert 0.0 <= result.ltvs <= 1.0
    assert 0.0 <= result.risk <= 1.0
    assert 0.0 <= result.fair <= 1.0
    assert 0.0 <= result.urg <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
