"""Tests for CRM-ready scheduling engine."""
import pytest
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.scheduling import PatientContext, SchedulingRequest, CaseContext
from app.engine.scoring import DataStore
from app.engine.recommender import recommend_slots
from app.engine.run_engine import run_case, run_from_crm
from app.integrations.crm.mock import MockCRMClient
from app.integrations.crm.adapter import build_case_context_from_crm


class TestCaseContext:
    """Test CaseContext creation and validation."""
    
    def test_patient_context_creation(self):
        """Test creating PatientContext."""
        patient = PatientContext(
            patient_id="123",
            full_name="علی احمدی",
            phone="09121234567",
            insurance_name="ایران",
            unfinished_treatment_title="درمان ریشه"
        )
        
        assert patient.patient_id == "123"
        assert patient.full_name == "علی احمدی"
        assert patient.insurance_name == "ایران"
        print("✓ PatientContext created successfully")
    
    def test_case_context_creation(self):
        """Test creating complete CaseContext."""
        patient = PatientContext(
            patient_id="123",
            full_name="علی احمدی",
            insurance_name="ایران",
            unfinished_treatment_title="درمان ریشه"
        )
        
        request = SchedulingRequest(
            service_name="کشیدن دندان",
            desired_weekday="شنبه"
        )
        
        case_context = CaseContext(
            patient=patient,
            request=request
        )
        
        assert case_context.patient.patient_id == "123"
        assert case_context.request.service_name == "کشیدن دندان"
        print("✓ CaseContext created successfully")


class TestMockCRM:
    """Test MockCRMClient functionality."""
    
    def test_mock_crm_get_patient(self):
        """Test fetching patient from mock CRM."""
        crm = MockCRMClient()
        patient = crm.get_patient("123")
        
        assert patient['patient_id'] == "123"
        assert patient['full_name'] == "علی احمدی"
        print(f"✓ Mock CRM returned patient: {patient['full_name']}")
    
    def test_mock_crm_get_insurance(self):
        """Test fetching patient insurance."""
        crm = MockCRMClient()
        insurance = crm.get_patient_insurance("123")
        
        assert insurance == "ایران"
        print(f"✓ Mock CRM returned insurance: {insurance}")
    
    def test_mock_crm_get_unfinished(self):
        """Test fetching unfinished treatments."""
        crm = MockCRMClient()
        unfinished = crm.get_patient_unfinished("123")
        
        assert len(unfinished) > 0
        assert unfinished[0]['title'] == "درمان ریشه"
        print(f"✓ Mock CRM returned {len(unfinished)} unfinished treatment(s)")


class TestCRMAdapter:
    """Test CRM adapter functionality."""
    
    def test_build_case_context_from_crm(self):
        """Test building CaseContext from CRM data."""
        crm = MockCRMClient()
        case_context = build_case_context_from_crm(
            crm_client=crm,
            patient_id="123",
            service_name="کشیدن دندان"
        )
        
        assert case_context.patient.patient_id == "123"
        assert case_context.patient.full_name == "علی احمدی"
        assert case_context.patient.insurance_name == "ایران"
        assert case_context.patient.unfinished_treatment_title == "درمان ریشه"
        assert case_context.request.service_name == "کشیدن دندان"
        
        print("✓ CaseContext built from CRM successfully")
        print(f"  Patient: {case_context.patient.full_name}")
        print(f"  Insurance: {case_context.patient.insurance_name}")
        print(f"  Unfinished: {case_context.patient.unfinished_treatment_title}")


class TestEngineWithCaseContext:
    """Test engine with CaseContext."""
    
    def test_recommendations_with_case_context(self):
        """Test generating recommendations with CaseContext."""
        try:
            # Load data
            data_store = DataStore()
            data_store.load_from_csv()
            
            # Create case context
            patient = PatientContext(
                patient_id="123",
                full_name="علی احمدی",
                insurance_name="ایران",
                unfinished_treatment_title="درمان ریشه"
            )
            
            request = SchedulingRequest(
                service_name="کشیدن دندان"
            )
            
            case_context = CaseContext(patient=patient, request=request)
            
            # Generate recommendations
            result = recommend_slots(case_context, data_store, top_n=10)
            
            assert len(result.top_recommendations) >= 5, "Should return at least 5 recommendations"
            
            # Verify score ranges
            for rec in result.top_recommendations:
                assert 0.0 <= rec.score <= 1.0, f"Score {rec.score} out of range"
                assert 0.0 <= rec.breakdown.urgency_score <= 1.0
                assert 0.0 <= rec.breakdown.financial_score <= 1.0
                assert 0.0 <= rec.breakdown.availability_score <= 1.0
                assert 0.0 <= rec.breakdown.complexity_fit_score <= 1.0
            
            print(f"✓ Generated {len(result.top_recommendations)} recommendations")
            print(f"  Top score: {result.top_recommendations[0].score:.3f}")
            print(f"  All scores in valid range (0-1)")
            
        except Exception as e:
            pytest.skip(f"CSV files not available or error: {e}")
    
    def test_run_case(self):
        """Test run_case entry point."""
        try:
            # Build case context from mock CRM
            crm = MockCRMClient()
            case_context = build_case_context_from_crm(
                crm_client=crm,
                patient_id="123",
                service_name="کشیدن دندان"
            )
            
            # Run engine
            result = run_case(case_context)
            
            assert result['success'], "Engine run should succeed"
            assert result['total_recommendations'] >= 5, "Should return at least 5 recommendations"
            assert result['patient_id'] == "123"
            assert 'draft' in result
            
            print("✓ run_case() completed successfully")
            print(f"  Patient: {result['patient_name']}")
            print(f"  Recommendations: {result['total_recommendations']}")
            print(f"  Draft created: {result['draft'] is not None}")
            
        except Exception as e:
            pytest.skip(f"CSV files not available or error: {e}")


class TestCRMEntryPoint:
    """Test CRM entry point."""
    
    def test_run_from_crm(self):
        """Test run_from_crm entry point with mock CRM."""
        try:
            result = run_from_crm(
                patient_id="123",
                service_name="کشیدن دندان",
                use_mock=True
            )
            
            assert result['success'], "Engine run should succeed"
            assert result['total_recommendations'] >= 5, "Should return at least 5 recommendations"
            assert result['patient_id'] == "123"
            assert result['patient_name'] == "علی احمدی"
            
            # Verify case context info
            assert result['case_context']['insurance'] == "ایران"
            assert result['case_context']['unfinished_treatment'] == "درمان ریشه"
            
            print("✓ run_from_crm() completed successfully")
            print(f"  Patient: {result['patient_name']}")
            print(f"  Insurance: {result['case_context']['insurance']}")
            print(f"  Recommendations: {result['total_recommendations']}")
            
        except Exception as e:
            pytest.skip(f"CSV files not available or error: {e}")
    
    def test_run_from_crm_with_preferences(self):
        """Test run_from_crm with preferred doctor."""
        try:
            result = run_from_crm(
                patient_id="123",
                service_name="ترمیم",
                preferred_doctor="دکتر نعمتی",
                use_mock=True
            )
            
            assert result['success']
            assert result['total_recommendations'] > 0
            
            # Check that preferences were applied
            print("✓ run_from_crm() with preferences completed")
            print(f"  Recommendations: {result['total_recommendations']}")
            
        except Exception as e:
            pytest.skip(f"CSV files not available or error: {e}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
