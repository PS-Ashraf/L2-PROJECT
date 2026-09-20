@echo off
echo Starting Daily Planner Agent...

:: Start Backend in a new terminal window
start cmd /k "echo Starting Backend... && python -m venv venv && call venv\Scripts\activate.bat && pip install -r requirements.txt && cd backend && uvicorn main:app --reload"

:: Start Frontend in a new terminal window
start cmd /k "echo Starting Frontend... && cd frontend && npm install && npm run dev"

echo.
echo =================================================================
echo   Servers are starting in separate windows...
echo.
echo   Frontend (UI) will be available at: http://localhost:5173
echo   Backend (API) will be available at: http://localhost:8000
echo =================================================================
echo.
pause
