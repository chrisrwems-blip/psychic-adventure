@echo off
REM =============================================================
REM  DataCenter Submittal Review Platform - Windows Startup
REM =============================================================
REM  Double-click this file or run it from Command Prompt
REM =============================================================

echo ============================================
echo   DC Submittal Review Platform - Starting
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed.
    echo Download it from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during install!
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed.
    echo Download it from: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/4] Installing Python dependencies...
cd backend
pip install -r requirements.txt --quiet
cd ..

echo [2/4] Installing frontend dependencies...
cd frontend
call npm install --silent
cd ..

echo [3/4] Starting backend server...
cd backend
start "Backend Server" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
cd ..

REM Wait a moment for backend
echo      Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo [4/4] Starting frontend...
cd frontend
start "Frontend Server" cmd /k "npm run dev"
cd ..

echo.
echo ============================================
echo   ALL RUNNING!
echo ============================================
echo.
echo   Open your browser to:
echo.
echo     http://localhost:5173
echo.
echo   To stop: close the two black windows
echo            that opened, or run stop.bat
echo ============================================
echo.

REM Open browser automatically
timeout /t 3 /nobreak >nul
start http://localhost:5173

pause
