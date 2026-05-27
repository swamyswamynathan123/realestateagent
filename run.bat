@echo off
setlocal EnableDelayedExpansion

echo.
echo  ==========================================
echo   Real Estate Agent - Startup
echo  ==========================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: 2. Create virtual environment if it does not exist
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
    echo [OK] Virtual environment found at .venv\
)

:: 3. Install / update required packages
echo [CHECK] Installing required packages (skips already-installed)...
.venv\Scripts\pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [ERROR] Package installation failed.
    echo         Check your internet connection and try again.
    pause
    exit /b 1
)
echo [OK] All packages ready

:: 4. Warn if .env is missing
if not exist ".env" (
    echo.
    echo [WARN] No .env file found.
    echo        You can still enter your OpenAI API key in the app sidebar.
    echo        To set it permanently:
    echo          1. copy .env.example .env
    echo          2. Edit .env and set OPENAI_API_KEY=sk-...
    echo.
)

:: 5. Launch the app
echo [START] Opening http://localhost:8501
echo         Press Ctrl+C to stop the server.
echo.
.venv\Scripts\streamlit run main.py --server.headless false

endlocal
