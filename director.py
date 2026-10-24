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
    line1_highlight: str = Field(description="4~8글자 이내의 아이 행동/도전 과제 노란색 강조 키워드 (예: '정상까지 갈 거야!')")
    line2_sub: str = Field(description="호기심/응원을 자극하는 흰색 질문 카피 (예: '쪼꼬미의 위대한 등산 도전')")


class ShortCut(BaseModel):
    cut_index: int = Field(description="컷 순번 (1부터 시작하는 순번)", ge=1)
    source_file: str = Field(description="해당 컷이 포함된 원본 영상 파일명 (예: 'GX010405.MP4')")
    start_time: str = Field(description="구간 시작 타임스탬프 (예: '00:02.00')")
    end_time: str = Field(description="구간 종료 타임스탬프 (예: '00:04.00')")
    duration: float = Field(description="해당 컷의 길이(초 단위, 1.2~2.5초 권장)")
    caption: str = Field(description="자막 문구 (1번 컷은 2줄 카피, 중간 컷은 감정과 대사를 담은 생생한 구어체/대화체/의성어 문구. '함께 오르기', '거대한 바위' 등 기계적 명사 설명 절대 금지!)")
    zoom_in: bool = Field(description="표정/손동작/발걸음 강조를 위한 줌인 트랜지션 여부 (True/False)", default=False)
    action_role: str = Field(description="해당 컷의 연출상 역할 및 감정 포인트 (예: '씩씩한 출발 선언', '거대 바위 앞 귀여운 감탄')")


