@echo off
chcp 65001 > nul
title 메바초이 릴스 스튜디오 - 클라우드 동기화 배포
cd /d "%~dp0"

echo ============================================================
echo   ☁️ 로컬 변경사항을 GitHub 및 클라우드 서버로 동시 배포합니다
echo ============================================================
echo.

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Git이 설치되어 있지 않거나 환경변수 PATH에 등록되지 않았습니다.
    pause
    exit /b 1
)

echo [1/3] 로컬 작업 파일 변경사항 확인 중...
git status --short

echo.
echo [2/3] 변경사항 커밋 및 GitHub 푸시 중...
git add -A
git commit -m "sync: auto-sync local changes to cloud server" >nul 2>&1
git push origin main

if %errorlevel% equ 0 (
    echo [3/3] ✓ GitHub 푸시 완료!
    echo.
    echo ============================================================
    echo   🚀 동기화 성공!
    echo   클라우드 VM(reels.my-toolkit.online)에 15~20초 내 자동 반영됩니다.
    echo ============================================================
) else (
    echo [!] 동기화 중 오류가 발생했거나 변경된 파일이 없습니다.
)

echo.
timeout /t 5
