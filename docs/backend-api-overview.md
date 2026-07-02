# 백엔드 API 개요

## 문서 목적

이 문서는 AI Speech 백엔드가 어떤 역할을 담당하는지 협업자가 빠르게 파악할 수 있도록 정리한 요약 문서입니다.

상세 API 요청/응답 예시는 [AISpeechBackend.pdf](../AISpeechBackend.pdf)를 기준으로 확인합니다.

## 백엔드 역할

백엔드는 React Native 앱과 AI 분석 모듈, PostgreSQL 데이터베이스, 파일 저장소 사이에서 전체 발표 준비 흐름을 관리합니다.

주요 책임은 다음과 같습니다.

- 사용자 인증 및 권한 검증
- 발표 프로젝트 생성 및 상태 관리
- 발표 자료 업로드 및 파싱 요청
- 슬라이드 분석 결과 저장
- 발표 시간 배분 및 대본 생성
- 리허설 음성·영상 업로드 관리
- 음성, 자세, 시선 분석 작업 실행
- AI 에이전트 평가 결과 저장
- Q&A 예상 질문 및 답변 평가 관리
- 종합 리포트 생성
- 비동기 작업 상태와 진행률 제공

## 고정 발표 조건

이 프로젝트는 발표 상황을 다음과 같이 고정합니다.

| 항목 | 조건 |
| --- | --- |
| 발표 대상 | 담당 교수님 |
| 발표 목적 | 대학 프로젝트 발표 및 평가 |
| 발표 상황 | 강의실 또는 프로젝트 발표 자리 |
| 발표 말투 | 공식적이고 이해하기 쉬운 설명체 |
| 평가 관점 | 교수 관점, 학생 관점, 최종 판단 관점 |

따라서 발표 대상, 발표 목적, 발표 상황, 말투를 따로 입력받는 API는 제공하지 않습니다.

## 주요 도메인 구조

```text
User
└─ PresentationProject
   ├─ PresentationFile
   ├─ Slide
   │  ├─ SlideAnalysis
   │  ├─ SlideTiming
   │  └─ SlideScript
   ├─ Rehearsal
   │  ├─ AudioAnalysis
   │  ├─ PoseAnalysis
   │  ├─ GazeAnalysis
   │  └─ RehearsalSlideResult
   ├─ AgentEvaluation
   │  ├─ PROFESSOR
   │  ├─ STUDENT
   │  └─ FINAL_JUDGE
   ├─ QaSession
   │  ├─ QaQuestion
   │  └─ QaAnswer
   └─ FinalReport
```

## API 그룹

### 인증 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/auth/signup` | 회원가입 |
| POST | `/auth/login` | 로그인 |
| POST | `/auth/refresh` | Access Token 재발급 |
| POST | `/auth/logout` | 로그아웃 |
| GET | `/users/me` | 로그인 사용자 조회 |
| PATCH | `/users/me` | 사용자 정보 수정 |

### 발표 프로젝트 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/presentations` | 발표 프로젝트 생성 |
| GET | `/presentations` | 발표 프로젝트 목록 |
| GET | `/presentations/{presentationId}` | 발표 프로젝트 상세 |
| PATCH | `/presentations/{presentationId}` | 발표 조건 수정 |
| DELETE | `/presentations/{presentationId}` | 발표 프로젝트 삭제 |
| POST | `/presentations/{presentationId}/duplicate` | 프로젝트 복제 |

### 발표 자료 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/presentations/{presentationId}/files` | 발표 자료 업로드 |
| GET | `/presentations/{presentationId}/files` | 업로드 파일 조회 |
| DELETE | `/presentations/{presentationId}/files/{fileId}` | 파일 삭제 |
| POST | `/presentations/{presentationId}/parse` | 자료 파싱 시작 |
| GET | `/presentations/{presentationId}/parse-result` | 파싱 결과 조회 |

### 슬라이드 분석·시간 배분·대본 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/presentations/{presentationId}/analysis` | 발표 자료 분석 시작 |
| GET | `/presentations/{presentationId}/analysis` | 전체 분석 결과 |
| POST | `/presentations/{presentationId}/timings/generate` | 시간 자동 배분 |
| GET | `/presentations/{presentationId}/timings` | 시간 배분 조회 |
| POST | `/presentations/{presentationId}/scripts/generate` | 교수 발표용 전체 대본 생성 |
| GET | `/presentations/{presentationId}/scripts` | 전체 대본 조회 |

### 리허설·미디어 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/presentations/{presentationId}/rehearsals` | 리허설 생성 |
| GET | `/presentations/{presentationId}/rehearsals` | 리허설 목록 |
| GET | `/rehearsals/{rehearsalId}` | 리허설 상세 |
| POST | `/rehearsals/{rehearsalId}/media/upload-url` | Presigned URL 생성 |
| POST | `/rehearsals/{rehearsalId}/audio` | 음성 직접 업로드 |
| POST | `/rehearsals/{rehearsalId}/video` | 영상 직접 업로드 |
| POST | `/rehearsals/{rehearsalId}/analyze` | 리허설 분석 시작 |

