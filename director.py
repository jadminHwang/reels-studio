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
class ClipCut(BaseModel):
    clip_index: int = Field(description="편집 시퀀스 순서 (1부터 시작하는 순번)", ge=1)
    file_name: str = Field(description="해당 컷이 포함된 원본 영상 파일명 (예: '8.mp4')")
    start: str = Field(description="선정된 구간의 시작 타임스탬프 (예: '00:01' 또는 '00:01.5')")
    end: str = Field(description="선정된 구간의 종료 타임스탬프 (예: '00:03' 또는 '00:03.0')")
    duration_seconds: float = Field(description="해당 컷의 길이(초 단위, 1.5~2.5초 권장)")
    caption: str = Field(description="10자 내외의 직관적이고 임팩트 있는 강조형 숏폼 자막 (한국어)")
    reason: str = Field(description="이 장면을 이 타이밍에 배치한 연출/알고리즘적 이유")


class ReelsPlan(BaseModel):
    title: str = Field(description="조회수를 부르는 매력적인 후킹형 릴스 제목")
    concept: str = Field(description="알고리즘 떡상을 위한 시청 지속 시간 극대화 연출 콘셉트")
    total_duration_seconds: float = Field(description="전체 편집 완성본의 총 길이 (초 단위)")
    bgm_vibe: str = Field(description="영상에 어울리는 트렌디하고 비트감 있는 배경음악(BGM) 추천")
    cuts: List[ClipCut] = Field(description="오프닝 훅부터 결말까지 재배치된 최종 컷 목록")


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
        progress_callback("🤖 Gemini AI 감독관이 영상들을 종합 분석하고 떡상 타임라인을 기획 중입니다...")

    contents = []
    for idx, (path, f_obj) in enumerate(ready_files, start=1):
        contents.append(f"[클립 {idx} 정보: 파일명='{path.name}']")
        contents.append(f_obj)

    prompt = f"""
당신은 인스타그램 릴스와 틱톡에서 조회수 1,000만을 터뜨리는 대한민국 최고의 숏폼 떡상 알고리즘 전문 디렉터(PD)입니다.
제공된 {len(video_files)}개의 영상 클립을 시청자가 1초 만에 스크롤을 멈추고 끝까지 보게 만드는 [알고리즘 떡상형 숏폼/릴스 편집 기획안]으로 완성해 주세요.

[🔥 알고리즘 떡상 핵심 가이드라인]
1. 🚨 [0~2초 오프닝 훅(Hooking) 강제 배치]
   - 절대로 시작부터 순서대로 보여주지 마십시오!
   - 전체 영상 중 가장 시각적 자극이 강하고 군침 도는 하이라이트/완성 장면을 맨 첫 컷(1.5초~2.5초)으로 파격 배치하십시오.
   - 1번째 컷의 자막(caption)은 반드시 **2줄 구조**로 작성하십시오!
     1번째 줄: 강렬한 핵심 키워드 (예: "호두 쏟아부은 미친 고소함!")
     2번째 줄: 호기심을 자극하는 서브 질문 카피 (예: "카페 사장님 비밀 레시피?")
     줄바꿈은 반드시 줄바꿈 문자(\\n)로 구분해 주세요.

2. ⚡ [미친 속도감과 템포 (1.5초 ~ 2.5초)]
   - 지루할 틈이 없도록 한 컷당 길이를 1.5초 ~ 2.5초로 극단적으로 짧고 리듬감 있게 쪼개십시오.
   - 전체 총 영상 길이는 약 {target_duration:.1f}초 내외로 완성해 주십시오.
   - 2번째 컷부터의 과정 자막은 10자 안팎의 직관적이고 임팩트 있는 깔끔한 1줄 카피로 작성하십시오.

3. 🔁 [결말 루프 및 저장/공유 유도]
   - 마지막 컷(완성/포장 장면)에서는 알고리즘 점수를 극대화하기 위해 저장(Save)과 공유(Share)를 이끌어내는 따뜻하고 직관적인 CTA 자막을 적용하십시오.
     (예: "진짜 맛있는 건 나눠 먹어야죠 ✨", "📌 레시피 저장하고 선물해 보세요!")

4. [타임스탬프 정확도]
   - 각 컷마다 해당 원본 영상 파일의 정확한 시작(start)과 종료(end) 시간을 추출하고, 왜 이 컷을 이 순서에 배치했는지 명확한 이유(reason)를 적어주십시오.
"""
    contents.append(prompt)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReelsPlan,
                temperature=0.7,
            ),
        )

        plan_data = json.loads(response.text)
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
