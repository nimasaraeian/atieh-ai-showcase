.PHONY: help install mock-data test run clean

help:
	@echo "Atieh Clinic Scheduling AI - Makefile Commands"
	@echo "==============================================="
	@echo ""
	@echo "  make install     - Install Python dependencies"
	@echo "  make mock-data   - Generate mock CRM data"
	@echo "  make test        - Run all tests"
	@echo "  make run         - Start development server (mock mode)"
	@echo "  make run-live    - Start development server (live CRM mode)"
	@echo "  make clean       - Clean temporary files"
	@echo ""

install:
	pip install -r requirements.txt

mock-data:
	python scripts/generate_mock_crm_data.py --patients 200 --appointments 1000

test:
	pytest tests/ -v

run:
	@echo "Starting server in MOCK mode..."
	CRM_MODE=mock uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-live:
	@echo "Starting server in LIVE mode..."
	@echo "WARNING: Make sure CRM environment variables are set!"
	CRM_MODE=live uvicorn main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".pytest_cache" -exec rm -rf {} +
	rm -f test_atieh.db
