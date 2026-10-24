import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from tqdm import tqdm

# Windows 터미널에서 한국어 UTF-8 출력을 보장하도록 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 환경 변수 로드
load_dotenv()


# ==========================================
# 1. 숏폼 기획안 구조화 스키마 정의 (Pydantic)
# ==========================================
class OpeningHook(BaseModel):
    line1_highlight: str = Field(description="4~6글자 이내의 극도로 임팩트 있는 노란색 키워드 (예: '호두 쏟아부은!')")
    line2_sub: str = Field(description="시청자의 궁금증을 자극하는 흰색 질문 카피 (예: '카페 사장님 비밀 레시피?')")


class ShortCut(BaseModel):
    cut_index: int = Field(description="컷 순번 (1부터 시작하는 순번)", ge=1)
    source_file: str = Field(description="해당 컷이 포함된 원본 영상 파일명 (예: '8.mp4')")
    start_time: str = Field(description="구간 시작 타임스탬프 (예: '00:02.00')")
    end_time: str = Field(description="구간 종료 타임스탬프 (예: '00:04.00')")
    duration: float = Field(description="해당 컷의 길이(초 단위, 1.2~2.5초 권장)")
    caption: str = Field(description="자막 문구 (1번 컷은 2줄 카피, 중간 컷은 4~8글자의 직관적 단어형 문구)")
    zoom_in: bool = Field(description="디테일/질감/손동작 강조를 위한 줌인 트랜지션 여부 (True/False)", default=False)
    action_role: str = Field(description="해당 컷의 연출상 역할 및 강조 포인트 (예: '완성작 클로즈업 후킹', '재료 볶는 소리와 질감 강조')")


class ShortDirectorPlan(BaseModel):
    title: str = Field(description="조회수를 부르는 매력적인 숏폼 제목")
    concept: str = Field(description="감각적인 손동작과 바삭한 질감을 극대화한 고급 숏폼 연출 콘셉트")
    bgm_vibe: str = Field(description="영상에 어울리는 트렌디하고 세련된 배경음악(BGM) 추천")
    opening_hook: OpeningHook = Field(description="첫 1~2초 오프닝 훅 (1줄 노란색 키워드 + 2줄 흰색 질문 카피)")
    ending_cta: str = Field(description="자연스러운 소장/저장 유도 엔딩 문구 (예: '진짜 맛있는 건 나눠 먹어야죠 ✨')")
    cuts: List[ShortCut] = Field(description="오프닝 훅부터 결말까지 재배치된 최종 컷 목록")


class SNSPackage(BaseModel):
    title: str = Field(description="인스타그램 및 유튜브 쇼츠 업로드용 후킹형 제목 (이모지 포함)")
    description: str = Field(description="시청자의 공감과 저장을 유도하는 감성적이고 친절한 본문 줄글 (재료 및 꿀팁 포함)")
    hashtags: List[str] = Field(description="도달률을 극대화하는 인기 해시태그 15개 (# 제외 단어 목록)")


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(".env 파일 또는 환경변수에 GEMINI_API_KEY가 설정되어 있지 않습니다.")
    return genai.Client(api_key=api_key)


# ==========================================
# 2. 영상 업로드 및 상태 대기 함수
# ==========================================
def upload_and_wait_videos(video_paths: List[Path], client=None, progress_callback=None):
    """비디오 파일들을 Files API로 업로드하고 ACTIVE 상태가 될 때까지 대기합니다."""
    if client is None:
        client = get_gemini_client()

    uploaded_files = []
    total = len(video_paths)

    for idx, video_path in enumerate(video_paths, start=1):
        if progress_callback:
            progress_callback(f"[{idx}/{total}] Gemini 서버로 영상 업로드 중: {video_path.name}")
        file_obj = client.files.upload(file=str(video_path))
        uploaded_files.append((video_path, file_obj))

    ready_files = []
    for idx, (video_path, file_obj) in enumerate(uploaded_files, start=1):
        if progress_callback:
            progress_callback(f"[{idx}/{total}] Gemini 서버 비디오 인코딩 대기 중: {video_path.name}")
        while file_obj.state.name == "PROCESSING":
            time.sleep(2)
            file_obj = client.files.get(name=file_obj.name)

        if file_obj.state.name == "FAILED":
            raise RuntimeError(f"파일 처리 실패: {video_path.name}")

        ready_files.append((video_path, file_obj))

    return ready_files


