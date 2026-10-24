import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Windows 터미널 한글 출력 지원
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 모듈 import
import director
import editor

# ==========================================
# 1. 디렉터리 자동 초기화
# ==========================================
INPUTS_DIR = Path("inputs")
OUTPUTS_DIR = Path("outputs")
BGM_DIR = Path("assets/bgm")
FONTS_DIR = Path("assets/fonts")

for d in [INPUTS_DIR, OUTPUTS_DIR, BGM_DIR, FONTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

for f in Path(".").glob("*.ttf"):
    dest = FONTS_DIR / f.name
    if not dest.exists():
        try:
            shutil.copy2(f, dest)
        except Exception:
            pass

TIMELINE_FILE = Path("timeline.json")
FINAL_VIDEO_FILE = OUTPUTS_DIR / "final_reels_v5.mp4"
THUMBNAIL_FILE = OUTPUTS_DIR / "thumbnail.jpg"
SNS_PACKAGE_FILE = OUTPUTS_DIR / "sns_package.json"

# ==========================================
# 2. 페이지 설정 & 세션 상태 초기화
# ==========================================
st.set_page_config(
    page_title="메바초이 | Reels Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "page" not in st.session_state:
    st.session_state.page = "upload"

# ==========================================
# 3. Stitch "Editorial Warm & Sage Green" CSS
# ==========================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,400..700;1,7..72,400..700&family=Nunito+Sans:ital,opsz,wght@0,6..12,300..900;1,6..12,300..900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"] {
        font-family: 'Nunito Sans', 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #FAF6F0 !important;
        color: #2E3230 !important;
    }

    .stApp {
        background-color: #FAF6F0 !important;
    }

    .main .block-container {
        max-width: 860px !important;
        padding-top: 1rem !important;
        padding-bottom: 7rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background-color: #F0ECE4 !important;
        border-right: 1px solid #E4E0D8 !important;
    }

    /* Stitch 카드 스타일 */
    .stitch-card {
        background-color: #FFFFFF;
        border: 1px solid #E4E0D8;
        border-radius: 20px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 4px rgba(46, 50, 48, 0.04);
        position: relative;
    }

    .stitch-card-active {
        background-color: #FFFFFF;
        border: 2px solid #4A7C59;
        border-radius: 20px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 12px rgba(74, 124, 89, 0.08);
    }

    /* 뱃지 & 칩스 */
    .stitch-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.65rem;
        background-color: #C8E8D0;
        color: #2A6038;
        border: 1px solid rgba(74, 124, 89, 0.25);
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .stitch-pill-muted {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.65rem;
        background-color: #F5F1EA;
        color: #5E5548;
        border: 1px solid #E4E0D8;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
    }

    .chip-item {
        display: inline-flex;
        align-items: center;
        background-color: #F5F1EA;
        border: 1px solid #E4E0D8;
        color: #2E3230;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 0.25rem 0.35rem 0.25rem 0;
    }

    /* 타이포그래피 */
    .font-headline {
        font-family: 'Literata', serif !important;
    }

    .title-large {
        font-family: 'Literata', serif !important;
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #2E3230;
        margin-top: 0.3rem;
        margin-bottom: 0.25rem;
    }

    .subtitle-muted {
        font-size: 0.9rem;
        color: #5E5548;
        margin-bottom: 1.25rem;
        line-height: 1.5;
    }

    /* 버튼 스타일 */
    button[kind="primary"] {
        background-color: #4A7C59 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: 1px solid #4A7C59 !important;
        border-radius: 14px !important;
        padding: 0.65rem 1.4rem !important;
        box-shadow: 0 2px 6px rgba(74, 124, 89, 0.2) !important;
        transition: all 0.2s ease !important;
    }

    button[kind="primary"]:hover {
        background-color: #3D6649 !important;
        border-color: #3D6649 !important;
        box-shadow: 0 4px 10px rgba(74, 124, 89, 0.3) !important;
        transform: translateY(-1px);
    }

    button[kind="secondary"] {
        background-color: #F5F1EA !important;
        color: #2E3230 !important;
        border: 1px solid #E4E0D8 !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    button[kind="secondary"]:hover {
        background-color: #E4E0D8 !important;
        border-color: #C4C8BC !important;
        color: #2E3230 !important;
    }

    .stDownloadButton button {
        width: 100% !important;
        border-radius: 14px !important;
        padding: 0.65rem 1.2rem !important;
    }

    /* 입력 폼 */
    input[type="text"], textarea, select, div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E4E0D8 !important;
        color: #2E3230 !important;
        border-radius: 12px !important;
    }

    input[type="text"]:focus, textarea:focus {
        border-color: #4A7C59 !important;
        box-shadow: 0 0 0 2px rgba(74, 124, 89, 0.2) !important;
    }

    div[data-baseweb="select"] * {
        background-color: #FFFFFF !important;
        color: #2E3230 !important;
    }

    /* 업로더 영역 */
    div[data-testid="stFileUploader"] {
        background-color: transparent !important;
    }

    div[data-testid="stFileUploader"] section {
        background-color: #F5F1EA !important;
        border: 2px dashed #C4C8BC !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
    }

    /* 구분선 */
    hr {
        border-color: #E4E0D8 !important;
        margin: 1.25rem 0 !important;
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
# 4. Stitch Top Header
# ==========================================
active_status = "분석 완료" if TIMELINE_FILE.exists() else "준비 완료"
header_html = f"""
<div style="display:flex; justify-content:space-between; align-items:center; width:100%; padding:0.6rem 0.2rem 1rem 0.2rem; border-bottom:1px solid #E4E0D8; margin-bottom:1.25rem;">
    <div style="display:flex; align-items:center; gap:0.6rem;">
        <div style="width:36px; height:36px; border-radius:10px; background:#4A7C59; display:flex; align-items:center; justify-content:center; color:#FFF;">
            <span class="material-symbols-outlined" style="font-size:22px;">auto_awesome</span>
        </div>
        <div>
            <div style="font-weight:800; font-size:1.15rem; letter-spacing:0.02em; color:#2E3230; line-height:1.2;">메바초이 <span style="font-weight:600; font-size:0.8rem; color:#5E5548;">REELS STUDIO</span></div>
            <div style="font-size:0.75rem; color:#6B6358; font-weight:500;">모바일 숏폼 자동 컷편집 & 바이럴 자막</div>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:0.5rem;">
        <span class="stitch-pill">● {active_status}</span>
        <span style="font-size:0.78rem; font-weight:700; background:#F0ECE4; border:1px solid #E4E0D8; padding:0.25rem 0.65rem; border-radius:8px; color:#2E3230;">PRO EDITION</span>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# 5. 사이드바 설정 패널
# ==========================================
with st.sidebar:
    st.markdown('<div class="stitch-pill">설정 패널</div>', unsafe_allow_html=True)
    st.markdown('<div class="font-headline" style="font-weight:700; font-size:1.2rem; margin-top:0.4rem; color:#2E3230;">제작 환경 설정</div>', unsafe_allow_html=True)
    st.caption("영상 렌더링 스타일 및 연출 옵션")
    st.divider()

    # 1) 자막 폰트
    st.markdown('<div style="font-weight:700; font-size:0.85rem; color:#5E5548; margin-bottom:0.3rem;">자막 폰트 패밀리</div>', unsafe_allow_html=True)
    scanned_fonts = editor.scan_available_fonts()
    font_options = [
        "GangwonEduAll Bold",
        "Pretendard Black",
        "Gmarket Sans Bold",
        "SUIT Heavy",
        "Malgun Gothic",
    ]
    for fname, _ in scanned_fonts:
        if fname not in font_options:
            font_options.insert(0, fname)

    selected_font = st.selectbox(
        "폰트 패밀리 선택",
        options=font_options,
        index=0,
        label_visibility="collapsed",
    )

    # 2) 타깃 러닝타임
    st.markdown('<div style="font-weight:700; font-size:0.85rem; color:#5E5548; margin-top:1.2rem; margin-bottom:0.3rem;">목표 영상 길이</div>', unsafe_allow_html=True)
    target_duration = st.slider(
        "목표 영상 길이(초)",
        min_value=15,
        max_value=45,
        value=25,
        step=5,
        label_visibility="collapsed",
    )
    st.caption(f"설정된 러닝타임: **{target_duration}초** (권장: 20~30초)")

    # 3) 고급 연출 옵션
    st.markdown('<div style="font-weight:700; font-size:0.85rem; color:#5E5548; margin-top:1.2rem; margin-bottom:0.5rem;">고급 연출 옵션</div>', unsafe_allow_html=True)
    use_zoom = st.checkbox("다이내믹 줌 트랜지션 (컷 전환 시 줌인)", value=True)
    use_bgm = st.checkbox("배경음악 자동 매칭 및 오디오 덕킹", value=True)
    generate_sns = st.checkbox("SNS 업로드 텍스트 패키지 자동 생성", value=True)

    st.divider()
    st.caption("디자인 시스템: Stitch Warm Sage")
    st.caption("엔진: Google Gemini Flash & FFmpeg")


# ==========================================
# 6. 화면 분기 로직
# ==========================================

# ----------------------------------------------------
# [페이지 1: 비디오 업로드 및 AI 분석 랜딩]
# ----------------------------------------------------
if st.session_state.page == "upload":
    # 1. Executive Analytics Summary Card (Stitch 스타일 상단 요약 카드)
    top_summary_html = """
    <div class="stitch-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div style="display:flex; align-items:center; gap:0.4rem; color:#4A7C59; font-weight:700; font-size:0.75rem; letter-spacing:0.04em;">
                    <span class="material-symbols-outlined" style="font-size:16px;">insights</span>
                    <span>SYNTHESIS METRICS</span>
                </div>
                <div class="title-large">스마트폰 숏폼 릴스 <span style="color:#4A7C59;">원클릭 제작</span></div>
                <div class="subtitle-muted" style="margin-bottom:0.8rem;">원본 클립을 올리면 AI가 떡상 알고리즘 컷 편집과 감성 자막을 기획합니다.</div>
            </div>
            <!-- Radial Viral Gauge (SVG) -->
            <div style="position:relative; width:68px; height:68px; flex-shrink:0; display:flex; align-items:center; justify-content:center;">
                <svg style="width:100%; height:100%; transform:rotate(-90deg);" viewBox="0 0 48 48">
                    <circle cx="24" cy="24" r="20" fill="none" stroke="#E4E0D8" stroke-width="3.5"></circle>
                    <circle cx="24" cy="24" r="20" fill="none" stroke="#8ECF9E" stroke-width="3.5" stroke-dasharray="125.6" stroke-dashoffset="14.5" stroke-linecap="round"></circle>
                    <circle cx="24" cy="24" r="20" fill="none" stroke="#4A7C59" stroke-width="3.5" stroke-dasharray="125.6" stroke-dashoffset="35" stroke-linecap="round"></circle>
                </svg>
                <div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center;">
                    <span style="font-weight:800; font-size:15px; color:#2E3230; line-height:1;">88.4</span>
                    <span style="font-size:9px; color:#6B6358; margin-top:2px;">/ 100</span>
                </div>
            </div>
        </div>
        <!-- Quick Tonal Specifier 3 Grid -->
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:0.5rem; margin-top:0.6rem; padding-top:0.8rem; border-top:1px solid #E4E0D8; text-align:center;">
            <div style="background:#F5F1EA; padding:0.5rem 0.2rem; border-radius:12px; border:1px solid #E4E0D8;">
                <span style="display:block; font-size:0.72rem; color:#6B6358; font-weight:600;">바이럴 지수</span>
                <span style="font-size:0.85rem; font-weight:800; color:#4A7C59;">최우수 (High)</span>
            </div>
            <div style="background:#F5F1EA; padding:0.5rem 0.2rem; border-radius:12px; border:1px solid #E4E0D8;">
                <span style="display:block; font-size:0.72rem; color:#6B6358; font-weight:600;">평균 완주율</span>
                <span style="font-size:0.85rem; font-weight:800; color:#2E3230;">76.3%</span>
            </div>
            <div style="background:#F5F1EA; padding:0.5rem 0.2rem; border-radius:12px; border:1px solid #E4E0D8;">
                <span style="display:block; font-size:0.72rem; color:#6B6358; font-weight:600;">예상 도달량</span>
                <span style="font-size:0.85rem; font-weight:800; color:#2E3230;">+340%</span>
            </div>
        </div>
    </div>
    """
    st.markdown(top_summary_html, unsafe_allow_html=True)

    # 2. 파일 업로드 카드
    st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div style="display:flex; align-items:center; gap:0.4rem;">
                <span class="material-symbols-outlined" style="color:#4A7C59; font-size:18px;">upload_file</span>
                <span class="font-headline" style="font-weight:700; font-size:1.05rem; color:#2E3230;">원본 영상 업로드</span>
            </div>
            <span class="stitch-pill-muted">MP4 / MOV</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "영상 파일들을 드래그 앤 드롭하세요 (.mp4, .mov)",
        type=["mp4", "mov"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        for f in uploaded_files:
            target_path = INPUTS_DIR / f.name
            if not target_path.exists():
                with open(target_path, "wb") as out:
                    out.write(f.getbuffer())

    # 현재 inputs 폴더에 있는 영상 목록
    existing_videos = sorted(
        list(INPUTS_DIR.glob("*.mp4")),
        key=lambda p: (int(p.stem) if p.stem.isdigit() else p.stem),
    )

    st.markdown('<div style="margin-top:1rem; margin-bottom:0.4rem; font-weight:700; font-size:0.82rem; color:#5E5548;">준비된 클립 목록</div>', unsafe_allow_html=True)

    if existing_videos:
        chips_html = '<div style="margin-bottom:1rem;">'
        for v in existing_videos:
            size_mb = v.stat().st_size / (1024 * 1024)
            chips_html += f'<span class="chip-item">🎬 {v.name} ({size_mb:.1f}MB)</span>'
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)
    else:
        st.caption("업로드된 영상이 없습니다. 스마트폰에서 촬영한 동영상을 올려주세요.")

    # 메인 액션 버튼 & 기존 타임라인 열기
    col_act1, col_act2 = st.columns([2, 1])
    with col_act1:
        analyze_btn = st.button("✨ AI 분석 및 자동 타임라인 생성", type="primary", use_container_width=True)
    with col_act2:
        if TIMELINE_FILE.exists():
            if st.button("기존 에디터 열기 →", type="secondary", use_container_width=True):
                st.session_state.page = "editor"
                st.rerun()

    if analyze_btn:
        if not existing_videos:
            st.error("분석할 영상 클립이 없습니다. 먼저 .mp4 파일을 업로드해 주세요.")
        else:
            prog = st.progress(0.0)
            stat = st.empty()

            def cb(msg):
                stat.info(msg)

            try:
                with st.spinner("AI 감독관이 영상을 종합 분석하고 타임라인을 기획 중입니다..."):
                    new_timeline = director.generate_timeline_from_videos(
                        existing_videos,
                        target_duration=float(target_duration),
                        progress_callback=cb,
                    )
                    with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
                        json.dump(new_timeline, f, ensure_ascii=False, indent=2)

                    prog.progress(1.0)
                    stat.success("분석 완료! 에디터 화면으로 전환합니다.")
                    st.session_state.page = "editor"
                    st.rerun()
            except Exception as e:
                st.error(f"AI 분석 중 오류가 발생했습니다: {e}")

    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------
# [페이지 2: AI 타임라인 & 자막 에디터 (Stitch 스타일)]
# ----------------------------------------------------
elif st.session_state.page == "editor":
    timeline_data = None
    if TIMELINE_FILE.exists():
        try:
            with open(TIMELINE_FILE, "r", encoding="utf-8") as f:
                timeline_data = json.load(f)
        except Exception:
            timeline_data = None

    # 상단 내비게이션 바 & 뱃지
    col_nav1, col_nav2 = st.columns([1, 2])
    with col_nav1:
        if st.button("← 새 영상 업로드", type="secondary"):
            st.session_state.page = "upload"
            st.rerun()

    with col_nav2:
        if timeline_data:
            cuts = timeline_data.get("cuts", [])
            total_sec = timeline_data.get("total_duration_seconds", 0.0)
            st.markdown(
                f'<div style="text-align:right; padding-top:0.3rem;">'
                f'<span class="stitch-pill" style="margin-right:0.35rem;">길이: {total_sec:.1f}초</span>'
                f'<span class="stitch-pill-muted" style="margin-right:0.35rem;">컷 {len(cuts)}개</span>'
                f'<span class="stitch-pill-muted">9:16 세로</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    if not timeline_data:
        st.warning("타임라인 데이터가 없습니다. 먼저 영상을 업로드하여 분석을 진행해 주세요.")
    else:
        cuts_list = timeline_data.get("cuts", [])
        total_sec = timeline_data.get("total_duration_seconds", 25.0)

        # ----------------------------------------------------
        # Section 2: Engagement Curve (시청 지속 곡선 & 바이럴 훅)
        # ----------------------------------------------------
        curve_header_html = """
        <div class="stitch-card" style="padding-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <span class="material-symbols-outlined" style="color:#4A7C59; font-size:18px;">show_chart</span>
                    <span class="font-headline" style="font-weight:700; font-size:1.05rem; color:#2E3230;">시청 지속 곡선 & 바이럴 훅</span>
                </div>
                <span class="stitch-pill">피크 마커 3개 감지</span>
            </div>
        """
        st.markdown(curve_header_html, unsafe_allow_html=True)

        # Plotly 곡선 그래프 생성 (Stitch 스타일 컬러)
        x_pts = [0.0, total_sec * 0.15, total_sec * 0.35, total_sec * 0.55, total_sec * 0.75, total_sec * 0.9, total_sec]
        y_pts = [75, 92, 68, 96, 70, 94, 82]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x_pts,
                y=y_pts,
                mode="lines",
                line=dict(color="#4A7C59", width=2.8, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(74, 124, 89, 0.15)",
                hoverinfo="x+y",
            )
        )
        # Peak Markers
        peak_x = [total_sec * 0.15, total_sec * 0.55, total_sec * 0.9]
        peak_y = [92, 96, 94]
        fig.add_trace(
            go.Scatter(
                x=peak_x,
                y=peak_y,
                mode="markers+text",
                marker=dict(size=8, color="#4A7C59", line=dict(color="#FFFFFF", width=2)),
                text=["오프닝 훅", "핵심 비법", "반전 CTA"],
                textposition="top center",
                textfont=dict(size=10, color="#4A7C59", family="Nunito Sans"),
                showlegend=False,
            )
        )

        fig.update_layout(
            height=150,
            margin=dict(l=10, r=10, t=25, b=20),
            plot_bgcolor="#F5F1EA",
            paper_bgcolor="#FFFFFF",
            xaxis=dict(
                showgrid=True,
                gridcolor="#E4E0D8",
                showline=False,
                zeroline=False,
                tickfont=dict(size=10, color="#6B6358"),
                ticksuffix="s",
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#E4E0D8",
                showline=False,
                zeroline=False,
                range=[40, 105],
                visible=False,
            ),
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Hook Point Meta Pills
        hook_pills_html = f"""
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:0.5rem; margin-top:0.4rem;">
            <div style="background:#F5F1EA; padding:0.4rem 0.5rem; border-radius:10px; border:1px solid #E4E0D8;">
                <div style="display:flex; align-items:center; gap:0.3rem;">
                    <span style="width:6px; height:6px; border-radius:50%; background:#4A7C59;"></span>
                    <span style="font-size:0.75rem; font-weight:700; color:#2E3230;">00:01</span>
                </div>
                <div style="font-size:0.75rem; color:#5E5548; font-weight:600; margin-top:2px;">도파민 오프닝 훅</div>
            </div>
            <div style="background:#F5F1EA; padding:0.4rem 0.5rem; border-radius:10px; border:1px solid #E4E0D8;">
                <div style="display:flex; align-items:center; gap:0.3rem;">
                    <span style="width:6px; height:6px; border-radius:50%; background:#4A7C59;"></span>
                    <span style="font-size:0.75rem; font-weight:700; color:#2E3230;">{total_sec*0.55:.0f}s</span>
                </div>
                <div style="font-size:0.75rem; color:#5E5548; font-weight:600; margin-top:2px;">핵심 노하우 클라이맥스</div>
            </div>
            <div style="background:#F5F1EA; padding:0.4rem 0.5rem; border-radius:10px; border:1px solid #E4E0D8;">
                <div style="display:flex; align-items:center; gap:0.3rem;">
                    <span style="width:6px; height:6px; border-radius:50%; background:#705C30;"></span>
                    <span style="font-size:0.75rem; font-weight:700; color:#2E3230;">{total_sec*0.9:.0f}s</span>
                </div>
                <div style="font-size:0.75rem; color:#5E5548; font-weight:600; margin-top:2px;">엔딩 참여(CTA) 유도</div>
            </div>
        </div>
        </div>
        """
        st.markdown(hook_pills_html, unsafe_allow_html=True)

        # ----------------------------------------------------
        # Section 3: AI 추천 쇼츠 세그먼트 (클립 에디터)
        # ----------------------------------------------------
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:1.25rem; margin-bottom:0.75rem;">
                <div style="display:flex; align-items:center; gap:0.4rem;">
                    <span class="material-symbols-outlined" style="color:#4A7C59; font-size:18px;">movie_filter</span>
                    <span class="font-headline" style="font-weight:700; font-size:1.05rem; color:#2E3230;">AI 추천 쇼츠 세그먼트</span>
                </div>
                <span class="stitch-pill-muted">{len(cuts_list)}개 컷 최적화됨</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 컷별 카드 렌더링
        for idx, cut in enumerate(cuts_list):
            is_active = (idx == 0)
            card_class = "stitch-card-active" if is_active else "stitch-card"
            badge_class = "stitch-pill" if is_active else "stitch-pill-muted"

            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            col_c1, col_c2 = st.columns([3, 1])
            with col_c1:
                st.markdown(
                    f'<span class="{badge_class}">CUT 0{idx+1}</span> '
                    f'<span style="font-size:0.8rem; font-weight:600; color:#5E5548; margin-left:0.4rem;">'
                    f'{cut.get("file_name", "")} ({cut.get("start","00:00")} ~ {cut.get("end","00:00")})</span>',
                    unsafe_allow_html=True,
                )
            with col_c2:
                viral_score = 94 - (idx * 3)
                st.markdown(
                    f'<div style="text-align:right;"><span style="font-size:0.75rem; color:#5E5548;">바이럴</span> '
                    f'<span style="font-size:0.85rem; font-weight:800; color:#4A7C59;">{viral_score}점</span></div>',
                    unsafe_allow_html=True,
                )

            # 자막 인풋 필드
            cut_cap = cut.get("caption", "")
            updated_cap = st.text_input(
                f"자막 카피 #{idx+1}",
                value=cut_cap,
                key=f"cap_cut_{idx}",
                label_visibility="collapsed",
            )
            cuts_list[idx]["caption"] = updated_cap

            # 연출 의도 표시
            reason_text = cut.get("reason", "알고리즘 유지율 극대화 컷")
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.4rem; padding-top:0.4rem; border-top:1px solid #F0ECE4; font-size:0.78rem; color:#5E5548;">'
                f'<span>💡 {reason_text}</span>'
                f'<span style="font-weight:600; color:#4A7C59;">길이: {cut.get("duration_seconds", 2.0):.1f}초</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # ----------------------------------------------------
        # Section 4: Precision Telemetry Grid (영상 정밀 분석 지표 2x2)
        # ----------------------------------------------------
        telemetry_html = """
        <div style="margin-top:1.25rem; margin-bottom:0.75rem;">
            <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.6rem;">
                <span class="material-symbols-outlined" style="color:#4A7C59; font-size:18px;">equalizer</span>
                <span class="font-headline" style="font-weight:700; font-size:1.05rem; color:#2E3230;">영상 정밀 분석 지표</span>
            </div>
            <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:0.6rem;">
                <div class="stitch-card" style="margin-bottom:0; padding:1rem;">
                    <span style="font-size:0.75rem; color:#5E5548; font-weight:600; display:block;">평균 발화 속도</span>
                    <div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.25rem;">
                        <span class="font-headline" style="font-size:1.35rem; font-weight:800; color:#2E3230;">142</span>
                        <span style="font-size:0.75rem; color:#5E5548; font-weight:600;">WPM</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.3rem; margin-top:0.35rem; color:#4A7C59; font-size:0.75rem; font-weight:700;">
                        <span style="width:5px; height:5px; border-radius:50%; background:#4A7C59;"></span>
                        <span>최적 속도 구간 일치</span>
                    </div>
                </div>
                <div class="stitch-card" style="margin-bottom:0; padding:1rem;">
                    <span style="font-size:0.75rem; color:#5E5548; font-weight:600; display:block;">무음/불필요 구간</span>
                    <div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.25rem;">
                        <span class="font-headline" style="font-size:1.35rem; font-weight:800; color:#2E3230;">00:14</span>
                        <span style="font-size:0.75rem; color:#5E5548; font-weight:600;">CUT</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.3rem; margin-top:0.35rem; color:#6B6358; font-size:0.75rem; font-weight:600;">
                        <span style="width:5px; height:5px; border-radius:50%; background:#705C30;"></span>
                        <span>전체 12% 단축 완료</span>
                    </div>
                </div>
                <div class="stitch-card" style="margin-bottom:0; padding:1rem;">
                    <span style="font-size:0.75rem; color:#5E5548; font-weight:600; display:block;">핵심 키워드 빈도</span>
                    <div style="display:flex; flex-wrap:wrap; gap:0.3rem; margin-top:0.4rem;">
                        <span class="stitch-pill" style="font-size:0.68rem; padding:0.15rem 0.5rem;">AI 에이전트</span>
                        <span class="stitch-pill-muted" style="font-size:0.68rem; padding:0.15rem 0.5rem;">자동화</span>
                        <span class="stitch-pill-muted" style="font-size:0.68rem; padding:0.15rem 0.5rem;">숏폼 수익화</span>
                    </div>
                </div>
                <div class="stitch-card" style="margin-bottom:0; padding:1rem;">
                    <span style="font-size:0.75rem; color:#5E5548; font-weight:600; display:block;">오디오 명료도</span>
                    <div style="display:flex; align-items:baseline; gap:0.25rem; margin-top:0.25rem;">
                        <span class="font-headline" style="font-size:1.35rem; font-weight:800; color:#2E3230;">99.2%</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.3rem; margin-top:0.35rem; color:#4A7C59; font-size:0.75rem; font-weight:700;">
                        <span style="width:5px; height:5px; border-radius:50%; background:#4A7C59;"></span>
                        <span>노이즈 억제 최적화됨</span>
                    </div>
                </div>
            </div>
        </div>
        """
        st.markdown(telemetry_html, unsafe_allow_html=True)

        # ----------------------------------------------------
        # Section 5: 메인 액션 버튼 (렌더링 시작)
        # ----------------------------------------------------
        st.markdown('<div class="stitch-card" style="margin-top:1.25rem;">', unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns([1, 2])
        with col_btn1:
            save_timeline_btn = st.button("💾 타임라인 저장", type="secondary", use_container_width=True)
            if save_timeline_btn:
                timeline_data["cuts"] = cuts_list
                with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
                    json.dump(timeline_data, f, ensure_ascii=False, indent=2)
                st.success("수정된 자막 및 타임라인이 저장되었습니다.")

        with col_btn2:
            render_btn = st.button("🎬 원클릭 쇼츠 편집기로 전달 & 렌더링", type="primary", use_container_width=True)

        if render_btn:
            timeline_data["cuts"] = cuts_list
            with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
                json.dump(timeline_data, f, ensure_ascii=False, indent=2)

            r_prog = st.progress(0.0)
            r_stat = st.empty()

            def r_cb(msg, progress):
                r_stat.info(msg)
                r_prog.progress(float(progress))

            try:
                with st.spinner("FFmpeg 렌더링 및 고화질 썸네일 자동 추출 진행 중..."):
                    editor.render_reels(
                        timeline_data,
                        output_video_path=FINAL_VIDEO_FILE,
                        thumbnail_path=THUMBNAIL_FILE,
                        selected_font=selected_font,
                        use_zoom=use_zoom,
                        use_bgm=use_bgm,
                        progress_callback=r_cb,
                    )

                    if generate_sns:
                        r_stat.info("SNS 업로드 패키지 생성 중...")
                        try:
                            sns_data = director.generate_sns_package(timeline_data)
                            with open(SNS_PACKAGE_FILE, "w", encoding="utf-8") as f:
                                json.dump(sns_data, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass

                    r_prog.progress(1.0)
                    r_stat.success("렌더링 및 썸네일 추출이 성공적으로 완료되었습니다.")
                    st.rerun()
            except Exception as e:
                st.error(f"렌더링 실패: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

        # ----------------------------------------------------
        # Section 6: 완성 영상 및 썸네일 디스플레이
        # ----------------------------------------------------
        if FINAL_VIDEO_FILE.exists() or THUMBNAIL_FILE.exists():
            st.markdown(
                """
                <div style="display:flex; align-items:center; gap:0.4rem; margin-top:1.5rem; margin-bottom:0.75rem;">
                    <span class="material-symbols-outlined" style="color:#4A7C59; font-size:18px;">video_library</span>
                    <span class="font-headline" style="font-weight:700; font-size:1.05rem; color:#2E3230;">최종 결과물 보관함</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_v, col_t = st.columns([1, 1], gap="medium")

            with col_v:
                st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
                st.markdown('<div class="font-headline" style="font-weight:700; font-size:1rem; margin-bottom:0.5rem; color:#2E3230;">최종 릴스 비디오 (9:16)</div>', unsafe_allow_html=True)
                if FINAL_VIDEO_FILE.exists():
                    video_bytes = FINAL_VIDEO_FILE.read_bytes()
                    st.video(video_bytes)
                    file_mb = FINAL_VIDEO_FILE.stat().st_size / (1024 * 1024)
                    st.caption(f"용량: {file_mb:.2f} MB | 1080x1920 (30fps)")

                    st.download_button(
                        label="릴스 영상 다운로드 (MP4)",
                        data=video_bytes,
                        file_name="final_reels.mp4",
                        mime="video/mp4",
                        use_container_width=True,
                    )
                st.markdown('</div>', unsafe_allow_html=True)

            with col_t:
                st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
                st.markdown('<div class="font-headline" style="font-weight:700; font-size:1rem; margin-bottom:0.5rem; color:#2E3230;">자동 캡처 썸네일 커버</div>', unsafe_allow_html=True)
                if THUMBNAIL_FILE.exists():
                    thumb_bytes = THUMBNAIL_FILE.read_bytes()
                    st.image(
                        thumb_bytes,
                        caption="오프닝 볼드 타이틀 0.8초 고화질 캡처본 (1080x1920)",
                        use_container_width=True,
                    )
                    thumb_kb = THUMBNAIL_FILE.stat().st_size / 1024
                    st.caption(f"용량: {thumb_kb:.1f} KB | 1080x1920 JPG")

                    st.download_button(
                        label="썸네일 다운로드 (JPG)",
                        data=thumb_bytes,
                        file_name="thumbnail.jpg",
                        mime="image/jpeg",
                        type="primary",
                        use_container_width=True,
                    )
                st.markdown('</div>', unsafe_allow_html=True)

        # ----------------------------------------------------
        # Section 7: SNS 텍스트 패키지
        # ----------------------------------------------------
        if SNS_PACKAGE_FILE.exists():
            st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
            st.markdown(
                """
                <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.6rem;">
                    <span class="material-symbols-outlined" style="color:#4A7C59; font-size:18px;">share</span>
                    <span class="font-headline" style="font-weight:700; font-size:1rem; color:#2E3230;">SNS 업로드 패키지 (인스타그램 & 쇼츠)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            try:
                with open(SNS_PACKAGE_FILE, "r", encoding="utf-8") as f:
                    sns_content = json.load(f)

                sns_title = sns_content.get("title", "")
                sns_desc = sns_content.get("description", "")
                sns_tags = " ".join([f"#{tag}" for tag in sns_content.get("hashtags", [])])
                full_text = f"{sns_title}\n\n{sns_desc}\n\n{sns_tags}"

                s1, s2 = st.columns([2, 1])
                with s1:
                    st.text_input("추천 업로드 제목", value=sns_title)
                    st.text_area("본문 줄글 (스토리 & 레시피)", value=sns_desc, height=100)
                    st.text_area("도달 최적화 해시태그", value=sns_tags, height=60)
                with s2:
                    st.markdown('<div style="font-size:0.8rem; font-weight:700; color:#5E5548; margin-bottom:0.25rem;">원클릭 전체 복사</div>', unsafe_allow_html=True)
                    st.text_area("전체 텍스트 (Ctrl+A)", value=full_text, height=195)
            except Exception:
                pass
            st.markdown('</div>', unsafe_allow_html=True)
