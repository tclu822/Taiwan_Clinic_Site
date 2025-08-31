@echo off
chcp 65001 >nul
echo Taiwan Map Application - Backend Starter
echo ================================================
echo.

REM Set Python path
set PYTHON_PATH=C:\Users\wwwtc\AppData\Local\Programs\Python\Python313\python.exe

REM Check if Python is installed
"%PYTHON_PATH%" --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.13.5
    pause
    exit /b 1
)

echo Starting backend service...
echo Service will start at http://localhost:8000
echo Press Ctrl+C to stop service
echo ------------------------------------------------

REM Start backend service
cd backend
"%PYTHON_PATH%" main.py

pause 