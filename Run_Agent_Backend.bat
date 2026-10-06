@echo off
echo ===================================================
echo      STARTING AUTONOMOUS AI AGENT BACKEND ONLY
echo ===================================================
echo.
echo Make sure your WorkHub frontend/backend and the AI Frontend
echo are already running in other windows!
echo.

set PYTHONPATH=%CD%
python start_agent.py

pause
