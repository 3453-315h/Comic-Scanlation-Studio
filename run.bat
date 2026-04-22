@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo   Comic Scanlation Studio - Source Launcher
echo ========================================================

REM Check if venv exists
if not exist "venv" (
    echo [ERROR] Virtual environment 'venv' not found!
    echo Please run the setup script or create a venv and install requirements:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Activate venv
echo [INFO] Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate environment.
    pause
    exit /b 1
)

REM Run Application
echo [INFO] Starting Application...
echo.
python src\main.py
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo [ERROR] Application crashed or closed with error code: %errorlevel%
    echo ========================================================
    pause
) else (
    echo.
    echo [INFO] Application closed normally.
)