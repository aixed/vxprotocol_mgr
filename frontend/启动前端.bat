@echo off
chcp 65001 >nul
REM Start frontend dev server (Vite) on http://localhost (port 80)
REM Note: port 80 requires admin privileges on Windows.

REM ----- Admin check -----
net session >nul 2>&1
if errorlevel 1 (
    echo ============================================================
    echo  [WARN] Not running as Administrator.
    echo  Vite needs admin rights to bind port 80.
    echo  Please right-click this file and choose "Run as administrator".
    echo ============================================================
    echo.
)

REM ----- Detect frontend directory -----
REM Try: same-dir/frontend, same-dir/../frontend, same-dir/../frontend
for %%A in ("%~dp0.") do set "PARENT=%%~dpA"
for %%A in ("%~dp0..") do set "GRANDPARENT=%%~dpA"

set "FRONTEND_DIR="
if exist "%~dp0frontend\" (
    set "FRONTEND_DIR=%~dp0frontend"
) else if exist "%PARENT%frontend\" (
    set "FRONTEND_DIR=%PARENT%frontend"
) else if exist "%GRANDPARENT%frontend\" (
    set "FRONTEND_DIR=%GRANDPARENT%frontend"
)

if not defined FRONTEND_DIR (
    echo ============================================================
    echo  [ERROR] Cannot find the frontend folder.
    echo  Looked in:
    echo    %~dp0frontend
    echo    %PARENT%frontend
    echo    %GRANDPARENT%frontend
    echo.
    echo  Make sure this batch file is inside the project root,
    echo  or inside the frontend folder.
    echo ============================================================
    pause
    exit /b 1
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

REM ----- Run -----
cd /d "%FRONTEND_DIR%"
echo Using frontend dir: %FRONTEND_DIR%
echo Installing dependencies (if needed) ...
call npm install
echo Starting Vite dev server on port 80 ...
call npm run dev
pause