# ==========================================
# 3. AI 타임라인 기획 생성 함수
# ==========================================
def generate_timeline_from_videos(
    video_files: List[Path],
    target_duration: float = 25.0,
    progress_callback=None,
) -> dict:
    client = get_gemini_client()

    ready_files = upload_and_wait_videos(video_files, client=client, progress_callback=progress_callback)

    if progress_callback:
        progress_callback("감각적인 숏폼 총괄 디렉터 AI가 영상들을 정밀 분석하고 타임라인을 기획 중입니다...")

    contents = []
    for idx, (path, f_obj) in enumerate(ready_files, start=1):
        contents.append(f"[클립 {idx} 정보: 파일명='{path.name}']")
        contents.append(f_obj)

    prompt = f"""
당신은 대한민국 최정상급의 감각적이고 고급스러운 [숏폼 총괄 디렉터]입니다.
재료의 질감이 살아나는 매크로 샷, 정교한 손동작, 절제된 리듬감, 시각적 쾌감을 최우선 가치로 두고 제공된 {len(video_files)}개의 영상 클립을 분석해 최상의 숏폼 편집 기획안을 완성해 주십시오.

[🎬 숏폼 총괄 디렉터 연출 원칙]
1. 🚨 첫 1~2초 후킹 (Opening Hook) - 시각적 쾌감 극대화:
   - 절대로 조리/제작 과정을 순서대로 시작하지 마십시오.
   - 전체 영상 중 가장 시각적 쾌감이 극대화된 하이라이트(완성작 클로즈업, 자르는 순간의 단면, 쏟아지는 질감 등)를 무조건 맨 첫 컷(1.2초~2.5초)으로 파격 배치하십시오.
   - 오프닝 훅(opening_hook) 카피:
     * line1_highlight: 4~6글자 이내의 극도로 임팩트 있는 노란색 강조 키워드 (예: "호두 쏟아부은!", "겉바속촉 미쳤다")
     * line2_sub: 시청자의 궁금증을 자극하는 흰색 질문 카피 (예: "카페 사장님 비밀 레시피?", "이걸 집에서 만든다고?")
   - 1번 컷의 caption은 반드시 이 두 문장을 줄바꿈(\\n)으로 연결하여 작성하십시오. (예: "호두 쏟아부은!\\n비밀 레시피?")

2. ⚡ 중간 컷 자막 (Process) - 설명조 금지, 단어형 문구:
   - 설명조의 긴 줄글은 절대 금지합니다.
   - 1줄당 4~8글자 이내로 씹히듯이 직관적인 단어형 문구로 작성하십시오.
     (예: "노릇하게 볶기", "풍미 끌어올리기", "결대로 썰기", "바삭함 가두기")

3. 🔁 엔딩 CTA (Ending Hook) - 자연스러운 소장/저장 유도:
   - 억지 팔로우 강요는 철저히 배제합니다.
   - 시청자가 자연스럽게 영상을 저장(Save)하고 공유하고 싶어지도록 따뜻하고 감각적인 문구를 작성하십시오.
     (예: "진짜 맛있는 건 나눠 먹어야죠 ✨", "주말에 꼭 만들어보세요 📌")
   - 마지막 완성 컷의 caption에도 이 감성을 자연스럽게 반영하십시오.

4. ⏱️ 컷 길이 및 리듬감:
   - 총 러닝타임은 {target_duration:.1f}초 내외(20~30초 기준)로 타이트하게 구성하십시오.
   - 지루한 준비 대기 시간은 과감히 잘라내고, 컷당 길이를 1.2초 ~ 2.5초 내외로 배치하여 속도감과 리듬감을 극대화하십시오.

5. 🔍 줌인 트랜지션 (zoom_in):
   - 손동작의 정교함, 재료가 볶아지거나 썰리는 질감, 완성작의 클로즈업 디테일이 강조되어야 하는 핵심 컷은 "zoom_in": true 플래그를 부여하십시오.
"""
    contents.append(prompt)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ShortDirectorPlan,
                temperature=0.7,
            ),
        )

        plan_data = json.loads(response.text)

        # 기존 app.py 및 editor.py와의 완전한 하위/상위 호환성 보장
        total_dur = 0.0
        for cut in plan_data.get("cuts", []):
            dur = float(cut.get("duration", 2.0))
            total_dur += dur
            cut["duration"] = dur
            # 기존 레거시 필드 자동 매핑
            cut["file_name"] = cut.get("source_file", "")
            cut["start"] = cut.get("start_time", "00:00")
            cut["end"] = cut.get("end_time", "00:00")
            cut["duration_seconds"] = dur
            cut["reason"] = cut.get("action_role", "")

        plan_data["total_duration_seconds"] = round(total_dur, 2)
        return plan_data

    finally:
        # 클라우드 업로드 파일 정리
        for _, f_obj in ready_files:
            try:
                client.files.delete(name=f_obj.name)
            except Exception:
                pass


