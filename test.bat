@echo off
REM ============================================================
REM  HL7 Inspector - Run Test Suite
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo         Run setup.bat first.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  HL7 Inspector - Test Suite
echo ============================================
echo.

".venv\Scripts\python.exe" -m pytest -v

echo.
echo ============================================
echo  Done.
echo ============================================
pause
endlocal