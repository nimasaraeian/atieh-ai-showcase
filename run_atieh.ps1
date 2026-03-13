cd C:\Users\USER\Documents\GitHub\atieh

Start-Process python -WindowStyle Hidden -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000"

Start-Sleep -Seconds 3

Start-Process "http://127.0.0.1:8000"