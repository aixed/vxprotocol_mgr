@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
REM Strip trailing backslash for clean concatenation
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM Start BOTH backend (port 8000) and frontend dev server (port 5173) in separate windows.
REM NOTE: call the bat files directly with start - no nested cmd /k quoting hell.
REM Each inner bat ends with 'pause' so its window stays open.
start "Backend (Flask :8000)" /D "%ROOT%\backend" "%ROOT%\backend\启动后端.bat"
timeout /t 2 /nobreak >nul
start "Frontend (Vite :5173)" /D "%ROOT%\frontend" "%ROOT%\frontend\启动前端.bat"
echo Both servers launching. Open http://localhost:5173 in your browser.
endlocal
pause
