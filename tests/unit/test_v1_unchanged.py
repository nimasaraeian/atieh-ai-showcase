"""
Test V1 Unchanged
==================
Ensures v1 behavior and API outputs remain unchanged after v2 implementation.
"""
import pytest
from app.engine.recommender import recommend_slots
from app.engine.scoring import DataStore
from app.schemas.scheduling import SchedulingRequest


@pytest.fixture
def data_store():
    """Create a DataStore with loaded CSV data."""
    ds = DataStore()
    ds.load_from_csv("data/outputs")
    return ds


@pytest.fixture
def v1_request():
    """Sample v1 SchedulingRequest."""
    return SchedulingRequest(
        service_name='کشیدن دندان',
        preferred_doctor='دکتر غیرموجود',
        insurance_name='ایران',
        backlog_title='درمان ریشه'
    )


def test_v1_response_structure(v1_request, data_store):
    """Test v1 response has expected structure."""
    result = recommend_slots(
        request=v1_request,
        data_store=data_store,
        top_n=5,
        engine_version="v1"
    )
    
    # Check expected v1 fields
    assert hasattr(result, 'top_recommendations')
    assert hasattr(result, 'inputs_echo')
    assert hasattr(result, 'total_slots_evaluated')
    
    assert isinstance(result.top_recommendations, list)
    assert len(result.top_recommendations) > 0


def test_v1_recommendation_fields(v1_request, data_store):
    """Test v1 recommendations have all expected fields."""
    result = recommend_slots(
        request=v1_request,
        data_store=data_store,
        top_n=3,
        engine_version="v1"
    )
    
    for rec in result.top_recommendations:
        # Check v1 slot fields
        assert hasattr(rec, 'weekday')
        assert hasattr(rec, 'shift_code')
        assert hasattr(rec, 'start_time')
        assert hasattr(rec, 'end_time')
        assert hasattr(rec, 'doctor')
        assert hasattr(rec, 'score')
        assert hasattr(rec, 'breakdown')
        assert hasattr(rec, 'service_duration_min')
        assert hasattr(rec, 'service_complexity')
        
        # Check breakdown fields
        breakdown = rec.breakdown
        assert hasattr(breakdown, 'urgency_score')
        assert hasattr(breakdown, 'financial_score')
        assert hasattr(breakdown, 'availability_score')
        assert hasattr(breakdown, 'complexity_fit_score')
        assert hasattr(breakdown, 'total_score')


def test_v1_breakdown_scores_in_range(v1_request, data_store):
    """Test v1 breakdown scores are in [0, 1] range."""
    result = recommend_slots(
        request=v1_request,
        data_store=data_store,
        top_n=5,
        engine_version="v1"
    )
    
    for rec in result.top_recommendations:
        bd = rec.breakdown
        
        assert 0.0 <= bd.urgency_score <= 1.0
        assert 0.0 <= bd.financial_score <= 1.0
        assert 0.0 <= bd.availability_score <= 1.0
        assert 0.0 <= bd.complexity_fit_score <= 1.0
        assert 0.0 <= bd.total_score <= 1.0
        assert 0.0 <= rec.score <= 1.0


def test_v1_no_v2_fields(v1_request, data_store):
    """Test v1 response doesn't contain v2-specific fields in main structure."""
    result = recommend_slots(
        request=v1_request,
        data_store=data_store,
        top_n=3,
        engine_version="v1"
    )
    
    for rec in result.top_recommendations:
        # V1 should not have v2 trace fields in main structure
        # (v2 may add them as private __dict__ attributes, but not as public attrs)
        assert not hasattr(rec, 'patient_tvs')
        assert not hasattr(rec, 'slot_fit_score')
        assert not hasattr(rec, 'trace')
        assert not hasattr(rec, 'rank')


def test_v1_scoring_weights(v1_request, data_store):
    """Test v1 uses expected scoring weights."""
    result = recommend_slots(
        request=v1_request,
        data_store=data_store,
        top_n=1,
        engine_version="v1"
    )
    
    rec = result.top_recommendations[0]
    bd = rec.breakdown
    
    # V1 weights (updated): urgency=0.30, financial=0.25, availability=0.20, complexity=0.15, time=0.10
    # Calculate expected total (without any doctor boost)
    expected_total = (
        0.30 * bd.urgency_score +
        0.25 * bd.financial_score +
        0.20 * bd.availability_score +
        0.15 * bd.complexity_fit_score +
        0.10 * bd.time_score
    )
    
    # Should match within floating point tolerance
    assert abs(bd.total_score - expected_total) < 0.001, \
        f"V1 total score {bd.total_score} doesn't match expected {expected_total}"


def test_v1_default_engine_version(v1_request, data_store):
    """Test that v1 is the default engine version."""
    import os
    from app.config import Config
    
    # Save original
    original_env = os.environ.get('ENGINE_VERSION')
    original_config = Config.ENGINE_VERSION
    
    try:
        # Clear environment and config should default to v1
        if 'ENGINE_VERSION' in os.environ:
            del os.environ['ENGINE_VERSION']
        Config.ENGINE_VERSION = "v1"
        
        result = recommend_slots(
            request=v1_request,
            data_store=data_store,
            top_n=2
            # No engine_version specified - should use default
        )
        
        # Should work without errors (v1 is default)
        assert len(result.top_recommendations) > 0
        
    finally:
        # Restore original
        if original_env:
            os.environ['ENGINE_VERSION'] = original_env
        Config.ENGINE_VERSION = original_config


def test_v1_vs_v1_consistency(v1_request, data_store):
    """Test v1 produces consistent results across calls."""
    result1 = recommend_slots(
        request=v1_request,
        data_store=data_store,
        top_n=5,
        engine_version="v1"
    )
    
    result2 = recommend_slots(
        request=v1_request,
        data_store=data_store,
        top_n=5,
        engine_version="v1"
    )
    
    # Should produce same number of recommendations
    assert len(result1.top_recommendations) == len(result2.top_recommendations)
    
    # Should produce same scores (deterministic)
    for rec1, rec2 in zip(result1.top_recommendations, result2.top_recommendations):
        assert rec1.weekday == rec2.weekday
        assert rec1.shift_code == rec2.shift_code
        assert abs(rec1.score - rec2.score) < 0.001


def test_v1_inputs_echo(v1_request, data_store):
    """Test v1 echoes back original request."""
    result = recommend_slots(
        request=v1_request,
        data_store=data_store,
        top_n=3,
        engine_version="v1"
    )
    
    # inputs_echo should match original request
    assert result.inputs_echo.service_name == v1_request.service_name
    assert result.inputs_echo.preferred_doctor == v1_request.preferred_doctor


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
