@echo off
setlocal enabledelayedexpansion

:: Change to the directory where this script is located
cd /d "%~dp0"

title Roblox DataStore Manager - Installer
color 0B

echo.
echo ============================================================
echo    Roblox DataStore Manager - Advanced Open Cloud Tool
echo ============================================================
echo.
echo Current directory: %CD%
echo.
echo This installer will set up everything you need to run the
echo DataStore Manager application.
echo.
echo Press any key to continue or CTRL+C to cancel...
pause

echo.
echo [1/6] Checking for Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Installing Python...
    echo.
    echo Downloading Python installer...

    :: Download Python installer
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile 'python_installer.exe'}"

    if not exist python_installer.exe (
        echo ERROR: Failed to download Python installer!
        echo Please install Python 3.8+ manually from https://www.python.org
        pause
        exit /b 1
    )

    echo Installing Python (this may take a few minutes)...
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

    :: Clean up
    del python_installer.exe

    :: Refresh environment variables
    call refreshenv >nul 2>&1

    echo Python installed successfully!
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo Found: %%i
)

echo.
echo [2/6] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
)

echo.
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)
echo Virtual environment activated!

echo.
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo Pip upgraded!

echo.
echo [5/6] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    echo Trying with verbose output...
    pip install -r requirements.txt
    pause
    exit /b 1
)
echo Dependencies installed successfully!

echo.
echo [6/6] Creating necessary directories...
if not exist data mkdir data
if not exist backups mkdir backups
if not exist logs mkdir logs
echo Directories created!

echo.
echo ============================================================
echo                    INSTALLATION COMPLETE!
echo ============================================================
echo.
echo Your DataStore Manager is now ready to use!
echo.
echo To start the application:
echo   1. Double-click 'start.bat' OR
echo   2. Run 'python app.py' from command line
echo.
echo To build a standalone .exe:
echo   Double-click 'build_exe.bat'
echo.
echo Documentation:
echo   - README.md for full usage guide
echo   - Visit https://create.roblox.com/credentials for API keys
echo.
echo Press any key to exit...
pause