### 음성·자세·시선 분석 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/rehearsals/{rehearsalId}/audio-analysis` | 음성 분석 시작 |
| GET | `/rehearsals/{rehearsalId}/audio-analysis` | 음성 분석 결과 |
| GET | `/rehearsals/{rehearsalId}/transcript` | STT 결과 |
| GET | `/rehearsals/{rehearsalId}/filler-words` | 추임새 분석 |
| GET | `/rehearsals/{rehearsalId}/speech-speed` | 말하기 속도 |
| POST | `/rehearsals/{rehearsalId}/pose-analysis` | 자세 분석 시작 |
| GET | `/rehearsals/{rehearsalId}/pose-analysis` | 자세 분석 결과 |
| POST | `/rehearsals/{rehearsalId}/gaze-analysis` | 시선 분석 시작 |
| GET | `/rehearsals/{rehearsalId}/gaze-analysis` | 시선 분석 결과 |

### 에이전트 평가·Q&A·리포트 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/rehearsals/{rehearsalId}/evaluations` | 교수·학생 평가 시작 |
| GET | `/rehearsals/{rehearsalId}/evaluations` | 전체 평가 조회 |
| GET | `/rehearsals/{rehearsalId}/evaluations/professor` | 교수 평가 |
| GET | `/rehearsals/{rehearsalId}/evaluations/student` | 학생 평가 |
| POST | `/rehearsals/{rehearsalId}/evaluations/final` | 최종 판단 실행 |
| POST | `/rehearsals/{rehearsalId}/qa-sessions` | Q&A 세션 생성 |
| POST | `/qa-sessions/{qaSessionId}/questions/generate` | 예상 질문 생성 |
| POST | `/qa-sessions/{qaSessionId}/questions/{questionId}/answers` | 답변 제출 |
| POST | `/qa-sessions/{qaSessionId}/answers/{answerId}/evaluate` | 답변 평가 |
| POST | `/rehearsals/{rehearsalId}/reports` | 종합 리포트 생성 |
| GET | `/rehearsals/{rehearsalId}/reports/latest` | 최신 리포트 조회 |
| GET | `/presentations/{presentationId}/comparison` | 이전 발표 비교 |

### 작업·시스템 API

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/jobs/{jobId}` | 작업 상태 조회 |
| DELETE | `/jobs/{jobId}` | 작업 취소 |
| GET | `/jobs/{jobId}/events` | SSE 진행률 |
| GET | `/health` | 서버 상태 |
| GET | `/ready` | DB, Redis, Queue 준비 상태 |
| GET | `/version` | API 버전 |

## 상태값

### 발표 프로젝트

```text
DRAFT
FILE_UPLOADED
PARSING
PARSED
ANALYZING
ANALYZED
SCRIPT_GENERATING
SCRIPT_READY
REHEARSAL_READY
COMPLETED
FAILED
```

### 비동기 작업

```text
PENDING
QUEUED
PROCESSING
COMPLETED
FAILED
CANCELLED
```

### 리허설

```text
CREATED
UPLOADING
UPLOADED
ANALYZING
ANALYZED
EVALUATING
COMPLETED
FAILED
```

## 대표 API 예시

### 발표 프로젝트 생성

```http
POST /api/v1/presentations
```

```json
{
  "title": "AI 발표 준비 도우미 프로젝트 발표",
  "totalDurationSeconds": 600,
  "qaDurationSeconds": 180
}
```

백엔드는 실제 발표 가능 시간을 아래처럼 계산합니다.

```text
presentationDurationSeconds = totalDurationSeconds - qaDurationSeconds
```

응답 예시:

```json
{
  "success": true,
  "data": {
    "presentationId": 101,
    "title": "AI 발표 준비 도우미 프로젝트 발표",
    "totalDurationSeconds": 600,
    "qaDurationSeconds": 180,
    "presentationDurationSeconds": 420,
    "presentationContext": "UNIVERSITY_PROJECT_FOR_PROFESSOR",
    "status": "DRAFT"
  }
}
```

## 비동기 처리 원칙

자료 파싱, 발표 자료 분석, 대본 생성, 음성 분석, 영상 분석, 에이전트 평가, 리포트 생성은 시간이 오래 걸릴 수 있으므로 비동기 작업으로 처리합니다.

API는 즉시 `jobId`를 반환하고, 클라이언트는 작업 상태 API 또는 SSE를 통해 진행률을 확인합니다.

```json
{
  "success": true,
  "data": {
    "jobId": "job_analysis_81ac21",
    "status": "QUEUED"
  }
}
```

## 구현 시 주의사항

- 인증이 필요한 API는 `Authorization: Bearer {accessToken}` 헤더를 사용합니다.
- Access Token 권장 만료 시간은 30분입니다.
- Refresh Token 권장 만료 시간은 14일입니다.
- 발표 자료 업로드 허용 형식은 PPT, PPTX, PDF, DOCX입니다.
- 업로드 권장 제한은 최대 100MB, 최대 100슬라이드입니다.
- 파일은 DB에 직접 저장하지 않고 파일 저장소 경로와 메타데이터만 DB에 저장합니다.
- 사용자별 발표 프로젝트 접근 권한을 반드시 검증합니다.
