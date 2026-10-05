@echo off
REM ============================================================
REM  HL7 Inspector - First-Time Setup
REM  Creates venv, installs dependencies, writes config files.
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo  HL7 Inspector - Setup
echo ============================================
echo.

REM --- 1. Check for Python 3.11 ---
where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher 'py' not found.
    echo         Install Python 3.11 from https://www.python.org/downloads/
    pause
    exit /b 1
)

py -3.11 --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.11 not found.
    echo         Install it from https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [1/5] Found Python 3.11
py -3.11 --version
echo.

REM --- 2. Remove any broken venv ---
echo [2/5] Removing old .venv if present...
if exist ".venv" (
    rmdir /s /q ".venv"
)
echo      Done.
echo.

REM --- 3. Create fresh venv ---
echo [3/5] Creating new virtual environment...
py -3.11 -m venv .venv
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] venv creation failed.
    pause
    exit /b 1
)
echo      Created .venv
echo.

REM --- 4. Write requirements.txt (no BOM needed - cmd writes plain) ---
echo [4/5] Writing configuration files...

(
echo fastapi^>=0.115.0
echo uvicorn[standard]^>=0.32.0
echo pydantic^>=2.9.2
echo python-multipart^>=0.0.12
echo httpx^>=0.27.2
) > requirements.txt

(
echo -r requirements.txt
echo pytest^>=8.3.3
) > requirements-dev.txt

(
echo [project]
echo name = "hl7-inspector"
echo version = "1.0.0"
echo description = "HL7 v2 inspector, validator, and converter"
echo requires-python = ">=3.12"
echo dependencies = [
echo     "fastapi^>=0.115.0",
echo     "uvicorn[standard]^>=0.32.0",
echo     "pydantic^>=2.9.2",
echo     "python-multipart^>=0.0.12",
echo     "httpx^>=0.27.2",
echo ]
echo.
echo [build-system]
echo requires = ["setuptools^>=68"]
echo build-backend = "setuptools.build_meta"
echo.
echo [tool.pytest.ini_options]
echo testpaths = ["tests"]
) > pyproject.toml

(
echo {
echo   "$schema": "https://openapi.vercel.sh/vercel.json",
echo   "functions": {
echo     "app/main.py": {
echo       "excludeFiles": "{tests/**,__pycache__/**,.venv/**,**/*.pyc}"
echo     }
echo   }
echo }
) > vercel.json

(
echo .venv/
echo __pycache__/
echo *.pyc
echo .pytest_cache/
echo tests/
echo .env
echo *.log
) > .vercelignore

echo      Wrote requirements.txt, requirements-dev.txt,
echo      pyproject.toml, vercel.json, .vercelignore
echo.

REM --- 5. Install dependencies ---
echo [5/5] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo  To run the app:    run.bat
echo  To run tests:      test.bat
echo.
pause
endlocal