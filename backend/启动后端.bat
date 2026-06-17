@echo off
chcp 65001 >nul
echo Starting Flask backend on http://0.0.0.0:8000 ...
cd /d "%~dp0"
python -m pip install -r requirements.txt
python app.py
pause