# ==========================================
# 4. SNS 업로드 패키지 자동 생성 함수
# ==========================================
def generate_sns_package(timeline_data: dict) -> dict:
    """타임라인 기획안을 바탕으로 인스타그램/유튜브 쇼츠 업로드용 제목, 본문, 해시태그 패키지를 생성합니다."""
    client = get_gemini_client()

    title = timeline_data.get("title", "")
    concept = timeline_data.get("concept", "")
    cuts_summary = "\n".join([f"- {c.get('caption')}" for c in timeline_data.get("cuts", [])])

    prompt = f"""
당신은 인스타그램 릴스와 유튜브 쇼츠 마케팅 전문 카피라이터입니다.
아래의 릴스 영상 기획안을 바탕으로 시청자의 폭발적인 참여(좋아요, 저장, 댓글, 공유)를 이끌어낼 [SNS 업로드 패키지]를 작성해 주세요.

[영상 제목]: {title}
[영상 콘셉트]: {concept}
[영상 자막 흐름]:
{cuts_summary}

다음 항목을 포함하여 JSON으로 작성하십시오:
1. title: 조회수를 부르는 매력적인 숏폼 제목 (이모지 포함)
2. description: 본문 줄글 (인스타 감성의 친절하고 매력적인 레시피/디저트 소개글, 저장 유도 문구 포함)
3. hashtags: 인스타그램 및 유튜브에서 가장 도달률이 높은 해시태그 15개 (# 기호 제외한 키워드 리스트)
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SNSPackage,
            temperature=0.8,
        ),
    )

    return json.loads(response.text)


# ==========================================
# 5. CLI 단독 실행 엔트리포인트
# ==========================================
def main():
    inputs_dir = Path("inputs")
    if not inputs_dir.exists():
        print("[오류] inputs 폴더가 존재하지 않습니다.")
        return

    video_files = sorted(
        list(inputs_dir.glob("*.mp4")),
        key=lambda p: (int(p.stem) if p.stem.isdigit() else p.stem),
    )

    if not video_files:
        print("[안내] inputs/ 폴더에 .mp4 영상 파일이 없습니다.")
        return

    print(f"📁 총 {len(video_files)}개의 원본 클립을 발견했습니다.")
    plan_data = generate_timeline_from_videos(video_files, target_duration=30.0)

    output_file = Path("timeline.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, ensure_ascii=False, indent=2)

    print(f"💾 기획안 데이터가 저장되었습니다: {output_file.resolve()}")


if __name__ == "__main__":
    main()
