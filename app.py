import json
import os
import shutil
import subprocess
import sys
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
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "page" not in st.session_state:
    st.session_state.page = "upload"

# ==========================================
# 3. 스티치 테마 스타일 (웜 아이보리 & 세이지 그린)
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

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background-color: #F0ECE4 !important;
        border-right: 1px solid #E4E0D8 !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: #E4E0D8 !important;
    }

    /* 스티치 라운드 카드 */
    .stitch-card {
        background-color: #FFFFFF;
        border: 1px solid #E4E0D8;
        border-radius: 18px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(46, 50, 48, 0.04);
    }

    /* 뱃지 */
    .stitch-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.65rem;
        background-color: #C8E8D0;
        color: #2A6038;
        border: 1px solid rgba(74, 124, 89, 0.25);
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .stitch-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        background-color: #F5F1EA;
        color: #5E5548;
        border: 1px solid #E4E0D8;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.35rem;
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
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #2E3230;
        margin-top: 0.35rem;
        margin-bottom: 0.3rem;
    }

    .subtitle-muted {
        font-size: 0.92rem;
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
        border-radius: 12px !important;
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
        border-radius: 12px !important;
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

    div[data-baseweb="select"] * {
        background-color: #FFFFFF !important;
        color: #2E3230 !important;
    }

    /* 파일 업로더 */
    div[data-testid="stFileUploader"] {
        background-color: transparent !important;
    }

    div[data-testid="stFileUploader"] section {
        background-color: #F5F1EA !important;
        border: 2px dashed #C4C8BC !important;
        border-radius: 14px !important;
    }

    /* 구분선 */
    hr {
        border-color: #E4E0D8 !important;
        margin: 1.5rem 0 !important;
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
# 4. 상단 브랜드 헤더 (메바초이 REELS STUDIO)
# ==========================================
header_html = """
<div style="display:flex; justify-content:space-between; align-items:center; width:100%; padding:0.5rem 0.2rem 1rem 0.2rem; border-bottom:1px solid #E4E0D8; margin-bottom:1.5rem;">
    <div style="display:flex; align-items:center; gap:0.6rem;">
        <div style="width:38px; height:38px; border-radius:12px; background:#4A7C59; display:flex; align-items:center; justify-content:center; color:#FFF; box-shadow:0 2px 5px rgba(74,124,89,0.25);">
            <span class="material-symbols-outlined" style="font-size:22px;">auto_awesome</span>
        </div>
        <div>
            <div style="font-weight:800; font-size:1.15rem; letter-spacing:0.02em; color:#2E3230; line-height:1.2;">메바초이 <span style="font-weight:600; font-size:0.8rem; color:#5E5548;">REELS STUDIO</span></div>
            <div style="font-size:0.75rem; color:#6B6358; font-weight:500;">AI 숏폼 릴스 자동 편집기 & 감성 자막</div>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:0.5rem;">
        <span class="stitch-badge">● 서비스 정상</span>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# 5. 사이드바 설정 패널
# ==========================================
with st.sidebar:
    st.markdown('<div class="stitch-badge">환경 설정</div>', unsafe_allow_html=True)
    st.markdown('<div class="font-headline" style="font-weight:700; font-size:1.15rem; margin-top:0.4rem; margin-bottom:0.1rem; color:#2E3230;">제작 환경 설정</div>', unsafe_allow_html=True)
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
    st.caption("스타일: Stitch Warm Sage")
    st.caption("엔진: Google Gemini Flash & FFmpeg")


# ==========================================
# 6. 화면 분기 로직 (st.session_state.page)
# ==========================================

# ----------------------------------------------------
# [페이지 1: 비디오 업로드 랜딩]
# ----------------------------------------------------
if st.session_state.page == "upload":
    col_l1, col_l2 = st.columns([3, 1])
    with col_l1:
        st.markdown('<div class="stitch-badge">스튜디오</div>', unsafe_allow_html=True)
        st.markdown('<div class="title-large">영상 클립 업로드 및 숏폼 릴스 제작</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle-muted">촬영한 원본 클립들을 업로드하면 AI 감독관이 떡상 알고리즘 컷 편집과 감성 자막을 자동으로 기획합니다.</div>', unsafe_allow_html=True)
    with col_l2:
        if TIMELINE_FILE.exists():
            st.markdown('<div style="text-align:right; margin-top:1.2rem;">', unsafe_allow_html=True)
            if st.button("기존 타임라인 열기 →", type="secondary"):
                st.session_state.page = "editor"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="stitch-card">', unsafe_allow_html=True)

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

    st.markdown('<div style="margin-top:1rem; margin-bottom:0.5rem; font-weight:700; font-size:0.85rem; color:#5E5548;">업로드된 원본 영상 목록</div>', unsafe_allow_html=True)

    if existing_videos:
        chips_html = '<div style="margin-bottom:1.5rem;">'
        for v in existing_videos:
            size_mb = v.stat().st_size / (1024 * 1024)
            chips_html += f'<span class="chip-item">🎬 {v.name} ({size_mb:.1f}MB)</span>'
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)
    else:
        st.caption("아직 준비된 영상 파일이 없습니다. 상단 영역에 영상을 업로드해 주세요.")

    # 메인 액션 버튼
    st.markdown('<div style="margin-top:1.5rem;">', unsafe_allow_html=True)
    analyze_btn = st.button("✨ AI 분석 및 타임라인 생성", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
# [페이지 2: AI 타임라인 & 자막 에디터]
# ----------------------------------------------------
elif st.session_state.page == "editor":
    timeline_data = None
    if TIMELINE_FILE.exists():
        try:
            with open(TIMELINE_FILE, "r", encoding="utf-8") as f:
                timeline_data = json.load(f)
        except Exception:
            timeline_data = None

    # 상단 내비게이션 바 & 한글 요약 뱃지
    col_nav1, col_nav2 = st.columns([1, 3])
    with col_nav1:
        if st.button("← 새 영상 업로드", type="secondary"):
            st.session_state.page = "upload"
            st.rerun()

    with col_nav2:
        if timeline_data:
            cuts = timeline_data.get("cuts", [])
            total_sec = timeline_data.get("total_duration_seconds", 0.0)
            st.markdown(
                f'<div style="text-align:right; padding-top:0.4rem;">'
                f'<span class="stitch-pill">제목: {timeline_data.get("title", "")[:16]}..</span>'
                f'<span class="stitch-pill">길이: {total_sec:.1f}초</span>'
                f'<span class="stitch-pill">컷 수: {len(cuts)}개</span>'
                f'<span class="stitch-badge">9:16 세로 릴스</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    if not timeline_data:
        st.warning("타임라인 데이터가 없습니다. 먼저 영상을 업로드하여 분석을 진행해 주세요.")
    else:
        cuts_list = timeline_data.get("cuts", [])

        # 1. 자막 및 타임라인 에디터 폼
        st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
        st.markdown('<div class="font-headline" style="font-weight:700; font-size:1.2rem; color:#2E3230; margin-bottom:0.25rem;">타임라인 및 자막 에디터</div>', unsafe_allow_html=True)
        st.caption("AI가 기획한 컷 구간과 자막을 직접 검토하고 필요에 맞게 자유롭게 수정하세요.")

        # 주요 카피 2열 배치 (오프닝 훅 2줄 / 엔딩 CTA)
        col_h, col_e = st.columns(2)
        with col_h:
            st.markdown('<div style="font-size:0.85rem; font-weight:700; color:#4A7C59; margin-bottom:0.3rem;">오프닝 후킹 자막 (1번 컷)</div>', unsafe_allow_html=True)
            hook_text = st.text_area(
                "오프닝 2줄 텍스트 (줄바꿈으로 1번째 줄 노랑 볼드 / 2번째 줄 흰색 질문 카피 구분)",
                value=cuts_list[0].get("caption", "") if cuts_list else "",
                height=70,
                key="editor_hook_copy",
                label_visibility="collapsed",
            )
            if cuts_list:
                cuts_list[0]["caption"] = hook_text

        with col_e:
            st.markdown('<div style="font-size:0.85rem; font-weight:700; color:#4A7C59; margin-bottom:0.3rem;">엔딩 CTA 자막 (마지막 컷)</div>', unsafe_allow_html=True)
            end_text = st.text_area(
                "엔딩 자막",
                value=cuts_list[-1].get("caption", "") if cuts_list else "",
                height=70,
                key="editor_end_copy",
                label_visibility="collapsed",
            )
            if cuts_list:
                cuts_list[-1]["caption"] = end_text

        # 전체 컷별 타임스탬프 & 자막 데이터 에디터
        st.markdown('<div style="margin-top:1.2rem; margin-bottom:0.3rem; font-size:0.85rem; font-weight:700; color:#5E5548;">전체 시퀀스 편집 테이블</div>', unsafe_allow_html=True)
        df_editor = pd.DataFrame(cuts_list)
        col_order = ["clip_index", "file_name", "start", "end", "duration_seconds", "caption", "reason"]
        df_editor = df_editor[[c for c in col_order if c in df_editor.columns]]

        edited_df = st.data_editor(
            df_editor,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "clip_index": st.column_config.NumberColumn("순번", width="small", disabled=True),
                "file_name": st.column_config.TextColumn("클립 파일", width="medium"),
                "start": st.column_config.TextColumn("시작 구간", width="small"),
                "end": st.column_config.TextColumn("종료 구간", width="small"),
                "duration_seconds": st.column_config.NumberColumn("길이(초)", format="%.1f", width="small"),
                "caption": st.column_config.TextColumn("적용 자막", width="large"),
                "reason": st.column_config.TextColumn("연출 의도", width="large"),
            },
            hide_index=True,
        )

        col_save_btn, _ = st.columns([1, 3])
        with col_save_btn:
            if st.button("타임라인 수정사항 저장", type="secondary"):
                updated_cuts = edited_df.to_dict(orient="records")
                timeline_data["cuts"] = updated_cuts
                timeline_data["total_duration_seconds"] = sum(float(c.get("duration_seconds", 2.0)) for c in updated_cuts)
                with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
                    json.dump(timeline_data, f, ensure_ascii=False, indent=2)
                st.success("타임라인 수정사항이 timeline.json에 저장되었습니다.")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # 2. 렌더링 액션 버튼
        st.markdown('<div style="margin-bottom:1.5rem;">', unsafe_allow_html=True)
        render_btn = st.button("🎬 최종 릴스 영상 렌더링", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if render_btn:
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

        # 3. 렌더링 결과물 2단 디스플레이
        if FINAL_VIDEO_FILE.exists() or THUMBNAIL_FILE.exists():
            col_v, col_t = st.columns([1, 1], gap="large")

            with col_v:
                st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
                st.markdown('<div class="font-headline" style="font-weight:700; font-size:1.05rem; margin-bottom:0.75rem; color:#2E3230;">최종 완성 영상 (1080x1920 세로 릴스)</div>', unsafe_allow_html=True)
                if FINAL_VIDEO_FILE.exists():
                    video_bytes = FINAL_VIDEO_FILE.read_bytes()
                    st.video(video_bytes)
                    file_mb = FINAL_VIDEO_FILE.stat().st_size / (1024 * 1024)
                    st.caption(f"파일: {FINAL_VIDEO_FILE.name} | 용량: {file_mb:.2f} MB | 해상도: 1080x1920 (30fps)")

                    st.download_button(
                        label="릴스 영상 다운로드 (MP4)",
                        data=video_bytes,
                        file_name="final_reels.mp4",
                        mime="video/mp4",
                    )
                st.markdown('</div>', unsafe_allow_html=True)

            with col_t:
                st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
                st.markdown('<div class="font-headline" style="font-weight:700; font-size:1.05rem; margin-bottom:0.75rem; color:#2E3230;">자동 캡처 썸네일 커버 (0.8초 지점)</div>', unsafe_allow_html=True)
                if THUMBNAIL_FILE.exists():
                    thumb_bytes = THUMBNAIL_FILE.read_bytes()
                    st.image(
                        thumb_bytes,
                        caption="오프닝 볼드 타이틀이 가장 선명한 순간의 고화질 캡처본 (1080x1920)",
                        use_container_width=True,
                    )
                    thumb_kb = THUMBNAIL_FILE.stat().st_size / 1024
                    st.caption(f"파일: {THUMBNAIL_FILE.name} | 용량: {thumb_kb:.1f} KB | 규격: 1080x1920 JPG")

                    st.download_button(
                        label="썸네일 커버 다운로드 (JPG)",
                        data=thumb_bytes,
                        file_name="thumbnail.jpg",
                        mime="image/jpeg",
                        type="primary",
                    )
                st.markdown('</div>', unsafe_allow_html=True)

        # 4. SNS 업로드 패키지 영역
        if SNS_PACKAGE_FILE.exists():
            st.markdown('<div class="stitch-card">', unsafe_allow_html=True)
            st.markdown('<div class="font-headline" style="font-weight:700; font-size:1.05rem; margin-bottom:0.75rem; color:#2E3230;">SNS 업로드 패키지 (인스타그램 & 유튜브 쇼츠)</div>', unsafe_allow_html=True)
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
                    st.text_area("본문 줄글 (스토리 & 레시피)", value=sns_desc, height=120)
                    st.text_area("도달 최적화 해시태그 15선", value=sns_tags, height=70)
                with s2:
                    st.markdown('<div style="font-size:0.85rem; font-weight:700; color:#5E5548; margin-bottom:0.3rem;">원클릭 전체 복사 영역</div>', unsafe_allow_html=True)
                    st.text_area("전체 텍스트 (Ctrl+A 후 복사)", value=full_text, height=230)
            except Exception:
                pass
            st.markdown('</div>', unsafe_allow_html=True)
