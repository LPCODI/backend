# AI Speech Backend

AI 기반 교수 발표 준비 도우미의 백엔드 API 서버입니다.

사용자가 발표 자료를 업로드하고 전체 발표 시간과 질의응답 시간을 입력하면, 백엔드는 발표 자료 분석, 슬라이드별 시간 배분, 교수 발표용 대본 생성, 리허설 음성·영상 분석, AI 에이전트 평가, 예상 질문 생성, 종합 리포트 생성을 처리합니다.

발표 상황은 **대학 프로젝트를 교수님 앞에서 발표하는 경우**로 고정합니다. 따라서 발표 대상, 발표 목적, 말투, 발표 상황을 사용자가 별도로 선택하지 않으며, 교수님 발표에 맞춘 흐름으로 API를 구성합니다.

## 문서

| 문서 | 설명 |
| --- | --- |
| [백엔드 API 개요](docs/backend-api-overview.md) | 기술 스택, 처리 흐름, 주요 API 그룹 |
| [원본 API 기술 명세서](AISpeechBackend.pdf) | 상세 API 명세 PDF |

## 기술 스택

| 구분 | 기술 |
| --- | --- |
| Backend Framework | FastAPI |
| Language | Python 3.12 |
| ORM | SQLAlchemy 2.x |
| Validation | Pydantic v2 |
| Database | PostgreSQL |
| Migration | Alembic |
| Cache / Queue Broker | Redis |
| 비동기 작업 | Celery 또는 RQ |
| 파일 저장소 | AWS S3 또는 MinIO |
| 음성 변환 | OpenAI Whisper API 또는 Faster-Whisper |
| 영상 분석 | YOLO Pose, MediaPipe, OpenCV |
| AI 대본·평가 | LLM API |
| 인증 | JWT Access Token + Refresh Token |
| API 문서 | Swagger UI / OpenAPI |
| 진행률 통신 | SSE 또는 WebSocket |
| 배포 | Docker, Nginx, AWS EC2 또는 홈서버 |

## API 기본 주소

```text
개발 환경: http://localhost:8000/api/v1
Swagger: http://localhost:8000/docs
```

## 전체 처리 흐름

```text
회원 로그인
-> 발표 프로젝트 생성
-> 발표 자료 업로드
-> 발표 자료 파싱
-> 슬라이드 분석
-> 발표 가능 시간 계산
-> 슬라이드별 시간 배분
-> 교수 발표용 대본 생성
-> 리허설 생성
-> 음성·영상 업로드
-> 음성·자세·시선 분석
-> 교수·학생 에이전트 평가
-> 예상 질문 생성
-> 사용자 답변 분석
-> 최종 판단 에이전트 평가
-> 종합 리포트 생성
-> 이전 리허설과 비교
```

## 주요 기능

- JWT 기반 회원가입, 로그인, 토큰 재발급
- 발표 프로젝트 생성 및 관리
- PPT, PPTX, PDF, DOCX 발표 자료 업로드
- 발표 자료 파싱 및 슬라이드 구조 분석
- 슬라이드별 핵심 메시지와 예상 질문 생성
- 전체 발표 시간과 Q&A 시간을 기준으로 발표 가능 시간 계산
- 슬라이드별 발표 시간 자동 배분
- 교수님 발표용 대본 생성 및 수정
- 리허설 음성·영상 업로드
- STT, 추임새, 말하기 속도, 누락 내용 분석
- 자세, 시선, 반복 행동 분석
- 교수 에이전트, 학생 에이전트, 최종 판단 에이전트 평가
- 실전 질의응답 세션과 답변 평가
- 종합 리포트 생성 및 이전 발표와 비교
- Redis Queue 기반 비동기 작업 처리

## 공통 응답 형식

### 성공

```json
{
  "success": true,
  "data": {},
  "message": "요청이 정상적으로 처리되었습니다.",
  "timestamp": "2026-06-30T18:30:00+09:00"
}
```

### 실패

```json
{
  "success": false,
  "error": {
    "code": "PRESENTATION_NOT_FOUND",
    "message": "발표 프로젝트를 찾을 수 없습니다.",
    "details": null
  },
  "timestamp": "2026-06-30T18:30:00+09:00"
}
```

## 개발 원칙

- OpenAI API Key는 클라이언트 앱에 노출하지 않습니다.
- 모든 AI API 호출은 FastAPI 서버를 통해 처리합니다.
- 발표 자료, 음성, 영상 파일은 사용자 권한을 확인한 뒤 접근합니다.
- 오래 걸리는 분석 작업은 비동기 작업으로 처리합니다.
- 작업 진행률은 작업 상태 API 또는 SSE/WebSocket으로 제공합니다.
- DB 구조 변경 시 SQLAlchemy 모델과 Alembic 마이그레이션을 함께 관리합니다.
