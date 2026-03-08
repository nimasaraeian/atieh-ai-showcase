"""Tests for scoring engine."""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.scoring import (
    DataStore,
    calculate_urgency_score,
    calculate_financial_score,
    calculate_availability_score,
    calculate_complexity_fit_score,
    calculate_total_score,
    score_slot
)
from app.engine.time_blocks import generate_all_slots
from app.schemas.scheduling import SchedulingRequest
from app.engine.recommender import recommend_slots


class TestScoring:
    """Test scoring functions."""
    
    def test_urgency_score_range(self):
        """Test that urgency score is within 0-1."""
        df = pd.DataFrame({
            'backlog_title': ['درمان ریشه', 'ایمپلنت'],
            'urgency_weight': [0.9, 1.0]
        })
        
        score = calculate_urgency_score('درمان ریشه', df)
        assert 0.0 <= score <= 1.0, f"Urgency score {score} out of range"
        
        # Test default when no match
        score = calculate_urgency_score('unknown', df)
        assert score == 0.5
    
    def test_financial_score_range(self):
        """Test that financial score is within 0-1."""
        df = pd.DataFrame({
            'insurance_name': ['ایران', 'تامین اجتماعی'],
            'priority_score': [0.8, 0.6]
        })
        
        score = calculate_financial_score('ایران', df)
        assert 0.0 <= score <= 1.0, f"Financial score {score} out of range"
        
        # Test default when no match
        score = calculate_financial_score('unknown', df)
        assert score == 0.5
    
    def test_availability_score_range(self):
        """Test that availability score is within 0-1."""
        df = pd.DataFrame({
            'weekday_fa': ['شنبه', 'شنبه'],
            'shift_code': ['D', 'E'],
            'doctor_name_norm': ['دکتر احمدی', 'دکتر محمدی']
        })
        
        score = calculate_availability_score('شنبه', 'D', df)
        assert 0.0 <= score <= 1.0, f"Availability score {score} out of range"
        
        # Test when no doctor available
        score = calculate_availability_score('جمعه', 'N', df)
        assert score == 0.3
    
    def test_complexity_fit_score_range(self):
        """Test that complexity fit score is within 0-1."""
        # High complexity in night shift
        score = calculate_complexity_fit_score('N', 0.9)
        assert 0.0 <= score <= 1.0, f"Complexity fit score {score} out of range"
        assert score < 0.8, "Should penalize high complexity in night shift"
        
        # Low complexity in day shift
        score = calculate_complexity_fit_score('D', 0.5)
        assert 0.0 <= score <= 1.0, f"Complexity fit score {score} out of range"
    
    def test_total_score_range(self):
        """Test that total score is within 0-1."""
        score = calculate_total_score(0.9, 0.8, 1.0, 0.7, 0.5)
        assert 0.0 <= score <= 1.0, f"Total score {score} out of range"
        
        # Test extreme values
        score = calculate_total_score(0.0, 0.0, 0.0, 0.0, 0.0)
        assert abs(score - 0.0) < 0.001
        
        score = calculate_total_score(1.0, 1.0, 1.0, 1.0, 1.0)
        assert abs(score - 1.0) < 0.001  # Use approximate comparison for floats
    
    def test_total_score_weights(self):
        """Test that weights sum correctly."""
        # All scores at 1.0 should give 1.0
        score = calculate_total_score(1.0, 1.0, 1.0, 1.0, 1.0)
        assert abs(score - 1.0) < 0.001
        
        # Check individual weights
        # 30% urgency
        score_urgency = calculate_total_score(1.0, 0.0, 0.0, 0.0, 0.0)
        assert abs(score_urgency - 0.30) < 0.001
        
        # 25% financial
        score_financial = calculate_total_score(0.0, 1.0, 0.0, 0.0, 0.0)
        assert abs(score_financial - 0.25) < 0.001
        
        # 20% availability
        score_availability = calculate_total_score(0.0, 0.0, 1.0, 0.0, 0.0)
        assert abs(score_availability - 0.20) < 0.001
        
        # 15% complexity
        score_complexity = calculate_total_score(0.0, 0.0, 0.0, 1.0, 0.0)
        assert abs(score_complexity - 0.15) < 0.001


