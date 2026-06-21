@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
REM Strip trailing backslash for clean concatenation
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM ----- Admin check -----
net session >nul 2>&1
if errorlevel 1 (
    echo ============================================================
    echo  [WARN] Not running as Administrator.
    echo  Port 80 (frontend) requires admin rights.
    echo  Please right-click this file and choose "Run as administrator".
    echo ============================================================
    echo.
)

REM ----- Check npm / node -----
where npm >nul 2>&1
if errorlevel 1 (
    echo ============================================================
    echo  [ERROR] npm is not found.
    echo  Please install Node.js from https://nodejs.org
    echo ============================================================
    pause
    exit /b 1
)

REM Start BOTH backend (port 8000) and frontend dev server (port 80) in separate windows.
REM NOTE: call the bat files directly with start - no nested cmd /k quoting hell.
REM Each inner bat ends with 'pause' so its window stays open.
start "Backend (Flask :8000)" /D "%ROOT%\backend" "%ROOT%\backend\启动后端.bat"
timeout /t 2 /nobreak >nul
start "Frontend (Vite :80)" /D "%ROOT%\frontend" "%ROOT%\frontend\启动前端.bat"
echo Both servers launching. Open http://localhost in your browser.
endlocal
pause
