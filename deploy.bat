@echo off
REM ============================================================
REM  HL7 Inspector - Deploy to Vercel
REM ============================================================

setlocal
cd /d "%~dp0"

where vercel >nul 2>nul
if errorlevel 1 (
    echo [INFO] Vercel CLI not found. Installing...
    call npm install -g vercel
    if errorlevel 1 (
        echo [ERROR] Failed to install Vercel CLI. Is Node.js installed?
        echo         Download Node.js from https://nodejs.org/
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo  Deploying to Vercel
echo ============================================
echo.
echo  First deploy will open a browser to log in.
echo.

call vercel --prod

echo.
pause
endlocal