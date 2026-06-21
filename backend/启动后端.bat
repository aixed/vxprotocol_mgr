@echo off
chcp 65001 >nul
REM Start Flask backend on http://0.0.0.0:8000

REM ----- Check python -----
where python >nul 2>&1
if errorlevel 1 (
    echo ============================================================
    echo  [ERROR] python is not found.
    echo  Please install Python 3 from https://python.org
    echo ============================================================
    pause
    exit /b 1
)

REM ----- Check pip -----
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ============================================================
    echo  [WARN] pip is not available. Trying to run anyway...
    echo ============================================================
    echo.
)

cd /d "%~dp0"
echo Installing Python dependencies (if needed) ...
python -m pip install -r requirements.txt
echo Starting Flask backend on http://0.0.0.0:8000 ...
python app.py
pause
