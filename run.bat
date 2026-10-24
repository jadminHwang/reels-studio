@echo off
chcp 65001 > nul
title AI 숏폼 릴스 자동 편집기

echo ============================================================
echo   🎬 AI 숏폼 릴스 자동 편집기 & 썸네일 스튜디오
echo ============================================================
echo.

cd /d "%~dp0"

:: 1. 가상환경(venv) 탐색
set PYTHON_EXE=
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
    echo [✓] 로컬 가상환경(.venv)이 확인되었습니다.
) else if exist "venv\Scripts\python.exe" (
    set PYTHON_EXE=venv\Scripts\python.exe
    echo [✓] 가상환경(venv)이 확인되었습니다.
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_EXE=python
        echo [!] 로컬 가상환경이 없어 시스템 Python을 사용합니다.
    ) else (
        echo [오류] Python 실행 파일을 찾을 수 없습니다.
        echo Python 3.10 이상 또는 .venv 가상환경이 필요합니다.
        goto ERROR
    )
)

echo [✓] 사용 파이썬: %PYTHON_EXE%
echo.

:: 2. 필수 디렉터리 확인 및 생성
if not exist "inputs" mkdir inputs
if not exist "outputs" mkdir outputs
if not exist "assets\bgm" mkdir "assets\bgm"
if not exist "assets\fonts" mkdir "assets\fonts"

:: 2-1. 최신 업데이트 자동 확인 (Git Pull)
where git >nul 2>&1
if %errorlevel% equ 0 (
    echo [⟳] GitHub 원격 저장소 최신 업데이트 확인 중...
    git pull origin main --quiet >nul 2>&1
    if %errorlevel% equ 0 (
        echo [✓] 최신 코드로 동기화 완료되었습니다.
    ) else (
        echo [!] 오프라인이거나 원격 동기화를 건너뜁니다.
    )
)

:: 3. 브라우저 자동 오픈 예약 (2초 후 오픈)
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8501"

:: 4. Streamlit 로컬 웹 애플리케이션 실행
echo ============================================================
echo   🚀 Streamlit 웹 서버를 시작합니다... (포트: 8501)
echo   종료하려면 이 창에서 Ctrl + C 를 누르세요.
echo ============================================================
echo.

%PYTHON_EXE% -m streamlit run app.py --server.port 8501 --server.maxUploadSize 2000

if %errorlevel% neq 0 (
    goto ERROR
)

goto END

:ERROR
echo.
echo ============================================================
echo   [!] 실행 중 오류가 발생했습니다. 위의 로그를 확인하세요.
echo ============================================================
pause

:END
