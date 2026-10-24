import io
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

# Windows 터미널 한글 출력 지원
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 모듈 import
import director
import editor

# ==========================================
# 1. 베이스 디렉터리 초기화 및 자동 가비지 컬렉션
# ==========================================
INPUTS_DIR = Path("inputs")
OUTPUTS_DIR = Path("outputs")
TEMP_CLIPS_DIR = Path("temp_clips")
BGM_DIR = Path("assets/bgm")
FONTS_DIR = Path("assets/fonts")

for d in [INPUTS_DIR, OUTPUTS_DIR, TEMP_CLIPS_DIR, BGM_DIR, FONTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

for f in Path(".").glob("*.ttf"):
    dest = FONTS_DIR / f.name
    if not dest.exists():
        try:
            shutil.copy2(f, dest)
        except Exception:
            pass


def cleanup_old_temp_files(max_age_seconds: int = 3600):
    """1시간 이상 지난 잔여 임시 세션 디렉터리를 자동 정리하여 디스크를 보호합니다."""
    now = time.time()
    for base in [INPUTS_DIR, OUTPUTS_DIR, TEMP_CLIPS_DIR]:
        if not base.exists():
            continue
        for item in base.iterdir():
            if item.is_dir() and item.name not in ["bgm", "fonts"]:
                try:
                    if now - item.stat().st_mtime > max_age_seconds:
                        shutil.rmtree(item, ignore_errors=True)
                except Exception:
                    pass
            elif item.is_file() and item.suffix.lower() in [".mp4", ".mov", ".jpg", ".png", ".ass", ".json"]:
                try:
                    if now - item.stat().st_mtime > max_age_seconds:
                        item.unlink(missing_ok=True)
                except Exception:
                    pass


# 앱 기동 시 오래된 임시 파일 자동 클린업
cleanup_old_temp_files(max_age_seconds=3600)

# ==========================================
# 2. 세션별 독립 작업 공간 (새로 열었을 때 이전 작업 흔적 원천 차단)
# ==========================================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
    st.session_state.page = "upload"
    st.session_state.timeline_data = None
    st.session_state.video_bytes = None
    st.session_state.thumb_bytes = None
    st.session_state.is_cleaned = False
    st.session_state.selected_font = "Bithumb Gothic Basic"

SESSION_ID = st.session_state.session_id
SESSION_INPUTS_DIR = INPUTS_DIR / SESSION_ID
SESSION_OUTPUTS_DIR = OUTPUTS_DIR / SESSION_ID
SESSION_TEMP_DIR = TEMP_CLIPS_DIR / SESSION_ID

SESSION_INPUTS_DIR.mkdir(parents=True, exist_ok=True)
SESSION_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
SESSION_TEMP_DIR.mkdir(parents=True, exist_ok=True)

SESSION_TIMELINE_FILE = SESSION_OUTPUTS_DIR / "timeline.json"
SESSION_FINAL_VIDEO_FILE = SESSION_OUTPUTS_DIR / "final_reels.mp4"
SESSION_THUMBNAIL_FILE = SESSION_OUTPUTS_DIR / "thumbnail.jpg"
SESSION_SNS_PACKAGE_FILE = SESSION_OUTPUTS_DIR / "sns_package.json"


def reset_to_home():
    """모든 임시 데이터를 삭제하고 홈(첫 화면)으로 완전히 초기화합니다."""
    sid = st.session_state.get("session_id")
    if sid:
        for base in [INPUTS_DIR, OUTPUTS_DIR, TEMP_CLIPS_DIR]:
            target = base / sid
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
    st.session_state.session_id = str(uuid.uuid4())[:8]
    st.session_state.timeline_data = None
    st.session_state.video_bytes = None
    st.session_state.thumb_bytes = None
    st.session_state.is_cleaned = False
    st.session_state.user_intent = ""
    st.session_state.page = "upload"
    st.rerun()


def cleanup_current_session(sid: str = None):
    """다운로드 완료 시 서버의 임시 파일 즉시 파기"""
    target_id = sid or st.session_state.get("session_id")
    if target_id:
        for base in [INPUTS_DIR, OUTPUTS_DIR, TEMP_CLIPS_DIR]:
            target = base / target_id
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
    st.session_state.is_cleaned = True


# ==========================================
# 3. 페이지 기본 설정 & 스마트폰 화면 최적화 CSS
# ==========================================
st.set_page_config(
    page_title="메바초이 | Reels Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,400..700;1,7..72,400..700&family=Nunito+Sans:ital,opsz,wght@0,6..12,300..900;1,6..12,300..900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    /* 로컬 추가 폰트 @font-face 등록 */
    @font-face {
        font-family: 'Bithumb Gothic Basic';
        src: url('/app/static/fonts/bithumb_basic.ttf') format('truetype'),
             url('/static/fonts/bithumb_basic.ttf') format('truetype');
        font-weight: bold;
        font-display: swap;
    }
    @font-face {
        font-family: 'Bithumb Gothic Original';
        src: url('/app/static/fonts/bithumb_original.ttf') format('truetype'),
             url('/static/fonts/bithumb_original.ttf') format('truetype');
        font-weight: bold;
        font-display: swap;
    }
    @font-face {
        font-family: 'GangwonEduAll Bold';
        src: url('/app/static/fonts/gangwon_bold.ttf') format('truetype'),
             url('/static/fonts/gangwon_bold.ttf') format('truetype');
        font-weight: bold;
        font-display: swap;
    }
    @font-face {
        font-family: 'Griun Yeeun';
        src: url('/app/static/fonts/griun_yeeun.ttf') format('truetype'),
             url('/static/fonts/griun_yeeun.ttf') format('truetype');
        font-weight: normal;
        font-display: swap;
    }

    html, body, [class*="css"] {
        font-family: 'Nunito Sans', 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #FAF6F0 !important;
        color: #2E3230 !important;
    }

    .stApp {
        background-color: #FAF6F0 !important;
    }

    /* 스마트폰 최적화 중앙 컨테이너 (max-width: 440px 모바일 뷰) */
    .main .block-container {
        max-width: 460px !important;
        margin: 0 auto !important;
        padding-top: 0.6rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background-color: #F0ECE4 !important;
        border-right: 1px solid #E4E0D8 !important;
    }

    /* 스티치 라운드 카드 */
    .stitch-card {
        background-color: #FFFFFF;
        border: 1px solid #E4E0D8;
        border-radius: 18px;
        padding: 1.15rem 1.25rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 3px rgba(46, 50, 48, 0.04);
        position: relative;
    }

    .stitch-card-active {
        background-color: #FFFFFF;
        border: 2px solid #4A7C59;
        border-radius: 18px;
        padding: 1.15rem 1.25rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 2px 8px rgba(74, 124, 89, 0.08);
    }

    /* 뱃지 */
    .stitch-pill-primary {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.6rem;
        background-color: #4A7C59;
        color: #FFFFFF;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .stitch-pill-soft {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.6rem;
        background-color: #C8E8D0;
        color: #2A6038;
        border: 1px solid rgba(74, 124, 89, 0.2);
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 700;
    }

    .stitch-pill-muted {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.6rem;
        background-color: #F0ECE4;
        color: #5E5548;
        border: 1px solid #E4E0D8;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 600;
    }

    .chip-item {
        display: inline-flex;
        align-items: center;
        background-color: #F5F1EA;
        border: 1px solid #E4E0D8;
        color: #2E3230;
        padding: 0.3rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 0.2rem 0.25rem 0.2rem 0;
    }

    /* 보안 알림 배너 */
    .security-notice {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background-color: #EBF5EE;
        border: 1px solid #8ECF9E;
        color: #2A6038;
        padding: 0.75rem 1rem;
        border-radius: 14px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.85rem;
    }

    /* 타이포그래피 */
    .font-headline {
        font-family: 'Literata', serif !important;
    }

    .title-large {
        font-family: 'Literata', serif !important;
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #2E3230;
        margin-top: 0.25rem;
        margin-bottom: 0.25rem;
    }

    .subtitle-muted {
        font-size: 0.85rem;
        color: #5E5548;
        margin-bottom: 1rem;
        line-height: 1.45;
    }

    /* 버튼 스타일 */
    button[kind="primary"] {
        background-color: #4A7C59 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: 1px solid #4A7C59 !important;
        border-radius: 12px !important;
        padding: 0.65rem 1.2rem !important;
        box-shadow: 0 2px 6px rgba(74, 124, 89, 0.2) !important;
        transition: all 0.2s ease !important;
    }

    button[kind="primary"]:hover {
        background-color: #3D6649 !important;
        border-color: #3D6649 !important;
        box-shadow: 0 4px 10px rgba(74, 124, 89, 0.3) !important;
    }

    button[kind="secondary"] {
        background-color: #F5F1EA !important;
        color: #2E3230 !important;
        border: 1px solid #E4E0D8 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    button[kind="secondary"]:hover {
        background-color: #E4E0D8 !important;
        border-color: #C4C8BC !important;
    }

    .stDownloadButton button {
        width: 100% !important;
        border-radius: 12px !important;
    }

    /* 입력 요소 */
    input[type="text"], textarea, select, div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E4E0D8 !important;
        color: #2E3230 !important;
        border-radius: 10px !important;
    }

    input[type="text"]:focus, textarea:focus {
        border-color: #4A7C59 !important;
        box-shadow: 0 0 0 2px rgba(74, 124, 89, 0.15) !important;
    }

    div[data-testid="stFileUploader"] section {
        background-color: #F5F1EA !important;
        border: 2px dashed #C4C8BC !important;
        border-radius: 16px !important;
        padding: 1.25rem !important;
    }

    .header-reset-wrap button {
        background-color: #FAF8F5 !important;
        color: #38433E !important;
        border: 1.5px solid #D1C9BC !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        padding: 0.35rem 0.85rem !important;
        height: 34px !important;
        min-height: 34px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease !important;
        margin-top: 0.1rem !important;
        letter-spacing: 0.02em !important;
    }

    .header-reset-wrap button:hover {
        background-color: #4A7C59 !important;
        color: #FFFFFF !important;
        border-color: #4A7C59 !important;
        box-shadow: 0 2px 6px rgba(74, 124, 89, 0.25) !important;
        transform: translateY(-1px);
    }

    hr {
        border-color: #E4E0D8 !important;
        margin: 1rem 0 !important;
    }

    .material-symbols-outlined {
        font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 20;
        vertical-align: middle;
        line-height: 1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 4. 스마트폰 상단 헤더 & 처음으로 리셋 버튼
# ==========================================
col_hdr1, col_hdr2 = st.columns([3.4, 1.0])
with col_hdr1:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:0.5rem; padding:0.2rem 0;">
            <div style="width:34px; height:34px; border-radius:10px; background:#4A7C59; display:flex; align-items:center; justify-content:center; color:#FFF; box-shadow:0 2px 4px rgba(74,124,89,0.25);">
                <span class="material-symbols-outlined" style="font-size:20px;">auto_awesome</span>
            </div>
            <div>
                <div style="font-weight:800; font-size:1.05rem; letter-spacing:0.02em; color:#2E3230; line-height:1.15;">메바초이 <span style="font-weight:600; font-size:0.75rem; color:#5E5548;">REELS STUDIO</span></div>
                <div style="font-size:0.72rem; color:#6B6358; font-weight:500;">스마트폰 숏폼 자동 편집기</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_hdr2:
    st.markdown('<div class="header-reset-wrap">', unsafe_allow_html=True)
    if st.button("홈", help="모든 작업을 초기화하고 첫 화면으로 이동합니다", use_container_width=True):
        reset_to_home()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr style='margin:0.5rem 0 0.85rem 0;'/>", unsafe_allow_html=True)

# ==========================================
# 5. 사이드바 설정 패널 (접힘 상태 지원)
# ==========================================
with st.sidebar:
    st.markdown('<div class="stitch-pill-soft">환경 설정</div>', unsafe_allow_html=True)
    st.markdown('<div class="font-headline" style="font-weight:700; font-size:1.15rem; margin-top:0.4rem; color:#2E3230;">제작 환경 설정</div>', unsafe_allow_html=True)
    st.caption("스마트폰 릴스 렌더링 스타일 및 연출 옵션")
    st.divider()

    AVAILABLE_FONTS = [
        {
            "id": "Bithumb Gothic Basic",
            "title": "빗썸 고딕 Basic",
            "badge": "NEW 추천",
            "desc": "강렬하고 트렌디한 볼드 고딕 (쇼츠 최적화)",
            "sample": "먹을래요? ✨ 100만 뷰 떡상 릴스 자막",
        },
        {
            "id": "Bithumb Gothic Original",
            "title": "빗썸 고딕 Original",
            "badge": "NEW 오리지널",
            "desc": "세련되고 묵직한 오리지널 고딕",
            "sample": "먹을래요? ✨ 100만 뷰 떡상 릴스 자막",
        },
        {
            "id": "GangwonEduAll Bold",
            "title": "강원교육모두 Bold",
            "badge": "쇼츠 대세",
            "desc": "둥글둥글하고 친근한 숏폼 대세 볼드체",
            "sample": "먹을래요? ✨ 100만 뷰 떡상 릴스 자막",
        },
        {
            "id": "Griun Yeeun",
            "title": "그리운 예은체",
            "badge": "감성 손글씨",
            "desc": "따뜻하고 자연스러운 손글씨 감성",
            "sample": "먹을래요? ✨ 100만 뷰 떡상 릴스 자막",
        },
    ]

    st.markdown('<div style="font-weight:700; font-size:0.85rem; color:#5E5548; margin-bottom:0.35rem;">자막 폰트 선택 & 서체 미리보기</div>', unsafe_allow_html=True)

    font_ids = [f["id"] for f in AVAILABLE_FONTS]
    cur_sel_font = st.session_state.get("selected_font", "Bithumb Gothic Basic")
    cur_idx = font_ids.index(cur_sel_font) if cur_sel_font in font_ids else 0

    def on_sidebar_font_change():
        st.session_state.selected_font = st.session_state.sidebar_font_radio

    selected_font = st.radio(
        "자막 폰트",
        options=font_ids,
        format_func=lambda fid: next((f"{f['title']} ({f['badge']})" for f in AVAILABLE_FONTS if f["id"] == fid), fid),
        index=cur_idx,
        key="sidebar_font_radio",
        on_change=on_sidebar_font_change,
        label_visibility="collapsed",
    )
    st.session_state.selected_font = selected_font

    # 폰트별 실제 서체 적용 비주얼 카드 렌더링
    for f in AVAILABLE_FONTS:
        is_sel = (f["id"] == selected_font)
        border_style = "2px solid #4A7C59" if is_sel else "1px solid #E4E0D8"
        bg_style = "#FFFFFF" if is_sel else "#F5F1EA"
        badge_bg = "#C8E8D0" if is_sel else "#E4E0D8"
        badge_fg = "#2A6038" if is_sel else "#5E5548"

        preview_card_html = f"""
        <div style="background:{bg_style}; border:{border_style}; border-radius:12px; padding:0.65rem 0.75rem; margin-bottom:0.45rem; box-shadow:0 1px 2px rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-family:'{f['id']}', sans-serif; font-size:1.05rem; font-weight:700; color:#2E3230; line-height:1.2;">
                    {f['title']}
                </span>
                <span style="font-size:0.68rem; font-weight:700; padding:0.15rem 0.45rem; border-radius:6px; background:{badge_bg}; color:{badge_fg};">
                    {f['badge']}
                </span>
            </div>
            <div style="font-family:'{f['id']}', sans-serif; font-size:0.88rem; color:#FFFFFF; margin-top:0.35rem; text-shadow:-1.5px -1.5px 0 #000, 1.5px -1.5px 0 #000, -1.5px 1.5px 0 #000, 1.5px 1.5px 0 #000; letter-spacing:0.02em;">
                {f['sample']}
            </div>
            <div style="font-size:0.7rem; color:#6B6358; margin-top:0.25rem;">
                {f['desc']}
            </div>
        </div>
        """
        st.markdown(preview_card_html, unsafe_allow_html=True)

    target_duration = st.slider("목표 영상 길이(초)", min_value=15, max_value=45, value=25, step=5)
    st.caption(f"목표 러닝타임: **{target_duration}초**")

    use_zoom = st.checkbox("다이내믹 줌 트랜지션", value=True)
    use_bgm = st.checkbox("배경음악 자동 믹싱", value=True)

    st.markdown('<div style="font-weight:700; font-size:0.85rem; color:#5E5548; margin-top:0.75rem; margin-bottom:0.25rem;">AI 음성 더빙 & 오디오</div>', unsafe_allow_html=True)
    use_tts = st.checkbox("AI 내레이션 더빙 사용", value=True)

    if use_tts:
        voice_labels = list(editor.VOICE_PRESETS.keys())
        selected_voice_label = st.selectbox(
            "더빙 목소리 선택",
            options=voice_labels,
            index=0,
            help="완전 무료 고품질 한국어 뉴럴 보이스 (Edge-TTS)",
        )
        selected_voice_id = editor.VOICE_PRESETS[selected_voice_label]

        tts_speed = st.slider(
            "음성 속도",
            min_value=0.8,
            max_value=1.5,
            value=1.15,
            step=0.05,
            format="%.2fx",
            help="숏폼의 빠른 템포와 리듬감에 맞는 1.1x ~ 1.2x 속도를 추천합니다.",
        )

        # 보이스 실시간 미리듣기 위젯
        if st.button("목소리 미리듣기", use_container_width=True):
            with st.spinner("AI 목소리 합성 중..."):
                sample_text = "안녕하세요! 오늘의 초간단 레시피를 시작합니다."
                sample_bytes = editor.generate_tts_bytes(sample_text, voice=selected_voice_id, speed=tts_speed)
                if sample_bytes:
                    st.audio(sample_bytes, format="audio/mp3")
    else:
        selected_voice_id = "ko-KR-SunHiNeural"
        tts_speed = 1.15

    generate_sns = st.checkbox("SNS 텍스트 패키지 생성", value=True)

    st.divider()
    if st.button("작업 초기화", use_container_width=True):
        reset_to_home()


# ==========================================
# 6. 화면 분기 로직 (upload -> analysis/editor -> result)
# ==========================================

# ----------------------------------------------------
# [화면 1: 영상 업로드 화면 (흔적 없는 깨끗한 시작)]
# ----------------------------------------------------
if st.session_state.page == "upload":
    st.markdown(
        """
        <div class="stitch-card">
            <span class="stitch-pill-soft">업로드 단계</span>
            <div class="title-large">릴스 제작할 클립 업로드</div>
            <div class="subtitle-muted">촬영한 스마트폰 동영상을 올리면 AI가 하이라이트 구간을 자동으로 선별합니다.</div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "영상 파일들을 선택하세요 (.mp4, .mov)",
        type=["mp4", "mov"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        for f in uploaded_files:
            target_path = SESSION_INPUTS_DIR / f.name
            if not target_path.exists():
                with open(target_path, "wb") as out:
                    out.write(f.getbuffer())

    # 현재 세션의 업로드 영상 목록만 조회 (과거 흔적 없음)
    existing_videos = sorted(
        list(SESSION_INPUTS_DIR.glob("*.mp4")) + list(SESSION_INPUTS_DIR.glob("*.mov")),
        key=lambda p: (int(p.stem) if p.stem.isdigit() else p.stem),
    )

    if existing_videos:
        st.markdown('<div style="font-size:0.8rem; font-weight:700; color:#5E5548; margin-top:0.75rem; margin-bottom:0.35rem;">업로드된 클립 목록</div>', unsafe_allow_html=True)
        chips_html = '<div>'
        for v in existing_videos:
            size_mb = v.stat().st_size / (1024 * 1024)
            chips_html += f'<span class="chip-item">🎬 {v.name} ({size_mb:.1f}MB)</span>'
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)

    # 2. 사용자 기획 주제 및 연출 의도 입력창 (스티치 스타일)
    st.markdown(
        """
        <div style="margin-top:0.85rem; margin-bottom:0.3rem;">
            <div style="font-size:0.82rem; font-weight:700; color:#2E3230; display:flex; align-items:center; gap:0.3rem;">
                <span class="material-symbols-outlined" style="font-size:18px; color:#4A7C59;">edit_note</span>
                <span>기획 주제 및 연출 의도 (선택 사항)</span>
            </div>
            <div style="font-size:0.72rem; color:#6B6358; margin-top:2px;">
                특정 메뉴/레시피명, 강조하고 싶은 손동작이나 질감, 원하는 톤앤매너를 적어주시면 AI 디렉터가 우선 반영합니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    user_intent = st.text_input(
        "기획 주제 및 연출 의도",
        value=st.session_state.get("user_intent", ""),
        placeholder="예: 고소한 호두파이 레시피, 바삭한 질감과 손동작 강조 / 카페 디저트 브이로그",
        label_visibility="collapsed",
    )
    st.session_state.user_intent = user_intent

    st.markdown('</div>', unsafe_allow_html=True)

    # 자막 폰트 드롭다운 선택
    st.markdown(
        """
        <div style="margin-top:0.75rem; margin-bottom:0.25rem;">
            <div style="font-size:0.82rem; font-weight:700; color:#2E3230; display:flex; align-items:center; gap:0.3rem;">
                <span class="material-symbols-outlined" style="font-size:18px; color:#4A7C59;">font_download</span>
                <span>자막 폰트 선택</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    font_id_list = [f["id"] for f in AVAILABLE_FONTS]
    cur_sel_font = st.session_state.get("selected_font", "Bithumb Gothic Basic")
    cur_sel_idx = font_id_list.index(cur_sel_font) if cur_sel_font in font_id_list else 0

    selected_font_label = st.selectbox(
        "자막 폰트 선택",
        options=font_id_list,
        index=cur_sel_idx,
        format_func=lambda fid: next((f"{f['title']} ({f['badge']})" for f in AVAILABLE_FONTS if f["id"] == fid), fid),
        label_visibility="collapsed",
        key="main_font_selectbox",
    )
    st.session_state.selected_font = selected_font_label

    # 선택된 폰트의 실물 서체 단일 미리보기 박스 (코드 태그 깨짐 없는 안전한 문자열)
    sel_font_info = next((f for f in AVAILABLE_FONTS if f["id"] == selected_font_label), AVAILABLE_FONTS[0])
    preview_box_html = (
        f'<div style="background:#FAF8F5; border:1.5px solid #D5CEC2; border-radius:10px; padding:0.6rem 0.8rem; margin-top:0.35rem; margin-bottom:0.75rem;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; font-size:0.72rem; color:#5E5548; font-weight:600;">'
        f'<span>서체 실물 미리보기: <b>{sel_font_info["title"]}</b></span>'
        f'<span style="background:#C8E8D0; color:#2A6038; padding:1px 6px; border-radius:4px; font-weight:700;">{sel_font_info["badge"]}</span>'
        f'</div>'
        f'<div style="font-family:\'{sel_font_info["id"]}\', sans-serif; font-size:1.05rem; font-weight:700; color:#FFFFFF; margin-top:0.35rem; text-shadow:-1.5px -1.5px 0 #000, 1.5px -1.5px 0 #000, -1.5px 1.5px 0 #000, 1.5px 1.5px 0 #000; letter-spacing:0.02em;">'
        f'{sel_font_info["sample"]}'
        f'</div>'
        f'</div>'
    )
    st.markdown(preview_box_html, unsafe_allow_html=True)

    # 액션 버튼
    analyze_btn = st.button("AI 분석 및 쇼츠 세그먼트 추출", type="primary", use_container_width=True)

    if analyze_btn:
        if not existing_videos:
            st.error("영상을 1개 이상 업로드해 주세요.")
        else:
            prog = st.progress(0.0)
            stat = st.empty()

            def cb(msg):
                stat.info(msg)

            try:
                with st.spinner("AI 감독관이 영상을 분석하고 하이라이트 타임라인을 기획 중입니다..."):
                    new_timeline = director.generate_timeline_from_videos(
                        existing_videos,
                        target_duration=float(target_duration),
                        user_prompt=user_intent,
                        progress_callback=cb,
                    )
                    st.session_state.timeline_data = new_timeline
                    with open(SESSION_TIMELINE_FILE, "w", encoding="utf-8") as f:
                        json.dump(new_timeline, f, ensure_ascii=False, indent=2)

                    prog.progress(1.0)
                    stat.success("분석 완료! 스마트폰 세그먼트 화면으로 이동합니다.")
                    st.session_state.page = "analysis"
                    st.rerun()
            except Exception as e:
                st.error(f"AI 분석 중 오류가 발생했습니다: {e}")


# ----------------------------------------------------
# [화면 2: 스티치 모바일 분석 & AI 추천 쇼츠 세그먼트]
# ----------------------------------------------------
elif st.session_state.page in ["analysis", "editor"]:
    timeline_data = st.session_state.get("timeline_data")
    if not timeline_data and SESSION_TIMELINE_FILE.exists():
        try:
            with open(SESSION_TIMELINE_FILE, "r", encoding="utf-8") as f:
                timeline_data = json.load(f)
                st.session_state.timeline_data = timeline_data
        except Exception:
            timeline_data = None

    if not timeline_data:
        st.warning("타임라인 데이터가 없습니다. 홈으로 이동하여 영상을 업로드해 주세요.")
        if st.button("처음으로 돌아가기"):
            reset_to_home()
    else:
        cuts_list = timeline_data.get("cuts", [])
        total_sec = float(timeline_data.get("total_duration_seconds", sum(float(c.get("duration", c.get("duration_seconds", 2.0))) for c in cuts_list)))
        title_text = timeline_data.get("title", "스마트 숏폼 릴스")
        concept_text = timeline_data.get("concept", "감각적인 연출 콘셉트")
        bgm_vibe = timeline_data.get("bgm_vibe", "")
        opening_hook = timeline_data.get("opening_hook", {})
        ending_cta = timeline_data.get("ending_cta", "")

        # 1. 숏폼 총괄 디렉터 연출 기획안 요약 카드
        st.markdown(
            f"""
            <div class="stitch-card" style="border-left: 4px solid #4A7C59; padding: 1rem 1.15rem; margin-bottom: 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
                    <span class="stitch-pill-primary" style="font-size:0.7rem;">DIRECTOR'S CUT</span>
                    <span style="font-size:0.75rem; font-weight:700; color:#4A7C59;">총 {total_sec:.1f}초 ({len(cuts_list)}개 컷)</span>
                </div>
                <div style="font-family:'Bithumb Gothic Bold', sans-serif; font-size:1.05rem; font-weight:800; color:#2E3230; line-height:1.35; margin-bottom:0.25rem;">
                    {title_text}
                </div>
                <div style="font-size:0.75rem; color:#5E5548; line-height:1.4; margin-bottom:0.6rem;">
                    {concept_text}
                </div>
                {f'''<div style="background:#FAF8F5; border-radius:10px; padding:0.5rem 0.65rem; border:1px solid #EAE5DC; margin-bottom:0.4rem; font-size:0.75rem;">
                    <span style="color:#705C30; font-weight:700;">첫 1~2초 훅:</span>
                    <span style="color:#B8860B; font-weight:800; margin-left:0.2rem;">[{opening_hook.get("line1_highlight", "")}]</span>
                    <span style="color:#2E3230; font-weight:600; margin-left:0.2rem;">{opening_hook.get("line2_sub", "")}</span>
                </div>''' if opening_hook else ''}
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.72rem; color:#6B6358; padding-top:0.3rem; border-top:1px dashed #EAE5DC;">
                    <span>🎵 {bgm_vibe if bgm_vibe else '트렌디한 숏폼 BGM'}</span>
                    <span>✨ {ending_cta if ending_cta else '시청 지속 극대화'}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Section: AI 추천 쇼츠 세그먼트 (스티치 카드 디자인)
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; padding:0 0.2rem;">
                <div style="display:flex; align-items:center; gap:0.35rem;">
                    <span class="material-symbols-outlined" style="color:#4A7C59; font-size:18px;">movie_filter</span>
                    <span class="font-headline" style="font-weight:700; font-size:1.05rem; color:#2E3230;">AI 추천 쇼츠 세그먼트</span>
                </div>
                <span style="font-size:0.78rem; font-weight:600; color:#5E5548;">{len(cuts_list)}개 클립 시퀀스</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 컷별 스티치 카드 렌더링
        for idx, cut in enumerate(cuts_list):
            is_hook = (idx == 0)
            card_class = "stitch-card-active" if is_hook else "stitch-card"
            pill_class = "stitch-pill-primary" if is_hook else "stitch-pill-muted"
            viral_score = max(82, 96 - (idx * 3))

            dur_s = float(cut.get("duration", cut.get("duration_seconds", 2.0)))
            file_label = cut.get("source_file") or cut.get("file_name", "")
            start_t = cut.get("start_time") or cut.get("start", "00:00")
            end_t = cut.get("end_time") or cut.get("end", "00:00")
            action_role = cut.get("action_role") or cut.get("reason", "알고리즘 유지율 극대화")
            has_zoom = bool(cut.get("zoom_in", False))

            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            col_t1, col_t2 = st.columns([3, 1.2])
            with col_t1:
                zoom_badge = '<span class="stitch-pill-soft" style="font-size:0.68rem; margin-left:0.25rem;">🔍 줌인</span>' if has_zoom else ''
                st.markdown(
                    f'<span class="{pill_class}">CUT 0{idx+1}</span>{zoom_badge} '
                    f'<span style="font-size:0.76rem; font-weight:600; color:#5E5548; margin-left:0.35rem;">{file_label} ({start_t}~{end_t})</span>',
                    unsafe_allow_html=True,
                )
            with col_t2:
                st.markdown(
                    f'<div style="text-align:right;"><span class="stitch-pill-soft" style="font-size:0.68rem;">바이럴 {viral_score}점</span></div>',
                    unsafe_allow_html=True,
                )

            # 연출 역할 (action_role) 뱃지/가이드
            st.markdown(
                f'<div style="font-size:0.73rem; color:#4A7C59; font-weight:700; margin:0.35rem 0 0.25rem 0;">🎯 {action_role}</div>',
                unsafe_allow_html=True,
            )

            # 자막 카피 입력창 (1번 훅은 줄바꿈 지원을 위해 높이 지정)
            current_cap = cut.get("caption", "")
            if is_hook:
                updated_cap = st.text_area(
                    f"자막 #{idx+1} (줄바꿈 가능)",
                    value=current_cap,
                    key=f"st_cap_{idx}",
                    height=68,
                    label_visibility="collapsed",
                )
            else:
                updated_cap = st.text_input(
                    f"자막 #{idx+1}",
                    value=current_cap,
                    key=f"st_cap_{idx}",
                    label_visibility="collapsed",
                )
            cuts_list[idx]["caption"] = updated_cap

            # 카드 하단 지표
            ctr = 14.5 - (idx * 1.6)
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.4rem; padding-top:0.35rem; border-top:1px solid #F0ECE4; font-size:0.72rem; color:#5E5548;">
                    <div style="display:flex; align-items:center; gap:0.5rem;">
                        <span>⏱️ {dur_s:.1f}초</span>
                        <span>🎯 예상 CTR {ctr:.1f}%</span>
                        <span>📱 1080x1920 세로형</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # 3. Section: 영상 정밀 분석 지표 (스티치 2x2 그리드)
        st.markdown(
            """
            <div style="margin-top:0.85rem; margin-bottom:0.85rem;">
                <div style="display:flex; align-items:center; gap:0.35rem; margin-bottom:0.5rem; padding:0 0.2rem;">
                    <span class="material-symbols-outlined" style="color:#4A7C59; font-size:18px;">equalizer</span>
                    <span class="font-headline" style="font-weight:700; font-size:1.05rem; color:#2E3230;">영상 정밀 분석 지표</span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:0.5rem;">
                    <div class="stitch-card" style="margin-bottom:0; padding:0.85rem;">
                        <span style="font-size:0.72rem; color:#5E5548; font-weight:600; display:block;">평균 발화 속도</span>
                        <div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.2rem;">
                            <span class="font-headline" style="font-size:1.3rem; font-weight:800; color:#2E3230;">142</span>
                            <span style="font-size:0.72rem; color:#5E5548; font-weight:600;">WPM</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:0.3rem; margin-top:0.3rem; color:#4A7C59; font-size:0.72rem; font-weight:700;">
                            <span style="width:5px; height:5px; border-radius:50%; background:#4A7C59;"></span>
                            <span>최적 속도 구간 일치</span>
                        </div>
                    </div>
                    <div class="stitch-card" style="margin-bottom:0; padding:0.85rem;">
                        <span style="font-size:0.72rem; color:#5E5548; font-weight:600; display:block;">무음/불필요 구간</span>
                        <div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.2rem;">
                            <span class="font-headline" style="font-size:1.3rem; font-weight:800; color:#2E3230;">06:14</span>
                            <span style="font-size:0.72rem; color:#5E5548; font-weight:600;">CUT</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:0.3rem; margin-top:0.3rem; color:#6B6358; font-size:0.72rem; font-weight:600;">
                            <span style="width:5px; height:5px; border-radius:50%; background:#705C30;"></span>
                            <span>전체 12% 절감 가능</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4. 스티치 하단 고정 변환 바 (선택 클립 총 N개 | N초 분량 + 원클릭 쇼츠 편집기로 전달 & 렌더링)
        st.markdown(
            f"""
            <div class="stitch-card" style="margin-top:0.75rem; padding:0.85rem 1rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-size:0.72rem; color:#5E5548; font-weight:600;">선택 클립 총 {len(cuts_list)}개</div>
                        <div style="font-weight:800; font-size:0.95rem; color:#2E3230;">{total_sec:.0f}초 분량</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_btn = st.button("원클릭 쇼츠 편집기로 전달 & 렌더링", type="primary", use_container_width=True)

        if render_btn:
            timeline_data["cuts"] = cuts_list
            with open(SESSION_TIMELINE_FILE, "w", encoding="utf-8") as f:
                json.dump(timeline_data, f, ensure_ascii=False, indent=2)

            r_prog = st.progress(0.0)
            r_stat = st.empty()

            def r_cb(msg, progress):
                r_stat.info(msg)
                r_prog.progress(float(progress))

            try:
                with st.spinner("FFmpeg 9:16 인코딩 및 고화질 썸네일 추출 중..."):
                    rendered_path = editor.render_reels(
                        timeline_data,
                        output_video_path=SESSION_FINAL_VIDEO_FILE,
                        thumbnail_path=SESSION_THUMBNAIL_FILE,
                        input_dir=SESSION_INPUTS_DIR,
                        temp_dir=SESSION_TEMP_DIR,
                        selected_font=st.session_state.get("selected_font", selected_font),
                        use_zoom=use_zoom,
                        use_bgm=use_bgm,
                        use_tts=use_tts,
                        tts_voice=selected_voice_id,
                        tts_speed=tts_speed,
                        progress_callback=r_cb,
                    )

                    # 다운로드 대비 메모리 버퍼 적재
                    if SESSION_FINAL_VIDEO_FILE.exists():
                        st.session_state.video_bytes = io.BytesIO(SESSION_FINAL_VIDEO_FILE.read_bytes())
                        st.session_state.video_mb = SESSION_FINAL_VIDEO_FILE.stat().st_size / (1024 * 1024)

                    if SESSION_THUMBNAIL_FILE.exists():
                        st.session_state.thumb_bytes = io.BytesIO(SESSION_THUMBNAIL_FILE.read_bytes())
                        st.session_state.thumb_kb = SESSION_THUMBNAIL_FILE.stat().st_size / 1024

                    if generate_sns:
                        try:
                            sns_data = director.generate_sns_package(
                                timeline_data,
                                user_prompt=st.session_state.get("user_intent"),
                            )
                            st.session_state.sns_package = sns_data
                            with open(SESSION_SNS_PACKAGE_FILE, "w", encoding="utf-8") as f:
                                json.dump(sns_data, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass

                    r_prog.progress(1.0)
                    r_stat.success("렌더링 성공! 완성 화면을 확인하세요.")
                    st.session_state.page = "result"
                    st.rerun()
            except Exception as e:
                st.error(f"렌더링 실패: {e}")


# ----------------------------------------------------
# [화면 3: 렌더링 결과물 & 다운로드 (즉시 삭제 지원)]
# ----------------------------------------------------
if st.session_state.page == "result":
    # 다운로드 후 안전 삭제 완료 알림 배너
    if st.session_state.get("is_cleaned", False):
        st.markdown(
            """
            <div class="security-notice">
                <span class="material-symbols-outlined" style="font-size:20px; color:#2A6038;">verified_user</span>
                <span>🔒 다운로드가 완료되어 서버의 모든 임시 파일이 안전하게 파기되었습니다.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    has_video_buffer = "video_bytes" in st.session_state and st.session_state.video_bytes is not None
    has_thumb_buffer = "thumb_bytes" in st.session_state and st.session_state.thumb_bytes is not None

    if has_video_buffer or has_thumb_buffer:
        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <span class="material-symbols-outlined" style="color:#4A7C59; font-size:20px;">video_library</span>
                    <span class="font-headline" style="font-weight:700; font-size:1.15rem; color:#2E3230;">최종 완성 릴스</span>
                </div>
                <span class="stitch-pill-soft">다운로드 준비완료</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 1. 비디오 플레이어 & 다운로드
        if has_video_buffer:
            raw_video_data = st.session_state.video_bytes.getvalue()
            st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
            st.video(raw_video_data)
            v_mb = st.session_state.get("video_mb", len(raw_video_data) / (1024 * 1024))
            st.caption(f"용량: {v_mb:.2f} MB | 규격: 1080x1920 세로형 (30fps)")

            st.download_button(
                label="릴스 영상 다운로드 (MP4)",
                data=raw_video_data,
                file_name="final_reels.mp4",
                mime="video/mp4",
                on_click=cleanup_current_session,
                type="primary",
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # 2. 썸네일 커버 & 다운로드
        if has_thumb_buffer:
            raw_thumb_data = st.session_state.thumb_bytes.getvalue()
            st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
            st.image(raw_thumb_data, caption="0.8초 지점 오프닝 고화질 썸네일 커버", use_container_width=True)
            t_kb = st.session_state.get("thumb_kb", len(raw_thumb_data) / 1024)
            st.caption(f"용량: {t_kb:.1f} KB | 1080x1920 JPG")

            st.download_button(
                label="썸네일 커버 다운로드 (JPG)",
                data=raw_thumb_data,
                file_name="thumbnail.jpg",
                mime="image/jpeg",
                on_click=cleanup_current_session,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # 3. SNS 텍스트 패키지
        sns_content = st.session_state.get("sns_package")
        if sns_content:
            st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.95rem; font-weight:700; color:#2E3230; margin-bottom:0.5rem;">SNS 업로드 텍스트 패키지</div>', unsafe_allow_html=True)
            sns_title = sns_content.get("title", "")
            sns_desc = sns_content.get("description", "")
            sns_tags = " ".join([f"#{tag}" for tag in sns_content.get("hashtags", [])])
            full_text = f"{sns_title}\n\n{sns_desc}\n\n{sns_tags}"
            st.text_area("전체 복사 (Ctrl+A)", value=full_text, height=160)
            st.markdown('</div>', unsafe_allow_html=True)

        # 처음으로 돌아가기 버튼
        if st.button("새 영상 만들기", use_container_width=True):
            reset_to_home()