class ShortDirectorPlan(BaseModel):
    title: str = Field(description="조회수를 부르는 매력적인 스토리텔링 숏폼 제목")
    concept: str = Field(description="다정한 시선과 생생한 대사가 살아있는 감성·위트 스토리텔링 연출 콘셉트")
    bgm_vibe: str = Field(description="영상 분위기에 어울리는 따뜻하고 경쾌한 배경음악(BGM) 추천")
    opening_hook: OpeningHook = Field(description="첫 1~2초 오프닝 훅 (1줄 노란색 도전 키워드 + 2줄 흰색 호기심 질문)")
    ending_cta: str = Field(description="자연스러운 공감과 응원을 유도하는 따뜻한 엔딩 문구")
    cuts: List[ShortCut] = Field(description="오프닝 훅부터 결말까지 감정 흐름에 맞게 재배치된 최종 컷 목록")


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
    user_prompt: Optional[str] = None,
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

    intent_section = ""
    if user_prompt and user_prompt.strip():
        intent_section = f"""
[🎯 사용자가 요청한 핵심 주제 및 연출 의도]
- 사용자 지정 의도: "{user_prompt.strip()}"
- 위 사용자의 기획 의도와 주제를 최우선으로 반영하되, 아래의 [자막 연출 절대 원칙]을 철저히 준수하여 완성하십시오.
"""

    prompt = f"""
당신은 대한민국 최정상급의 감각적인 [스토리텔링 숏폼 총괄 디렉터]입니다.
영상 상황을 단순 기계적으로 설명하거나 나열하는 교과서식 영상은 시청자가 1초 만에 이탈합니다.
시청 지속률(Retention Rate)과 바이럴 공감을 극대화하기 위해 제공된 {len(video_files)}개의 영상 클립을 분석하고,
'엄마/아빠의 다정한 시선' 또는 '아이의 깜찍한 독백 시점'이 살아 숨 쉬는 감성·위트 스토리텔링 숏폼 편집 기획안을 완성해 주십시오.
{intent_section}
[🎬 숏폼 총괄 디렉터 자막 연출 절대 원칙]

1. 🚫 금지 패턴 (Negative Prompt - 위반 시 엄격히 실패 처리):
   - ❌ 교과서식 명사형 설명 절대 금지: "손 잡고 걷기", "함께 오르기", "거대한 바위", "자연의 신비", "새로운 길", "바스락 발자국", "정상 도착" 등 상황을 제3자처럼 단순 서술하는 단어 조합은 절대 생성하지 마십시오.
   - ❌ 뻔하고 진부한 다큐/힐링 멘트 금지: "오늘의 행복 기억해요", "자연과 함께하는 소중한 시간" 등 클리셰 문구 금지.

2. 🎭 화자 페르소나 부여 (다정한 구어체 & 대화체):
   - 영상을 기록하는 '엄마/아빠의 다정한 시선' 또는 '아이의 당찬 독백/대화 시점' 중 하나로 일관되게 통일하십시오.
   - 입에 착착 감기는 생생한 구어체(~하자!, ~했지?, ~해볼까?), 감탄사(우와!, 앗!), 의성어/의태어(바스락바스락, 아장아장, 성큼성큼), 호기심 질문을 가득 담으십시오.

3. 🚨 첫 1~2초 후킹 (Opening Hook):
   - 1번 컷은 전체 영상 중 가장 인상적이거나 호기심을 유발하는 장면을 첫 컷(1.2초~2.5초)으로 과감히 배치하십시오.
   - opening_hook:
     * line1_highlight: 아이의 당찬 행동이나 도전 과제 (4~8글자, 노란색 강조)
       (예: "정상까지 갈 거야!", "혼자서도 씩씩하게!", "오늘 산 정복한다!")
     * line2_sub: 시청자의 궁금증과 응원을 유발하는 흰색 서브 카피
       (예: "쪼꼬미의 위대한 등산 도전", "과연 끝까지 갈 수 있을까?", "출발 3분 만에 위기?")
   - 1번 컷의 caption은 반드시 이 두 문장을 줄바꿈(\\n)으로 연결하여 작성하십시오.
     (예: "정상까지 갈 거야!\\n쪼꼬미의 위대한 등산 도전")

4. 💬 본문 컷 자막 (Process) - 감정과 생생한 대사:
   - 동작을 묘사하지 말고, 그 순간의 **감정과 캐릭터의 살아있는 대사**를 넣으십시오.
   - 컷당 1줄, 5~14글자 내외의 리드미컬하고 직관적인 대화체로 작성하십시오.

5. 🛑 [Few-Shot 예시 강제: 나쁜 자막 vs 좋은 자막 대비표]
   반드시 다음 좋은 자막의 톤앤매너를 100% 모방하고, 나쁜 자막 스타일은 철저히 배제하십시오:
   --------------------------------------------------------------------------------
   [영상 상황]       | ❌ 나쁜 자막 (절대 금지: 기계적 묘사)  | ⭕ 좋은 자막 (필수 적용: 감성·위트 대화체)
   --------------------------------------------------------------------------------
   - 출발/오르막    | "함께 오르기", "발걸음 옮기기"         | "엄마 손 꼭 잡고 출발!" / "씩씩하게 첫 발자국 쿵!"
   - 커다란 바위    | "거대한 바위", "자연의 신비"           | "우와! 집채만 한 바위다!" / "요 거대한 돌은 뭐지?"
   - 낙엽/흙길      | "바스락 발자국", "낙엽 밟기"           | "바스락바스락 신나는 발걸음" / "낙엽 밟는 소리 최고!"
   - 가파른 코스    | "새로운 길", "험난한 오르막"           | "여긴 좀 가파른데? 조심조심!" / "끙차! 한 걸음 더!"
   - 힘들거나 쉴 때 | "잠시 휴식", "물 마시기"               | "다리 아파도 포기는 없다!" / "꿀맛 같은 물 한 모금!"
   - 정상/성공      | "정상 도착", "정복 완료"               | "드디어 해냈다! 만세!" / "내가 산을 정복했다!"
   - 마무리/엔딩    | "오늘의 행복 기억해요"                 | "우리 다음 산은 어디 갈까?" / "다음 주말에 또 오자!"
   --------------------------------------------------------------------------------

6. 🔁 엔딩 CTA (Ending Hook) - 자연스러운 소장/응원 유도:
   - 억지 팔로우 강요는 배제하고, 시청자가 미소 지으며 응원 댓글을 달고 저장(Save)하고 싶어지는 따뜻한 문구를 작성하십시오.
     (예: "우리 꼬마 등산가 응원해 주실 거죠? ✨", "주말에 아이와 꼭 가보세요 📌")
   - 마지막 컷의 caption에도 이 감성을 자연스럽게 녹여내십시오.

7. ⏱️ 컷 길이 및 속도감:
   - 총 러닝타임은 {target_duration:.1f}초 내외로 타이트하게 구성하십시오.
   - 늘어지는 구간은 과감히 쳐내고, 컷당 길이를 1.2초 ~ 2.5초 내외로 배치하여 숏폼 특유의 경쾌한 리듬감을 만드십시오.
   - 디테일한 표정, 손동작, 발걸음, 포인트 샷에는 "zoom_in": true를 적용하십시오.
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
        # 1번 컷 오프닝 훅 줄바꿈 포맷팅 보장
        if plan_data.get("cuts") and plan_data.get("opening_hook"):
            oh = plan_data["opening_hook"]
            h1 = oh.get("line1_highlight", "").strip()
            h2 = oh.get("line2_sub", "").strip()
            if h1 and h2:
                plan_data["cuts"][0]["caption"] = f"{h1}\n{h2}"

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
def generate_sns_package(timeline_data: dict, user_prompt: Optional[str] = None) -> dict:
    """타임라인 기획안을 바탕으로 인스타그램/유튜브 쇼츠 업로드용 제목, 본문, 해시태그 패키지를 생성합니다."""
    client = get_gemini_client()

    title = timeline_data.get("title", "")
    concept = timeline_data.get("concept", "")
    cuts_summary = "\n".join([f"- {c.get('caption')}" for c in timeline_data.get("cuts", [])])
    intent_line = f"\n[사용자 기획 의도]: {user_prompt.strip()}" if (user_prompt and user_prompt.strip()) else ""

    prompt = f"""
당신은 인스타그램 릴스와 유튜브 쇼츠 마케팅 전문 카피라이터입니다.
아래의 릴스 영상 기획안을 바탕으로 시청자의 폭발적인 참여(좋아요, 저장, 댓글, 공유)를 이끌어낼 [SNS 업로드 패키지]를 작성해 주세요.

[영상 제목]: {title}
[영상 콘셉트]: {concept}{intent_line}
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
