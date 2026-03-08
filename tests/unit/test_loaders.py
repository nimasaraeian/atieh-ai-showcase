"""Tests for Atieh data loaders."""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.loaders.atieh_loader import (
    parse_doctor_shifts,
    parse_services_catalog,
    parse_unfinished_catalog,
    parse_insurance_priority,
    OUTPUT_DIR
)
from app.utils.fa_normalize import normalize_fa, extract_tags, split_doctors


class TestPersianNormalization:
    """Test Persian text normalization utilities."""
    
    def test_normalize_fa_basic(self):
        """Test basic Persian normalization."""
        assert normalize_fa("ي") == "ی"
        assert normalize_fa("ك") == "ک"
        assert normalize_fa("  text  ") == "text"
        assert normalize_fa("a    b") == "a b"
    
    def test_normalize_fa_digits(self):
        """Test Persian digit conversion."""
        assert normalize_fa("۱۲۳") == "123"
        assert normalize_fa("٤٥٦") == "456"
    
    def test_extract_tags(self):
        """Test tag extraction."""
        text, tags = extract_tags("دکتر احمدی (اطفال)")
        assert "دکتر احمدی" in text
        assert "اطفال" in tags
    
    def test_split_doctors(self):
        """Test splitting multiple doctor names."""
        doctors = split_doctors("دکتر احمدی - دکتر محمدی")
        assert len(doctors) == 2
        
        doctors = split_doctors("دکتر احمدی\nدکتر محمدی")
        assert len(doctors) == 2


class TestDataLoaders:
    """Test data loader functions."""
    
    def test_doctor_shifts_structure(self):
        """Test that doctor shifts CSV has correct structure."""
        try:
            df = parse_doctor_shifts()
            
            # Check it's non-empty
            assert len(df) > 0, "Doctor shifts DataFrame is empty"
            
            # Check required columns
            required_cols = ['weekday_fa', 'shift_code', 'doctor_name_raw', 
                           'doctor_name_norm', 'tags']
            for col in required_cols:
                assert col in df.columns, f"Missing column: {col}"
            
            # Check shift codes are valid
            valid_shifts = {'D', 'E', 'N'}
            assert df['shift_code'].isin(valid_shifts).all(), "Invalid shift codes found"
            
            print(f"✓ Doctor shifts test passed: {len(df)} entries")
            
        except FileNotFoundError:
            pytest.skip("Input file not found - skipping test")
    
    def test_services_catalog_structure(self):
        """Test that services catalog CSV has correct structure."""
        try:
            df = parse_services_catalog()
            
            # Check it's non-empty
            assert len(df) > 0, "Services catalog DataFrame is empty"
            
            # Check required columns
            required_cols = ['category', 'service_name', 'service_name_norm',
                           'default_duration_min', 'complexity_weight']
            for col in required_cols:
                assert col in df.columns, f"Missing column: {col}"
            
            # Check duration and complexity are reasonable
            assert df['default_duration_min'].min() >= 0, "Negative duration found"
            assert df['default_duration_min'].max() <= 300, "Unreasonably high duration found"
            assert df['complexity_weight'].min() >= 0, "Negative complexity found"
            assert df['complexity_weight'].max() <= 1.0, "Complexity > 1.0 found"
            
            print(f"✓ Services catalog test passed: {len(df)} entries")
            
        except FileNotFoundError:
            pytest.skip("Input file not found - skipping test")
    
    def test_unfinished_treatments_structure(self):
        """Test that unfinished treatments CSV has correct structure."""
        try:
            df = parse_unfinished_catalog()
            
            # Check it's non-empty
            assert len(df) > 0, "Unfinished treatments DataFrame is empty"
            
            # Check required columns
            required_cols = ['backlog_title', 'urgency_weight']
            for col in required_cols:
                assert col in df.columns, f"Missing column: {col}"
            
            # Check urgency is in valid range
            assert df['urgency_weight'].min() >= 0, "Negative urgency found"
            assert df['urgency_weight'].max() <= 1.0, "Urgency > 1.0 found"
            
            print(f"✓ Unfinished treatments test passed: {len(df)} entries")
            
        except FileNotFoundError:
            pytest.skip("Input file not found - skipping test")
    
    def test_insurance_priority_structure(self):
        """Test that insurance priority CSV has correct structure."""
        try:
            df = parse_insurance_priority()
            
            # Check it's non-empty
            assert len(df) > 0, "Insurance priority DataFrame is empty"
            
            # Check required columns
            required_cols = ['insurance_name', 'priority_score']
            for col in required_cols:
                assert col in df.columns, f"Missing column: {col}"
            
            # Check priority is in valid range
            assert df['priority_score'].min() >= 0, "Negative priority found"
            assert df['priority_score'].max() <= 1.0, "Priority > 1.0 found"
            
            print(f"✓ Insurance priority test passed: {len(df)} entries")
            
        except FileNotFoundError:
            pytest.skip("Input file not found - skipping test")


class TestOutputFiles:
    """Test that output CSV files exist and are valid."""
    
    def test_output_csvs_exist(self):
        """Test that all expected CSV files are created."""
        expected_files = [
            'doctor_shifts.csv',
            'services_catalog.csv',
            'unfinished_treatments.csv',
            'insurance_priority.csv'
        ]
        
        for filename in expected_files:
            filepath = OUTPUT_DIR / filename
            if filepath.exists():
                # Try to read it
                df = pd.read_csv(filepath)
                assert len(df) > 0, f"{filename} is empty"
                print(f"✓ {filename} exists and is valid ({len(df)} rows)")
            else:
                pytest.skip(f"{filename} not generated yet - run main() first")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
