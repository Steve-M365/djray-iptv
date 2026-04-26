@echo off
REM Quick setup script for apsattv-iptv (Windows)

echo === Apsattv IPTV Setup ===
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 is required but not installed.
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate venv and install
call venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt

REM Create output directory
mkdir output 2>nul

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit config.json if you want EPGshare (or use default iptvorg)
echo 2. Run: python main.py
echo 3. Run: python epg_generator.py
echo 4. Deploy output/ to GitHub Pages
echo.
pause
