@echo off
title ParkOS - Smart Parking Computing Platform
color 0B

echo =========================================================================
echo   ParkOS - Smart Parking Computing Platform
echo   BTech CSE CAPP (Computer Architecture & Parallel Processing) Project
echo =========================================================================
echo.

:: Check if Python is available in PATH
where python >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Python detected on system.
    echo [*] Checking dependencies...
    python -c "import flask" >nul 2>nul
    if %errorlevel% neq 0 (
        echo [*] Installing Flask backend...
        pip install flask
    )
    echo [*] Starting Python Flask backend server...
    start "" "http://127.0.0.1:5000"
    python app.py
) else (
    echo [!] Python is not in system PATH.
    echo [*] Launching ParkOS in Standalone Browser Emulation Mode...
    echo [*] All CAPP concepts, interactive map, and demo features are fully functional!
    start "" index.html
)

pause
