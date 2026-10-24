@echo off
title Reels Studio Local
cd /d "%~dp0"

echo ============================================================
echo   Reels Studio - Local High Speed Mode
echo ============================================================
echo.

echo [1/3] Checking directories...
if not exist "inputs" mkdir inputs
if not exist "outputs" mkdir outputs
if not exist "assets\bgm" mkdir "assets\bgm"
if not exist "assets\fonts" mkdir "assets\fonts"

echo [2/3] Checking Git updates & dependencies...
git pull origin main --quiet >nul 2>&1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import edge_tts" >nul 2>&1
    if errorlevel 1 (
        echo Installing missing packages...
        ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet >nul 2>&1
    )
)

echo [3/3] Launching Reels Studio on http://localhost:8501 ...
start "" http://localhost:8501

if exist ".venv\Scripts\streamlit.exe" (
    ".venv\Scripts\streamlit.exe" run app.py --server.port 8501 --server.maxUploadSize 2000
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --server.maxUploadSize 2000
) else (
    python -m streamlit run app.py --server.port 8501 --server.maxUploadSize 2000
)

if %errorlevel% neq 0 (
    echo.
    echo [Error] Failed to start Streamlit. Please check your Python environment.
    pause
)
