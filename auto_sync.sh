#!/usr/bin/env bash
# ==============================================================================
# Reels Studio GitHub 자동 동기화 데몬 (CI/CD Auto-Deploy)
# GitHub에 새 커밋이 올라오면 30초 안에 감지하여 서버를 자동 업데이트합니다.
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "🔄 GitHub 자동 감지 배포 데몬이 시작되었습니다. (프로젝트: $PROJECT_DIR)"

while true; do
    # 30초마다 GitHub 최신 커밋 확인
    git fetch origin main --quiet 2>/dev/null || true
    LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "")
    REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "")

    if [ -n "$LOCAL" ] && [ -n "$REMOTE" ] && [ "$LOCAL" != "$REMOTE" ]; then
        echo "============================================================"
        echo "🚀 [$(date '+%Y-%m-%d %H:%M:%S')] 새 커밋 발견! ($LOCAL -> $REMOTE)"
        echo "============================================================"
        bash "$PROJECT_DIR/update.sh"
    fi

    sleep 30
done
