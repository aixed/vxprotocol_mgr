@echo off
chcp 65001 >nul
REM Build frontend and run everything from a single Flask server on :8000
cd /d "%~dp0frontend"
echo [1/2] Building frontend ...
call npm install
call npm run build
if errorlevel 1 (
    echo Frontend build failed.
    pause
    exit /b 1
)
echo [2/2] Starting Flask (it will serve both API and built frontend) ...
cd /d "%~dp0backend"
call 启动后端.bat
