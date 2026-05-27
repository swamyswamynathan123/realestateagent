@echo off
setlocal EnableDelayedExpansion

echo.
echo  ===========================================
echo   Real Estate Agent App
echo  ===========================================
echo.

:: ── 1. Check Python ────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found

:: ── 2. Create virtual environment if missing ────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment found
)

:: ── 3. Install / verify requirements ───────────────────────────────────────
echo [CHECK] Checking required packages...

.venv\Scripts\pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [ERROR] Failed to install requirements. Check your internet connection.
    pause
    exit /b 1
)
echo [OK] All packages ready

:: ── 4. Check for .env file ─────────────────────────────────────────────────
if not exist ".env" (
    echo.
    echo [WARN] No .env file found.
    echo        Copy .env.example to .env and add your OPENAI_API_KEY:
    echo.
    echo          copy .env.example .env
    echo          notepad .env
    echo.
    echo        You can also enter your API key directly in the app sidebar.
    echo.
)

:: ── 5. Launch Streamlit ─────────────────────────────────────────────────────
echo [START] Launching app at http://localhost:8501
echo         Press Ctrl+C to stop.
echo.

.venv\Scripts\streamlit run main.py --server.headless false

endlocal
