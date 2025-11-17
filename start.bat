@echo off
setlocal enabledelayedexpansion

:: Change to the directory where this script is located
cd /d "%~dp0"

title Roblox DataStore Manager
color 0A

echo.
echo ============================================================
echo    Roblox DataStore Manager - Starting...
echo ============================================================
echo.
echo Current directory: %CD%
echo.

:: Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found!
    echo Please run install.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Check if dependencies are installed
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Dependencies not installed!
    echo Please run install.bat first.
    pause
    exit /b 1
)

echo Starting server...
echo.
echo ============================================================
echo    Server running at: http://127.0.0.1:5000
echo    Press Ctrl+C to stop the server
echo ============================================================
echo.

:: Open browser after a short delay
start /b cmd /c "timeout /t 2 >nul && start http://127.0.0.1:5000"

:: Start the application
python app.py

:: Deactivate when done
call venv\Scripts\deactivate.bat
