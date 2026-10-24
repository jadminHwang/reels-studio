#!/usr/bin/env bash
# ==============================================================================
# AI 숏폼 릴스 자동 편집기 (Reels Studio) - GCP Ubuntu 22.04 원클릭 서버 셋업 스크립트
# ==============================================================================
set -e

echo "============================================================"
echo "  🚀 Reels Studio 클라우드 서버 자동 설치 및 서비스를 시작합니다."
echo "============================================================"

PROJECT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "[1/7] 시스템 패키지 업데이트 및 FFmpeg/파이썬 설치 중..."
sudo apt update -y
sudo apt install -y python3-pip python3-venv git ffmpeg fonts-nanum curl

echo "[2/7] 평생 무료 e2-micro용 가상 메모리(4GB Swap) 설정 중..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 4G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✓ 4GB 가상 메모리 설정 완료 (메모리 부족 방지)"
else
    echo "✓ 이미 가상 메모리가 설정되어 있습니다."
fi

echo "[3/7] 프로젝트 필수 디렉터리 구조 생성 중..."
mkdir -p inputs outputs assets/bgm assets/fonts .streamlit

echo "[3/6] 파이썬 가상환경(venv) 생성 및 패키지 설치 중..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "[4/6] 환경 변수(.env) 설정 확인 중..."
if [ ! -f ".env" ]; then
    echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
    echo "⚠️ .env 파일이 새로 생성되었습니다. 나중에 'nano .env'로 실제 API 키를 입력해 주세요."
else
    echo "✓ 기존 .env 파일을 확인했습니다."
fi

echo "[5/6] 24시간 백그라운드 자동 실행 systemd 서비스 등록 중..."
SERVICE_FILE="/etc/systemd/system/reels.service"

sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Reels Studio Streamlit App
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/streamlit run app.py --server.port 8501 --server.headless true --server.maxUploadSize 2000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable reels.service
sudo systemctl restart reels.service

echo "[6/6] 서비스 상태 확인..."
sudo systemctl is-active --quiet reels.service && echo "✓ reels.service 가 정상 실행 중입니다!" || echo "⚠️ 서비스 시작 확인 필요"

echo "============================================================"
echo "  🎉 로컬 서버 세팅 완료! (포트: 8501)"
echo "  현재 서비스 상태 확인: sudo systemctl status reels.service"
echo "  로그 실시간 확인: journalctl -u reels.service -f"
echo "============================================================"
