@echo off
title Universal Scraper Launcher
color 0A

echo ====================================================================
echo                    UNIVERSAL SCRAPER LAUNCHER
echo ====================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Get the directory where the batch file is located
cd /d "%~dp0"

echo [INFO] Current directory: %CD%
echo.

REM Check if the Python script exists
if not exist "universal.py" (
    echo [ERROR] scraper.py not found in the current directory!
    echo.
    echo Please make sure scraper.py is in the same folder as this batch file.
    echo Current location: %CD%
    echo.
    pause
    exit /b 1
)

echo [INFO] Found universal.py
echo.

REM Check if required packages are installed
echo [INFO] Checking dependencies...
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Some dependencies might be missing!
    echo.
    echo If the scraper fails, please run:
    echo   pip install playwright aiohttp beautifulsoup4 tqdm aiofiles requests pillow
    echo   playwright install chromium
    echo.
    pause
)

echo.
echo ====================================================================
echo                         LAUNCHING SCRAPER
echo ====================================================================
echo.

REM Run the Python script
python universal.py

echo.
echo ====================================================================
echo                         SCRAPER FINISHED
echo ====================================================================
echo.
pause