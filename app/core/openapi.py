"""Swagger and OpenAPI metadata configuration."""

from collections.abc import Mapping
from typing import Any

from app.core.config import Settings, get_settings

API_VERSION = "0.1.0"

OPENAPI_DESCRIPTION = """
AI 기반 교수 발표 준비 도우미 백엔드 API입니다.

발표 상황은 대학 프로젝트를 교수님 앞에서 발표하는 경우로 고정합니다.
클라이언트는 발표 대상, 발표 목적, 발표 상황, 말투를 별도로 전달하지 않습니다.

모든 업무 API는 `/api/v1` prefix 아래에 노출합니다.
""".strip()

OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": "auth", "description": "회원가입, 로그인, 토큰 재발급, 로그아웃"},
    {"name": "users", "description": "로그인 사용자 조회와 정보 수정"},
    {"name": "presentations", "description": "발표 프로젝트 생성, 조회, 수정, 삭제"},
    {"name": "files", "description": "발표 자료 업로드, 조회, 삭제"},
    {"name": "slides", "description": "슬라이드 조회, 수정, 순서 변경, 제외 처리"},
    {"name": "analysis", "description": "발표 자료 분석과 슬라이드 분석 결과"},
    {"name": "timings", "description": "발표 가능 시간 계산과 슬라이드별 시간 배분"},
    {"name": "scripts", "description": "교수 발표용 대본 생성, 조회, 수정"},
    {"name": "rehearsals", "description": "리허설 생성, 조회, 업로드 완료, 분석 시작"},
    {"name": "media", "description": "리허설 음성 및 영상 업로드 관리"},
    {"name": "audio-analysis", "description": "STT, 추임새, 속도, 누락 내용 분석"},
    {"name": "video-analysis", "description": "자세, 시선, 반복 행동 분석"},
    {"name": "evaluations", "description": "교수, 학생, 최종 판단 에이전트 평가"},
    {"name": "qa", "description": "예상 질문 생성과 답변 평가"},
    {"name": "reports", "description": "종합 리포트 생성, 조회, 다운로드, 비교"},
    {"name": "jobs", "description": "비동기 작업 상태 조회, 취소, 진행률 스트림"},
    {"name": "system", "description": "헬스체크, 준비 상태, 버전 정보"},
]


def build_openapi_metadata(settings: Settings | None = None) -> Mapping[str, Any]:
    """Return FastAPI constructor metadata for Swagger UI and OpenAPI schema."""

    app_settings = settings or get_settings()
    return {
        "title": app_settings.app_name,
        "summary": "AI 기반 교수 발표 준비 도우미 API",
        "description": OPENAPI_DESCRIPTION,
        "version": API_VERSION,
        "openapi_tags": OPENAPI_TAGS,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
    }