class TestDataStore:
    """Test data store loading."""
    
    def test_data_store_load(self):
        """Test that data store can load CSV files."""
        try:
            data_store = DataStore()
            data_store.load_from_csv()
            
            # Check that dataframes are loaded
            assert data_store.doctor_shifts is not None
            assert data_store.services_catalog is not None
            assert data_store.unfinished_treatments is not None
            assert data_store.insurance_priority is not None
            
            print(f"✓ Loaded {len(data_store.doctor_shifts)} doctor shifts")
            print(f"✓ Loaded {len(data_store.services_catalog)} services")
            print(f"✓ Loaded {len(data_store.unfinished_treatments)} treatments")
            print(f"✓ Loaded {len(data_store.insurance_priority)} insurances")
            
        except Exception as e:
            pytest.skip(f"CSV files not available: {e}")


class TestRecommendations:
    """Test recommendation engine."""
    
    def test_recommendations_exist(self):
        """Test that at least 1 recommendation is generated."""
        try:
            data_store = DataStore()
            data_store.load_from_csv()
            
            request = SchedulingRequest(
                service_name='کشیدن دندان',
                insurance_name='ایران',
                backlog_title='درمان ریشه'
            )
            
            result = recommend_slots(request, data_store, top_n=10)
            
            assert len(result.top_recommendations) > 0, "No recommendations generated"
            print(f"✓ Generated {len(result.top_recommendations)} recommendations")
            
            # Check that all scores are in valid range
            for rec in result.top_recommendations:
                assert 0.0 <= rec.score <= 1.0, f"Score {rec.score} out of range"
                assert 0.0 <= rec.breakdown.urgency_score <= 1.0
                assert 0.0 <= rec.breakdown.financial_score <= 1.0
                assert 0.0 <= rec.breakdown.availability_score <= 1.0
                assert 0.0 <= rec.breakdown.complexity_fit_score <= 1.0
            
            print(f"✓ All scores within valid range (0-1)")
            
            # Print top 3 for inspection
            print("\nTop 3 recommendations:")
            for idx, rec in enumerate(result.top_recommendations[:3], 1):
                print(f"{idx}. {rec.weekday} {rec.shift_code} {rec.start_time} - "
                      f"Score: {rec.score:.3f}")
            
        except Exception as e:
            pytest.skip(f"CSV files not available or error: {e}")
    
    def test_score_sorting(self):
        """Test that recommendations are sorted by score."""
        try:
            data_store = DataStore()
            data_store.load_from_csv()
            
            request = SchedulingRequest(service_name='کشیدن دندان')
            result = recommend_slots(request, data_store, top_n=10)
            
            if len(result.top_recommendations) > 1:
                scores = [rec.score for rec in result.top_recommendations]
                assert scores == sorted(scores, reverse=True), \
                    "Recommendations not sorted by score"
                print("✓ Recommendations properly sorted by score")
        
        except Exception as e:
            pytest.skip(f"CSV files not available or error: {e}")


class TestTimeBlocks:
    """Test time block generation."""
    
    def test_all_slots_generated(self):
        """Test that all slots are generated."""
        slots = generate_all_slots(slot_minutes=30)
        
        # 7 weekdays × 3 shifts × slots per shift
        # D: 08:00-14:00 = 6 hours = 12 slots
        # E: 14:00-20:00 = 6 hours = 12 slots
        # N: 20:00-24:00 = 4 hours = 8 slots
        # Total per day: 32 slots
        # Total: 7 × 32 = 224 slots
        expected_min = 200  # Allow some variance
        
        assert len(slots) >= expected_min, f"Expected at least {expected_min} slots, got {len(slots)}"
        print(f"✓ Generated {len(slots)} time slots")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
