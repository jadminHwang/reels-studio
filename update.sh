#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  🚀 Reels Studio 최신 코드 자동 동기화 및 서비스 갱신"
echo "============================================================"

PROJECT_DIR=$(pwd)
echo "[1/3] GitHub에서 최신 코드 가져오기..."
git pull origin main

echo "[2/3] 신규 의존성 패키지 점검..."
if [ -d "venv" ]; then
    ./venv/bin/pip install -r requirements.txt --quiet || ./venv/bin/python3 -m pip install -r requirements.txt || true
elif [ -d ".venv" ]; then
    ./.venv/bin/pip install -r requirements.txt --quiet || ./.venv/bin/python3 -m pip install -r requirements.txt || true
fi

echo "[3/3] 24시간 서비스 재시작 중..."
sudo systemctl restart reels.service

echo "============================================================"
echo "  🎉 서버 업데이트 완료!"
echo "============================================================"
sudo systemctl status reels.service --no-pager -n 5
