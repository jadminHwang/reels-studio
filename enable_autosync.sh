#!/usr/bin/env bash
# ==============================================================================
# Reels Studio GitHub 자동 동기화 서비스 등록 스크립트
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER=$(whoami)
SERVICE_FILE="/etc/systemd/system/reels-sync.service"

chmod +x "$PROJECT_DIR/auto_sync.sh" "$PROJECT_DIR/update.sh"

echo "[1/3] reels-sync.service 시스템 데몬 등록 중..."
sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Reels Studio GitHub Auto Sync Daemon
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/bin/bash $PROJECT_DIR/auto_sync.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

echo "[2/3] 서비스 활성화 및 시작..."
sudo systemctl daemon-reload
sudo systemctl enable reels-sync.service
sudo systemctl restart reels-sync.service

echo "[3/3] 서비스 상태 확인..."
if sudo systemctl is-active --quiet reels-sync.service; then
    echo "============================================================"
    echo "🎉 GitHub 자동 배포 데몬 등록 성공!"
    echo "   이제 GitHub에서 코드를 수정하거나 푸시하면"
    echo "   서버 터미널을 열 필요 없이 30초 내로 자동 업데이트됩니다."
    echo "============================================================"
else
    echo "⚠️ 서비스 시작 실패. 'journalctl -u reels-sync.service -n 20'으로 확인하세요."
fi
