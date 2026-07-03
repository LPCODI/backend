# MVP Stub Policy

실제 AI, 문서 파싱, 음성, 영상 처리는 MVP 단계에서 교체 가능한 서비스 인터페이스 뒤에 둔다.
API 라우터와 DB 저장 로직은 `app.services.interfaces`의 Protocol에만 의존하고,
Whisper, LLM, YOLO Pose, MediaPipe, OpenCV, FFmpeg, python-pptx 같은 구체 구현은 adapter로 분리한다.

## 기본 정책

| 항목 | 정책 |
| --- | --- |
| 기본 stub 정책 | `DETERMINISTIC_MVP` |
| 기본 구현 | `DeterministicMvpAnalysisStub` |
| 결과 성격 | 외부 네트워크, GPU, 파일 변환 없이 재현 가능한 placeholder |
| 표시 방식 | 모든 stub 결과는 provider, version, warnings를 포함 |
| 교체 기준 | 실제 서비스 adapter가 같은 Protocol을 만족하면 라우터/DB 코드는 변경하지 않음 |

## Stub 대상

| 기능 | 인터페이스 | 실제 교체 대상 |
| --- | --- | --- |
| 발표 자료 파싱 | `DocumentParserService` | python-pptx, PyMuPDF, python-docx, LibreOffice Headless |
| 슬라이드 분석 | `SlideAnalysisService` | LLM API 또는 로컬 NLP |
| 대본 생성 | `ScriptGenerationService` | LLM API |
| 음성 분석 | `AudioAnalysisService` | FFmpeg, Whisper API 또는 Faster-Whisper |
| 자세 분석 | `PoseAnalysisService` | YOLO Pose, OpenCV |
| 시선 분석 | `GazeAnalysisService` | MediaPipe, OpenCV |
| 에이전트 평가 | `AgentEvaluationService` | LLM API |
| 예상 질문 생성 | `QaGenerationService` | LLM API |
| 종합 리포트 생성 | `ReportGenerationService` | LLM API, PDF renderer |

## 구현 원칙

- stub는 성공한 실제 분석처럼 오인되지 않도록 `warnings`에 MVP stub임을 남긴다.
- stub는 테스트와 API 개발을 막지 않는 최소 구조만 반환한다.
- 외부 서비스 adapter는 입력/출력 타입을 유지한 채 별도 모듈로 추가한다.
- 발표 조건은 계속 `UNIVERSITY_PROJECT_FOR_PROFESSOR` 고정값을 사용한다.
