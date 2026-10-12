@echo off
echo ========================================================
echo  Starting Bulk Certificate Generator (Backend + Frontend)
echo ========================================================

echo Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "CertFlow Backend (FastAPI)" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting CertFlow Frontend on http://localhost:5173 ...
start "CertFlow Frontend (Vite)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Both servers launched in separate terminal windows!
echo Backend Docs: http://127.0.0.1:8000/docs
echo Frontend UI:   http://localhost:5173
echo ========================================================
