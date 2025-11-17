@echo off
title Roblox DataStore Manager - Build Executable
color 0E

echo.
echo ============================================================
echo    Building Standalone Executable
echo ============================================================
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

:: Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building executable (this may take several minutes)...
echo.

:: Build the executable
pyinstaller --onefile ^
    --name "RobloxDataStoreManager" ^
    --icon "static/icon.ico" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "src;src" ^
    --hidden-import=waitress ^
    --hidden-import=flask ^
    --hidden-import=flask_cors ^
    --noconsole ^
    --clean ^
    app.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo                    BUILD COMPLETE!
echo ============================================================
echo.
echo Your executable is ready at:
echo   dist\RobloxDataStoreManager.exe
echo.
echo You can now distribute this single .exe file!
echo.

:: Create a distribution package
echo Creating distribution package...
if not exist dist\RobloxDataStoreManager mkdir dist\RobloxDataStoreManager
copy dist\RobloxDataStoreManager.exe dist\RobloxDataStoreManager\
xcopy /E /I /Y data dist\RobloxDataStoreManager\data\ >nul 2>&1
xcopy /E /I /Y backups dist\RobloxDataStoreManager\backups\ >nul 2>&1

echo.
echo Distribution package created at:
echo   dist\RobloxDataStoreManager\
echo.

pause
