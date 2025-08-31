@echo off
chcp 65001 >nul
echo Taiwan Map Application - Frontend Starter
echo ================================================
echo.
echo Note: Please ensure backend service is running at http://localhost:8000
echo ------------------------------------------------

REM Set Python path
set PYTHON_PATH=C:\Users\wwwtc\AppData\Local\Programs\Python\Python313\python.exe

REM Start frontend service
cd frontend
"%PYTHON_PATH%" -m http.server 8080

pause 