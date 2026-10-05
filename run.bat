@echo off
REM ============================================================
REM  HL7 Inspector - Run Development Server
REM  Starts uvicorn on http://localhost:8000
REM ============================================================

setlocal
cd /d "%~dp0"

REM --- Sanity check ---
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo         Run setup.bat first.
    pause
    exit /b 1
)

if not exist "app\main.py" (
    echo [ERROR] app\main.py not found. Are you in the project root?
    pause
    exit /b 1
)

echo.
echo ============================================
echo  HL7 Inspector
echo ============================================
echo.
echo  Starting server at http://localhost:8000
echo.
echo  Press Ctrl+C to stop.
echo.

REM --- Open browser after a short delay (in background) ---
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

REM --- Run uvicorn ---
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

REM --- If uvicorn exits, pause so user can read the error ---
echo.
echo Server stopped.
pause
endlocal