@echo off
chcp 65001 >nul
REM Start frontend dev server (Vite) on http://localhost (port 80)
REM Note: port 80 requires admin privileges on Windows.
net session >nul 2>&1
if errorlevel 1 (
    echo ============================================================
    echo  [WARN] Not running as Administrator.
    echo  Vite needs admin rights to bind port 80.
    echo  Please right-click this file and choose "Run as administrator".
    echo ============================================================
    echo.
)
cd /d "%~dp0frontend"
echo Installing dependencies (if needed) ...
call npm install
echo Starting Vite dev server on port 80 ...
call npm run dev
pause
