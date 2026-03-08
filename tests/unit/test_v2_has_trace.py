"""
Test V2 Has Decision Trace
===========================
Ensures v2 results include full explainability trace with all components.
"""
import pytest
from app.engine.tvs.allocator import recommend_slots_v2
from app.engine.scoring import DataStore


@pytest.fixture
def data_store():
    """Create a DataStore with loaded CSV data."""
    ds = DataStore()
    ds.load_from_csv("data/outputs")
    return ds


@pytest.fixture
def slots():
    """Sample slots."""
    return [
        {
            'weekday': 'شنبه',
            'shift_code': 'D',
            'start_time': '09:00',
            'end_time': '09:30'
        },
        {
            'weekday': 'شنبه',
            'shift_code': 'D',
            'start_time': '10:00',
            'end_time': '10:30'
        },
        {
            'weekday': 'یکشنبه',
            'shift_code': 'E',
            'start_time': '14:00',
            'end_time': '14:30'
        }
    ]


@pytest.fixture
def request_params():
    """Sample request parameters with patient data."""
    return {
        'service_name': 'کشیدن دندان',
        'insurance_name': 'ایران',
        'backlog_title': 'درمان ریشه',
        'visit_count': 5,
        'total_revenue': 10_000_000,
        'no_show_risk': 0.1,
        'late_payment_risk': 0.05,
        'queue_days': 7,
        'adherence_rate': 0.9
    }


def test_v2_response_structure(slots, request_params, data_store):
    """Test v2 response has expected structure."""
    result = recommend_slots_v2(
        slots=slots,
        request_params=request_params,
        data_store=data_store,
        top_k=3
    )
    
    # Check top-level structure
    assert 'recommendations' in result
    assert 'meta' in result
    
    # Check meta
    meta = result['meta']
    assert meta['engine_version'] == 'v2'
    assert 'total_evaluated' in meta
    assert 'patient_tvs' in meta
    assert 'weights' in meta


def test_v2_has_trace_fields(slots, request_params, data_store):
    """Test v2 recommendations include all trace fields."""
    result = recommend_slots_v2(
        slots=slots,
        request_params=request_params,
        data_store=data_store,
        top_k=2
    )
    
    recommendations = result['recommendations']
    assert len(recommendations) > 0, "Should have at least one recommendation"
    
    for rec in recommendations:
        # Check recommendation structure
        assert hasattr(rec, 'slot')
        assert hasattr(rec, 'final_score')
        assert hasattr(rec, 'patient_tvs')
        assert hasattr(rec, 'slot_fit_score')
        assert hasattr(rec, 'trace')
        assert hasattr(rec, 'rank')
        
        # Check trace has all patient value components
        trace = rec.trace
        assert hasattr(trace, 'cis')
        assert hasattr(trace, 'cis_notes')
        assert hasattr(trace, 'ltvs')
        assert hasattr(trace, 'ltvs_notes')
        assert hasattr(trace, 'risk')
        assert hasattr(trace, 'risk_notes')
        assert hasattr(trace, 'fair')
        assert hasattr(trace, 'fair_notes')
        assert hasattr(trace, 'urg')
        assert hasattr(trace, 'urg_notes')
        assert hasattr(trace, 'patient_tvs')
        
        # Check trace has slot fit components
        assert hasattr(trace, 'slot_fit_score')
        assert hasattr(trace, 'slot_urgency')
        assert hasattr(trace, 'slot_financial')
        assert hasattr(trace, 'slot_availability')
        assert hasattr(trace, 'slot_complexity_fit')
        
        # Check trace has final score info
        assert hasattr(trace, 'final_score')
        assert hasattr(trace, 'patient_weight')
        assert hasattr(trace, 'slot_weight')
        assert hasattr(trace, 'engine_version')
        assert trace.engine_version == 'v2'


def test_trace_notes_not_empty(slots, request_params, data_store):
    """Test that trace notes contain meaningful information."""
    result = recommend_slots_v2(
        slots=slots,
        request_params=request_params,
        data_store=data_store,
        top_k=1
    )
    
    recommendations = result['recommendations']
    assert len(recommendations) > 0
    
    rec = recommendations[0]
    trace = rec.trace
    
    # All notes should be non-empty strings
    assert isinstance(trace.cis_notes, str) and len(trace.cis_notes) > 0
    assert isinstance(trace.ltvs_notes, str) and len(trace.ltvs_notes) > 0
    assert isinstance(trace.risk_notes, str) and len(trace.risk_notes) > 0
    assert isinstance(trace.fair_notes, str) and len(trace.fair_notes) > 0
    assert isinstance(trace.urg_notes, str) and len(trace.urg_notes) > 0


def test_trace_scores_consistent(slots, request_params, data_store):
    """Test that trace scores are consistent across recommendation."""
    result = recommend_slots_v2(
        slots=slots,
        request_params=request_params,
        data_store=data_store,
        top_k=2
    )
    
    recommendations = result['recommendations']
    assert len(recommendations) >= 2
    
    # Patient TVS should be the same across all recommendations (computed once)
    patient_tvs_values = [rec.patient_tvs for rec in recommendations]
    assert len(set(patient_tvs_values)) == 1, "Patient TVS should be same for all slots"
    
    # Trace patient_tvs should match recommendation patient_tvs
    for rec in recommendations:
        assert rec.patient_tvs == rec.trace.patient_tvs
        
        # Slot fit score should match trace
        assert rec.slot_fit_score == rec.trace.slot_fit_score
        
        # Final score should match trace
        assert rec.final_score == rec.trace.final_score


def test_rankings_assigned(slots, request_params, data_store):
    """Test that rankings are assigned correctly."""
    result = recommend_slots_v2(
        slots=slots,
        request_params=request_params,
        data_store=data_store,
        top_k=3
    )
    
    recommendations = result['recommendations']
    
    # Check rankings are sequential
    ranks = [rec.rank for rec in recommendations]
    assert ranks == list(range(1, len(recommendations) + 1))
    
    # Check scores are descending
    scores = [rec.final_score for rec in recommendations]
    assert scores == sorted(scores, reverse=True)


def test_empty_slots(request_params, data_store):
    """Test v2 with empty slots."""
    result = recommend_slots_v2(
        slots=[],
        request_params=request_params,
        data_store=data_store,
        top_k=5
    )
    
    assert result['recommendations'] == []
    assert result['meta']['engine_version'] == 'v2'
    assert result['meta']['total_evaluated'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
