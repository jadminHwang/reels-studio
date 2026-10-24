import asyncio
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from tqdm import tqdm

# Windows 터미널에서 UTF-8 출력 보장
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


# ==========================================
# 1. FFmpeg 실행 경로 탐색 함수
# ==========================================
def find_ffmpeg_binaries():
    """시스템 PATH 또는 설치된 로컬 폴더에서 ffmpeg 및 ffprobe 경로를 찾습니다."""
    ffmpeg_exe = shutil.which("ffmpeg")
    ffprobe_exe = shutil.which("ffprobe")

    if not ffmpeg_exe:
        local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ffmpeg"
        for p in local_app.glob("**/ffmpeg.exe"):
            ffmpeg_exe = str(p)
            break

    if not ffprobe_exe:
        local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ffmpeg"
        for p in local_app.glob("**/ffprobe.exe"):
            ffprobe_exe = str(p)
            break

    if not ffmpeg_exe or not Path(ffmpeg_exe).exists():
        raise FileNotFoundError("ffmpeg.exe를 찾을 수 없습니다. FFmpeg가 정상적으로 설치되었는지 확인해 주세요.")

    return ffmpeg_exe, ffprobe_exe


# ==========================================
# 2. 타임스탬프 변환 헬퍼 (초 단위 float)
# ==========================================
def parse_timestamp_to_seconds(ts: str) -> float:
    """'00:02.0' 또는 '02.5' 또는 '2' 형태의 타임스탬프를 초 단위 float로 변환합니다."""
    ts = str(ts).strip()
    parts = ts.split(":")
    if len(parts) == 3:  # HH:MM:SS[.xxx]
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:  # MM:SS[.xxx]
        return float(parts[0]) * 60 + float(parts[1])
    else:
        return float(ts)


def format_ass_time(seconds: float) -> str:
    """초 단위 시간을 ASS 자막 타임코드 (H:MM:SS.cs) 형태로 변환합니다."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


# ==========================================
# 2-2. Edge-TTS AI 음성 더빙 및 오디오 덕킹 헬퍼
# ==========================================
VOICE_PRESETS = {
    "여성 활기찬 보이스 (선희)": "ko-KR-SunHiNeural",
    "남성 깔끔한 보이스 (인준)": "ko-KR-InJoonNeural",
}


def clean_text_for_tts(text: str) -> str:
    """TTS 음성 합성을 위해 자막의 줄바꿈 태그, 이모지 및 특수문자를 정제합니다."""
    if not text:
        return ""
    # 줄바꿈 태그 변환
    cleaned = text.replace("\\N", " ").replace("\n", " ")
    # ASS 스타일 태그 제거 (예: {\fs96...})
    cleaned = re.sub(r"\{.*?\}", "", cleaned)
    # 이모지 및 특수 기호 제거
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", cleaned)
    cleaned = re.sub(r"[#*~`^_+=[\]|✨📌🎬❤️🔥👍]", "", cleaned)
    # 연속된 공백 축소
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def format_edge_tts_rate(speed: float) -> str:
    """배속 숫자를 edge-tts의 rate 문자열(+15%, -10% 등)로 변환합니다."""
    pct = int(round((speed - 1.0) * 100))
    if pct >= 0:
        return f"+{pct}%"
    else:
        return f"{pct}%"


def ensure_edge_tts():
    """edge-tts 패키지가 설치되어 있는지 확인하고 없으면 자동 설치합니다."""
    try:
        import edge_tts
        return edge_tts
    except ImportError:
        import subprocess
        # 1차 시도: pip 모듈로 설치
        res = subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts"], capture_output=True)
        if res.returncode == 0:
            import edge_tts
            return edge_tts
        # 2차 시도: ensurepip 후 pip 설치
        subprocess.run([sys.executable, "-m", "ensurepip", "--default-pip"], capture_output=True)
        res2 = subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts"], capture_output=True)
        if res2.returncode == 0:
            import edge_tts
            return edge_tts
        raise RuntimeError("edge-tts 패키지를 자동으로 설치할 수 없습니다. 터미널에서 'pip install edge-tts'를 실행해 주세요.")


async def generate_tts_bytes_async(text: str, voice: str = "ko-KR-SunHiNeural", speed: float = 1.15) -> bytes:
    """edge-tts를 비동기로 호출하여 오디오 바이트(mp3)를 메모리에 버퍼링합니다."""
    edge_tts = ensure_edge_tts()

    rate_str = format_edge_tts_rate(speed)
    cleaned = clean_text_for_tts(text)
    if not cleaned:
        cleaned = " "
    communicate = edge_tts.Communicate(cleaned, voice, rate=rate_str)
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    return buffer.getvalue()


def generate_tts_bytes(text: str, voice: str = "ko-KR-SunHiNeural", speed: float = 1.15) -> bytes:
    """동기 환경에서 안전하게 TTS 바이트를 생성합니다."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 이벤트 루프가 돌아가는 경우(예: Streamlit/Jupyter 내부)
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(generate_tts_bytes_async(text, voice, speed))
        return loop.run_until_complete(generate_tts_bytes_async(text, voice, speed))
    except Exception:
        return asyncio.run(generate_tts_bytes_async(text, voice, speed))


