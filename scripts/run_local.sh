#!/bin/bash
# Local development startup script (Unix/Linux/Mac)

set -e

echo "====================================="
echo "Atieh Clinic Scheduling AI - Local Run"
echo "====================================="
echo ""

# Step 1: Generate mock data if not exists
if [ ! -f "data/mock/patients.json" ]; then
    echo "📊 Generating mock CRM data..."
    python scripts/generate_mock_crm_data.py --patients 200 --appointments 1000
    echo ""
fi

# Step 2: Set CRM mode to mock
export CRM_MODE=mock
echo "✓ CRM_MODE set to: mock"
echo ""

# Step 3: Run tests (optional)
if [ "$1" == "--test" ]; then
    echo "🧪 Running tests..."
    pytest tests/ -q
    echo ""
fi

# Step 4: Start server
echo "🚀 Starting FastAPI server..."
echo "   Server will be available at: http://localhost:8000"
echo "   API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
