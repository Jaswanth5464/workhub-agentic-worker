@echo off
echo Starting AI Task Worker Project...
echo =======================================

echo Starting HR Backend Server (FastAPI on Port 8000)...
start "HR Backend (FastAPI)" cmd /c "set PYTHONPATH=. && uvicorn backend_hr:app --reload --host 0.0.0.0 --port 8000"

echo Starting AI Agent Backend Server (FastAPI on Port 8001)...
start "AI Agent Backend (FastAPI)" cmd /c "set PYTHONPATH=. && python start_agent.py"

echo Starting HR Frontend (WorkHub UI on Port 3000)...
start "HR Frontend (WorkHub UI)" cmd /c "cd workhub_project\frontend && python -m http.server 3000"

echo Starting AI Agent Frontend (Execution Flow UI on Port 3002)...
start "AI Agent Frontend" cmd /c "cd frontend-ai && python server.py"

echo =======================================
echo All 4 servers started successfully in separate terminals!
echo.
echo [1] HR Dashboard UI:    http://localhost:3000
echo [2] AI Agent UI:        http://localhost:3002
echo [3] HR API Docs:        http://localhost:8000/docs
echo [4] Agent API Docs:     http://localhost:8001/docs
echo.
echo Leave the popup terminal windows open to keep the servers running.
pause