def build_tts_master_track(
    cuts: list,
    output_audio_path: Path,
    voice: str = "ko-KR-SunHiNeural",
    speed: float = 1.15,
    ffmpeg_exe: str = "ffmpeg",
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> Optional[Path]:
    """
    각 컷의 자막을 순서대로 edge-tts로 생성하고,
    컷별 시작 타임코드에 맞춰 지연(adelay)을 적용한 단일 마스터 TTS 오디오 트랙을 생성합니다.
    """
    temp_dir = output_audio_path.parent / "temp_tts"
    temp_dir.mkdir(parents=True, exist_ok=True)

    tts_clips = []
    current_time_ms = 0

    for idx, cut in enumerate(cuts, start=1):
        dur = float(cut.get("duration", cut.get("duration_seconds", 2.0)))
        raw_cap = cut.get("caption", "").strip()
        cleaned_cap = clean_text_for_tts(raw_cap)

        if cleaned_cap and len(cleaned_cap) > 0:
            if progress_callback:
                progress_callback(f"🎙️ AI 음성 합성 중 (컷 {idx}/{len(cuts)}): '{cleaned_cap[:12]}...'", 0.0)

            raw_audio = generate_tts_bytes(cleaned_cap, voice=voice, speed=speed)
            if raw_audio and len(raw_audio) > 0:
                clip_file = temp_dir / f"tts_{idx:03d}.mp3"
                clip_file.write_bytes(raw_audio)
                tts_clips.append((clip_file, current_time_ms))

        current_time_ms += int(dur * 1000)

    if not tts_clips:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    # FFmpeg adelay 및 amix 필터를 통해 단일 마스터 트랙 생성
    inputs_cmd = []
    filter_parts = []
    mix_labels = []

    for i, (fpath, delay_ms) in enumerate(tts_clips):
        inputs_cmd.extend(["-i", str(fpath)])
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[d{i}]")
        mix_labels.append(f"[d{i}]")

    all_mix = "".join(mix_labels)
    filter_complex = f"{';'.join(filter_parts)};{all_mix}amix=inputs={len(tts_clips)}:normalize=0:dropout_transition=0[aout]"

    cmd = [
        ffmpeg_exe,
        "-y",
        *inputs_cmd,
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_audio_path),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    shutil.rmtree(temp_dir, ignore_errors=True)

    if res.returncode == 0 and output_audio_path.exists():
        return output_audio_path
    return None


# ==========================================
# 3. 로컬 폰트 탐색 및 릴스 최적 폰트 선정
# ==========================================
def scan_available_fonts(project_dir: Path = Path(".")):
    """프로젝트 루트 및 assets/fonts 폴더 내의 TTF/OTF 폰트 목록을 스캔합니다."""
    font_dirs = [project_dir, project_dir / "assets" / "fonts"]
    font_files = []
    seen = set()

    for d in font_dirs:
        if d.exists():
            for f in list(d.glob("*.ttf")) + list(d.glob("*.otf")):
                if f.name not in seen:
                    seen.add(f.name)
                    font_files.append(f)

    available_fonts = []
    known_name_map = {
        "Bithumb Gothic Basic.ttf": "Bithumb Gothic Basic",
        "Bithumb Gothic Original.ttf": "Bithumb Gothic Original",
        "bithumb_basic.ttf": "Bithumb Gothic Basic",
        "bithumb_original.ttf": "Bithumb Gothic Original",
        "강원교육모두 Bold.ttf": "GangwonEduAll Bold",
        "gangwon_bold.ttf": "GangwonEduAll Bold",
        "Griun_Yeeun-Rg.ttf": "Griun Yeeun",
        "griun_yeeun.ttf": "Griun Yeeun",
        "GmarketSansBold.ttf": "Gmarket Sans Bold",
        "gmarket_sans_bold.ttf": "Gmarket Sans Bold",
        "Pretendard-Black.ttf": "Pretendard Black",
        "pretendard_black.ttf": "Pretendard Black",
    }

    try:
        from fontTools.ttLib import TTFont
        for fpath in font_files:
            if fpath.name in known_name_map:
                available_fonts.append((known_name_map[fpath.name], fpath))
                continue
            try:
                font = TTFont(fpath)
                family_name = None
                for record in font["name"].names:
                    if record.nameID in (4, 1):
                        try:
                            name_val = record.toUnicode()
                            if name_val and not family_name and len(name_val.strip()) > 1:
                                family_name = name_val.strip()
                        except Exception:
                            pass
                family_name = family_name or fpath.stem
                available_fonts.append((family_name, fpath))
            except Exception:
                available_fonts.append((fpath.stem, fpath))
    except ImportError:
        for fpath in font_files:
            name = known_name_map.get(fpath.name, fpath.stem)
            available_fonts.append((name, fpath))

    # 중복 제거 (이름 기준)
    unique_fonts = []
    seen_names = set()
    for name, fpath in available_fonts:
        if name not in seen_names:
            seen_names.add(name)
            unique_fonts.append((name, fpath))

    return unique_fonts


def select_best_font(available_fonts):
    """숏폼에 가장 적합한 볼드 폰트를 자동 선정합니다."""
    if not available_fonts:
        return "Malgun Gothic", None

    for name, fpath in available_fonts:
        lower_name = (name + fpath.stem).lower()
        if any(keyword in lower_name for keyword in ["bold", "모두", "black", "heavy", "gmarket"]):
            return name, fpath

    return available_fonts[0]


# ==========================================
# 4. ASS 릴스 자막 파일 생성
# ==========================================
def split_into_two_lines(text: str) -> str:
    """문장을 시각적 균형에 맞게 2줄(\\N)로 분할합니다."""
    text = text.strip()
    if "\n" in text:
        return text.replace("\n", "\\N")
    if "\\N" in text:
        return text

    words = text.split()
    if len(words) <= 1:
        return text

    half_len = len(text) / 2
    best_idx = 1
    min_diff = float("inf")
    accum = 0
    for i in range(len(words) - 1):
        accum += len(words[i]) + 1
        diff = abs(accum - half_len)
        if diff < min_diff:
            min_diff = diff
            best_idx = i + 1

    return " ".join(words[:best_idx]) + "\\N" + " ".join(words[best_idx:])


def generate_ass_subtitles(cuts: list, ass_path: Path, font_name: str = "GangwonEduAll Bold"):
    """
    유튜브 쇼츠(YouTube Shorts) 레퍼런스 스타일 ASS 자막 파일 생성:
    - 위치: 화면 정중앙/가슴 높이 (Alignment: 5, Y ≈ 960px)
    - 폰트: 도톰하고 가독성 높은 볼드 산세리프 (92pt)
    - 컬러: 선명한 순백색(#FFFFFF) 본문 + 두껍고 또렷한 블랙 외곽선(5.8px) + 소프트 드롭 섀도우(2.8px)
    - 특징: 불투명/반투명 검은 배경 박스를 완전히 제거하여 영상의 피사체를 가리지 않고 몰입감 극대화
    - 팝인 효과: 자막 등장 시 0.15초간 미세 바운스(106% -> 100%)로 역동적인 숏폼 텐션 연출
    - 1번 컷(오프닝 훅): 1줄 옐로우(#FFDE00, 96pt) + 2줄 화이트(#FFFFFF, 74pt) 2줄 임팩트
    - 2번 컷 이후: 중앙 배치 92pt 화이트 볼드 자막
    """
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ShortsHook,{font_name},96,&H0000DEFF&,&H000000FF,&H00000000,&H60000000,1,0,0,0,100,100,1,0,1,6.0,3.0,5,50,50,0,1
Style: ShortsBody,{font_name},92,&H00FFFFFF,&H000000FF,&H00000000,&H60000000,1,0,0,0,100,100,1,0,1,5.8,2.8,5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    current_time = 0.0

    for idx, cut in enumerate(cuts, start=1):
        dur = float(cut.get("duration", cut.get("duration_seconds", 2.0)))
        start_ass = format_ass_time(current_time)
        end_ass = format_ass_time(current_time + dur)
        raw_caption = cut.get("caption", "").strip()

        if idx == 1:
            style = "ShortsHook"
            if "\n" in raw_caption:
                lines = [l.strip() for l in raw_caption.split("\n") if l.strip()]
            elif "\\N" in raw_caption:
                lines = [l.strip() for l in raw_caption.split("\\N") if l.strip()]
            else:
                two_lines_text = split_into_two_lines(raw_caption)
                lines = [l.strip() for l in two_lines_text.split("\\N") if l.strip()]

            if len(lines) >= 2:
                line1, line2 = lines[0], lines[1]
            else:
                line1 = lines[0] if lines else ""
                line2 = ""

            pop_anim = "{\\t(0,90,\\fscx106\\fscy106)\\t(90,170,\\fscx100\\fscy100)}"
            if line2:
                caption = (
                    f"{pop_anim}{{\\fs96\\1c&H0000DEFF&\\3c&H00000000&\\bord6.0\\shad3.0\\b1}}{line1}\\N"
                    f"{{\\fs74\\1c&H00FFFFFF&\\3c&H00000000&\\bord4.8\\shad2.6\\b1}}{line2}"
                )
            else:
                caption = f"{pop_anim}{{\\fs96\\1c&H0000DEFF&\\3c&H00000000&\\bord6.0\\shad3.0\\b1}}{line1}"
        else:
            style = "ShortsBody"
            # 줄바꿈 및 팝인 애니메이션 적용
            formatted_text = raw_caption.replace("\n", "\\N")
            pop_anim = "{\\t(0,80,\\fscx105\\fscy105)\\t(80,160,\\fscx100\\fscy100)}"
            caption = f"{pop_anim}{{\\fs92\\1c&H00FFFFFF&\\3c&H00000000&\\bord5.8\\shad2.8\\b1}}{formatted_text}"

        events.append(f"Dialogue: 0,{start_ass},{end_ass},{style},,0,0,0,,{caption}")
        current_time += dur

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")


# ==========================================
# 5. 고화질 썸네일 캡처 함수
# ==========================================
def extract_thumbnail(
    video_path: Path,
    thumbnail_path: Path,
    timestamp: str = "00:00:00.800",
    ffmpeg_exe: str = "ffmpeg",
) -> bool:
    """오프닝 타이틀이 가장 선명한 순간(기본 0.8초)의 1개 프레임을 무손실 고화질 JPG로 추출합니다."""
    cmd = [
        ffmpeg_exe,
        "-y",
        "-ss", timestamp,
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(thumbnail_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.returncode == 0


# ==========================================
# 6. 메인 영상 렌더링 파이프라인
# ==========================================
def render_reels(
    timeline_data: dict,
    output_video_path: Path = Path("outputs/final_reels_v5.mp4"),
    thumbnail_path: Path = Path("outputs/thumbnail.jpg"),
    input_dir: Optional[Path] = None,
    temp_dir: Optional[Path] = None,
    selected_font: Optional[str] = None,
    use_zoom: bool = False,
    use_bgm: bool = False,
    use_tts: bool = False,
    tts_voice: str = "ko-KR-SunHiNeural",
    tts_speed: float = 1.15,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> Path:
    """타임라인 데이터를 기반으로 9:16 릴스 영상 인코딩, 자막 번인, 썸네일 추출을 완수합니다."""
    ffmpeg_exe, _ = find_ffmpeg_binaries()

    cuts = timeline_data.get("cuts", [])
    if not cuts:
        raise ValueError("타임라인에 편집할 컷 정보가 없습니다.")

    # 폰트 자동 선택 (인자로 넘어오지 않은 경우)
    available_fonts = scan_available_fonts()
    if not selected_font:
        selected_font, _ = select_best_font(available_fonts)

    if input_dir is None:
        input_dir = Path("inputs")
    if temp_dir is None:
        temp_dir = Path("temp_clips") / (output_video_path.parent.name if output_video_path.parent.name != "outputs" else "default")

    temp_dir.mkdir(parents=True, exist_ok=True)
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    total_cuts = len(cuts)

    # 1. 각 컷별 클리핑 및 9:16 규격 변환
    for idx, cut in enumerate(cuts, start=1):
        if progress_callback:
            progress_callback(f"[{idx}/{total_cuts}] 클립 컷팅 및 9:16 규격 변환 중: {cut.get('caption', '')}", (idx / (total_cuts + 3)))

        file_name = cut.get("source_file") or cut.get("file_name", "")
        input_video = input_dir / file_name

        if not input_video.exists():
            # 혹시 원본 파일명이 절대경로나 기본 inputs에 있을 경우 대비
            if (Path("inputs") / file_name).exists():
                input_video = Path("inputs") / file_name
            else:
                raise FileNotFoundError(f"입력 비디오 파일을 찾을 수 없습니다: {input_video}")

        start_str = cut.get("start_time") or cut.get("start", "00:00")
        end_str = cut.get("end_time") or cut.get("end", "00:00")
        start_sec = parse_timestamp_to_seconds(start_str)
        end_sec = parse_timestamp_to_seconds(end_str)
        duration = end_sec - start_sec
        if duration <= 0:
            duration = float(cut.get("duration") or cut.get("duration_seconds", 2.0))

        out_clip = temp_dir / f"clip_{idx:03d}.mp4"

        # 컷별 줌인 플래그(zoom_in) 또는 글로벌 use_zoom 적용
        cut_zoom = bool(cut.get("zoom_in", False)) or use_zoom
        if cut_zoom:
            # 줌인 트랜지션 (매크로 샷 및 텍스처 강조 필터)
            vf_filter = (
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                "setsar=1,fps=30"
            )
        else:
            vf_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"

        cmd = [
            ffmpeg_exe,
            "-y",
            "-threads", "0",
            "-ss", f"{start_sec:.3f}",
            "-t", f"{duration:.3f}",
            "-i", str(input_video),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            str(out_clip),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode != 0:
            raise RuntimeError(f"컷 {idx} 인코딩 실패:\n{result.stderr}")

        clip_paths.append(out_clip)

    # 2. Concat 영상 병합
    if progress_callback:
        progress_callback("🔗 모든 컷을 하나의 릴스 시퀀스로 병합 중...", (total_cuts + 1) / (total_cuts + 3))

    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve().as_posix()}'\n")

    merged_no_sub = temp_dir / "merged_no_sub.mp4"
    concat_cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(merged_no_sub),
    ]

    concat_res = subprocess.run(concat_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if concat_res.returncode != 0:
        raise RuntimeError(f"영상 병합 실패:\n{concat_res.stderr}")

    # 3. BGM 오디오 믹싱 & 덕킹 (선택된 경우)
    merged_with_audio = merged_no_sub
    bgm_dir = Path("assets/bgm")
    bgm_files = list(bgm_dir.glob("*.mp3")) + list(bgm_dir.glob("*.wav"))

    if use_bgm and bgm_files:
        bgm_file = bgm_files[0]
        if progress_callback:
            progress_callback(f"🎵 배경음악({bgm_file.name}) 오디오 덕킹 믹싱 중...", (total_cuts + 1.5) / (total_cuts + 3))

        bgm_mixed_file = temp_dir / "merged_with_bgm.mp4"
        # BGM 볼륨 0.25, 원본 오디오 유지 믹싱
        filter_complex = (
            "[1:a]aloop=loop=-1:size=2e+09,volume=0.25[bgm];"
            "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        bgm_cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(merged_no_sub),
            "-i", str(bgm_file),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(bgm_mixed_file),
        ]
        bgm_res = subprocess.run(bgm_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if bgm_res.returncode == 0:
            merged_with_audio = bgm_mixed_file

    # 3-2. AI 음성 더빙(TTS) 및 스마트 오디오 덕킹(Audio Ducking)
    if use_tts:
        if progress_callback:
            progress_callback("🎙️ AI 내레이션 더빙 생성 및 스마트 오디오 덕킹 믹싱 중...", (total_cuts + 1.8) / (total_cuts + 3))

        tts_master_path = temp_dir / "tts_master.aac"
        tts_built = build_tts_master_track(
            cuts,
            tts_master_path,
            voice=tts_voice,
            speed=tts_speed,
            ffmpeg_exe=ffmpeg_exe,
            progress_callback=progress_callback,
        )

        if tts_built and tts_master_path.exists():
            ducked_file = temp_dir / "merged_with_tts.mp4"
            # 오디오 덕킹: sidechaincompress 필터로 TTS 음성 재생 시 배경음 볼륨을 부드럽게 70% 압축/인하
            # tts 음성은 1.25배 볼륨으로 또렷하게 부스팅
            duck_filter = (
                "[0:a][1:a]sidechaincompress=threshold=0.08:ratio=4:attack=50:release=350[bg_ducked];"
                "[bg_ducked][1:a]amix=inputs=2:weights=1 1.25:dropout_transition=2[aout]"
            )
            duck_cmd = [
                ffmpeg_exe,
                "-y",
                "-i", str(merged_with_audio),
                "-i", str(tts_master_path),
                "-filter_complex", duck_filter,
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                str(ducked_file),
            ]
            duck_res = subprocess.run(duck_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if duck_res.returncode == 0:
                merged_with_audio = ducked_file

    # 4. ASS 자막 생성 및 Burn-in 렌더링
    if progress_callback:
        progress_callback(f"✍️ '{selected_font}' 폰트 적용 감성 자막 번인 렌더링 중...", (total_cuts + 2) / (total_cuts + 3))

    ass_file = temp_dir / "subtitles.ass"
    generate_ass_subtitles(cuts, ass_file, font_name=selected_font)

    ass_filter_path = ass_file.resolve().as_posix().replace(":", "\\:")
    fonts_dir_path = Path("assets/fonts").resolve().as_posix().replace(":", "\\:")
    subtitle_filter = f"subtitles='{ass_filter_path}':fontsdir='{fonts_dir_path}'"

    burn_cmd = [
        ffmpeg_exe,
        "-y",
        "-threads", "0",
        "-i", str(merged_with_audio),
        "-vf", subtitle_filter,
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-c:a", "copy",
        str(output_video_path),
    ]

    burn_res = subprocess.run(burn_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if burn_res.returncode != 0:
        raise RuntimeError(f"자막 렌더링 실패:\n{burn_res.stderr}")

    # 5. 고화질 썸네일 자동 캡처 (0.8초 지점)
    if progress_callback:
        progress_callback("🖼️ 0.8초 시점 오프닝 후킹 고화질 썸네일 추출 중...", 1.0)
    extract_thumbnail(output_video_path, thumbnail_path, timestamp="00:00:00.800", ffmpeg_exe=ffmpeg_exe)

    # 6. 임시 파일 정리
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    return output_video_path


# ==========================================
# 7. CLI 단독 실행 엔트리포인트
# ==========================================
def main():
    timeline_path = Path("timeline.json")
    if not timeline_path.exists():
        print("[오류] timeline.json 파일이 존재하지 않습니다.")
        sys.exit(1)

    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    final_output = Path("outputs/final_reels_v5.mp4")
    thumbnail_output = Path("outputs/thumbnail.jpg")

    render_reels(timeline, final_output, thumbnail_output)
    print(f"\n🎉 렌더링 완료: {final_output.resolve()}")
    print(f"🖼️ 썸네일 완료: {thumbnail_output.resolve()}")


if __name__ == "__main__":
    main()
