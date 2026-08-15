# Codi AI 구현 및 API 정비 계획

> 기준 문서: `Codi_AI.docx` v1.1 아바타 확장판  
> 작성 기준: 2026-08-14 현재 백엔드 코드와 Git의 마지막 프론트엔드 커밋  
> 목표: 보유 의류, 자연어 일정, 위치 기반 날씨, 신체 프로필을 이용해 코디를 추천하고 2D 아바타 착장을 제공하는 모바일 우선 웹 서비스

## 1. 현재 상태 요약

현재 백엔드에는 Firebase/Gemini 기반으로 다음 기능의 기초 구현이 있다.

- Firebase Authentication 회원가입
- Firestore 사용자 프로필 저장 및 조회
- GCS 의류 이미지 업로드
- Gemini 기반 의류 색상·설명 추출
- 옷장 등록·조회·삭제
- 보유 의류 ID 기반 코디 1개 추천
- Gemini 기반 마네킹 이미지 생성
- 직접 선택한 의류 조합에 대한 점수·코멘트 생성
- 추천 코디 찜 저장·조회·취소

기획서의 완료 기준으로 평가하면 MVP 10개 중 완전 충족한 기능은 없으며, 7개가 부분 구현, 3개가 미구현 상태다.

주의할 현재 작업 상태:

- `frontEnd/codi-ai-frontend` 전체가 작업 트리에서 삭제된 상태다. 복구할지 새로 만들지 먼저 확정해야 한다.
- 현재 DB/AI 스택은 Firestore/Gemini지만 목표 기획은 MySQL/MyBatis/OpenAI다.
- 로그인은 전달된 비밀번호를 검증하지 않으며 인증 토큰도 발급하지 않는다.
- Gemini API 키와 Firebase 서비스 계정이 저장소와 Git 이력에 포함돼 있다.
- Maven Wrapper와 백엔드 테스트가 정상 동작하지 않는다.

## 2. 개발 전 확정할 기술 결정

기획서대로 진행한다는 전제에서 아래 구성을 목표 구조로 사용한다.

| 영역 | 목표 선택 | 비고 |
|---|---|---|
| Frontend | React + Vite | 삭제된 기존 코드를 복구할지 새 UI로 재구축할지 확정 |
| Backend | Java 21 + Spring Boot | REST API 및 외부 연동 |
| 인증 | Spring Security + JWT | 요청의 `userId` 직접 입력 제거 |
| DB | MySQL + MyBatis | Flyway로 스키마 버전 관리 권장 |
| AI | OpenAI API | 구조화 출력과 이미지 편집 사용 |
| 빠른 착장 | 2D Canvas 또는 SVG Composer | AI 호출 없이 빠르게 표시 |
| 고품질 착장 | 이미지 편집 모델 | 사용자가 선택한 코디만 비동기 처리 |
| 날씨 | 기상청 단기예보 API | 위·경도→격자 변환 및 응답 캐시 |
| 이미지 저장 | Object Storage | 원본·마스크·아바타·착장 결과 구분 |
| 배포 | Docker Compose | 프론트·백엔드·MySQL 재현 |

결정이 바뀌어 Firebase/Gemini를 유지한다면 API 계약은 그대로 두고 Repository/AI Adapter 구현만 교체한다. 서비스 계층이 특정 공급자 SDK에 직접 의존하지 않도록 인터페이스를 분리한다.

## 3. 우선순위별 작업 목록

### P0-0. 저장소·보안·실행 환경 정상화

- [ ] 노출된 Gemini 키와 Firebase 서비스 계정 폐기 및 재발급
- [ ] 비밀값을 환경변수 또는 Secret Manager로 이동
- [ ] Git 이력에서 비밀 파일 제거
- [ ] `.gitignore.txt`를 실제 `.gitignore`로 정리
- [ ] `target`, IDE 설정, 인증 JSON을 Git 추적에서 제거
- [ ] Maven Wrapper 실행 권한과 `.mvn/wrapper` 복구
- [ ] 테스트 패키지명 `com.ClothCodi.Ai`를 `com.clothcodi.ai`로 통일
- [ ] 로컬 실행용 `.env.example` 작성
- [ ] 백엔드·프론트·MySQL용 Docker Compose 작성
- [ ] README에 설치·환경변수·실행·테스트 방법 추가
- [ ] 삭제된 프론트엔드를 복구할지 재구축할지 확정

완료 기준:

- 새 개발자가 비밀값을 직접 전달받지 않고 예제 설정을 참고할 수 있다.
- `docker compose up` 또는 문서화된 명령으로 전체 환경이 실행된다.
- `mvn test`와 프론트엔드 lint/build가 통과한다.

### P0-1. 백엔드 공통 기반

- [ ] `/api/v1` 버전 경로 적용
- [ ] Spring Security + JWT 인증 필터 구현
- [ ] 공통 에러 응답과 전역 예외 처리 구현
- [ ] Bean Validation 기반 요청 검증
- [ ] MySQL 연결 및 MyBatis Mapper 구성
- [ ] Flyway 마이그레이션 추가
- [ ] OpenAPI/Swagger 문서화
- [ ] 사용자 소유 리소스 권한 검사 공통화
- [ ] AI·날씨·스토리지 공급자 Adapter 인터페이스 분리
- [ ] 외부 API timeout, retry, circuit breaker 기본 정책 적용

### P0-2. 회원·신체 프로필·취향

- [ ] 이메일 회원가입과 중복 검사
- [ ] 비밀번호 단방향 해시 저장
- [ ] 로그인 시 access/refresh token 발급
- [ ] 로그아웃 및 refresh token 폐기
- [ ] 키·체형·성별 표현·퍼스널 컬러·선호 스타일 저장
- [ ] 프로필 조회·수정·삭제
- [ ] 신체정보 수집 동의 시각 저장
- [ ] 사용자 탈퇴 시 이미지와 파생 데이터 삭제

완료 기준:

- 클라이언트가 `userId`를 보내지 않아도 토큰으로 사용자를 식별한다.
- 키·체형·성별 표현·선호 스타일·퍼스널 컬러를 저장하고 수정할 수 있다.

### P0-3. 가상 옷장과 이미지 전처리

- [ ] 의류 등록·조회·수정·삭제 완성
- [ ] 카테고리, 색상, 계절, 보온성, 격식, 핏, 기장 속성 추가
- [ ] AI 자동 분석 후 사용자가 결과를 확인·수정하는 단계 추가
- [ ] 이미지 MIME type, 크기, 용량 검증
- [ ] 의류 배경 제거 및 투명 마스크 생성
- [ ] 카테고리별 합성 기준점과 bounding box 저장
- [ ] 카테고리·계절·색상 필터와 페이지네이션
- [ ] 원본과 마스크 이미지 삭제 동기화
- [ ] 이미지 접근을 public ACL 대신 서명 URL 또는 제한 URL로 전환

완료 기준:

- 상의·하의·아우터를 등록해 투명 마스크까지 생성할 수 있다.
- AI가 추출한 속성을 사용자가 수정할 수 있다.

### P0-4. 개인 아바타

- [ ] `body_profiles`, `avatars` 데이터 모델 생성
- [ ] 표준 정면 포즈 체형 템플릿 제작
- [ ] 키·체형·성별 표현을 템플릿 파라미터로 변환
- [ ] 상의·하의·아우터 합성 기준점 정의
- [ ] 아바타 생성·조회·수정·재생성 API 구현
- [ ] 같은 프로필로 재생성할 때 포즈와 기준점 일관성 보장
- [ ] 아바타 버전 관리 및 이전 결과 무효화 정책 구현
- [ ] 아바타 설정 화면과 참고용 안내 문구 구현

완료 기준:

- 사용자별 표준 포즈 아바타 1개가 생성된다.
- 키 또는 체형을 수정하면 일관된 방향으로 실루엣이 바뀐다.

### P0-5. 일정/TPO 구조화와 날씨

- [ ] 자연어 일정에서 날짜·시간·장소·활동·격식·분위기 추출
- [ ] AI 구조화 출력 JSON Schema 정의
- [ ] 사용자가 분석된 TPO를 확인·수정하는 UI 구현
- [ ] 장소 검색 또는 위·경도 입력 방식 결정
- [ ] 위·경도를 기상청 격자 좌표로 변환
- [ ] 단기예보에서 기온·강수·풍속·습도 조회
- [ ] 시간대별 체감 조건과 일교차 계산
- [ ] Redis 또는 DB 기반 날씨 캐시 적용
- [ ] API 실패 시 최근 응답 또는 계절 기본 규칙으로 대체

완료 기준:

- 복합 일정이 시간 구간별 TPO로 변환된다.
- 선택 위치와 시간의 날씨 조건이 추천 요청에 포함된다.

### P0-6. AI 코디 추천

- [ ] 날씨·계절·격식 기준 규칙 필터 구현
- [ ] 상의·하의·아우터·신발 조합 생성기 구현
- [ ] 보유 의류 ID만 AI 후보로 전달
- [ ] 추천 점수 가중치 구현
- [ ] 1순위와 대안 포함 1~3개 코디 반환
- [ ] 추천 이유, 날씨 팁, 핏 주의사항, 대체 아이템 반환
- [ ] AI가 반환한 의류 ID의 존재·소유권·카테고리 검증
- [ ] 잘못된 AI 출력에 대한 재시도 및 규칙 기반 대체
- [ ] 추천 요청과 결과 스냅샷 저장
- [ ] 추천 지연시간과 실패율 로깅

초기 점수 가중치:

| 평가 항목 | 가중치 |
|---|---:|
| 날씨 적합성 | 25% |
| TPO 적합성 | 25% |
| 색상 조화 | 20% |
| 체형·핏 조화 | 15% |
| 사용자 선호 | 10% |
| 옷장 활용도 | 5% |

완료 기준:

- 반환되는 모든 핵심 의류 ID가 사용자의 실제 옷장에 존재한다.
- 1~3개 코디에 점수·이유·날씨 팁·핏 안내가 포함된다.
- AI 실패 시에도 기본 추천을 반환할 수 있다.

### P0-7. 빠른 아바타 착장

- [ ] 아바타와 의류 마스크를 레이어로 합성
- [ ] 카테고리별 레이어 순서 적용
- [ ] 기준점 기반 위치·크기·기장 보정
- [ ] 추천 후보 전환 및 전후 비교 UI
- [ ] 합성 결과 캐시
- [ ] “스타일·비율 참고용이며 실제 사이즈를 보장하지 않음” 안내 표시

완료 기준:

- 상의·하의·아우터 조합을 3초 안에 표시한다.
- 후보 코디를 바꿔도 같은 아바타와 포즈가 유지된다.

### P1-1. 찜과 사용자 평가

- [ ] 추천 결과 스냅샷 찜 저장
- [ ] 찜 목록 조회·취소
- [ ] 좋아요·별로예요 평가
- [ ] 부정 평가 사유: 날씨·색상·격식·취향·핏
- [ ] 평가 중복 방지 또는 수정 정책
- [ ] 이후 추천에 선호 점수 반영

### P1-2. 직접 코디 피드백

- [ ] 사용자가 의류 ID를 직접 선택
- [ ] 사용자 프로필·TPO·날씨를 함께 전달
- [ ] 색상·핏·격식·날씨 적합성별 세부 점수 반환
- [ ] 종합 점수·코멘트·개선 아이템 제안
- [ ] 선택 조합의 빠른 아바타 미리보기 제공

### P1-3. 고해상도 AI 렌더

- [ ] 사용자가 고른 코디 1개만 이미지 편집 모델에 전달
- [ ] 기존 아바타의 포즈·체형·의류 색상 유지 조건 적용
- [ ] 비동기 작업 상태 관리
- [ ] 완료 결과 저장 및 캐시
- [ ] 실패·시간 초과 시 빠른 2D 미리보기 자동 반환
- [ ] 사용자별 호출 제한과 비용 로깅

### P1-4. 시연·품질·배포

- [ ] 핵심 사용자 흐름 E2E 테스트
- [ ] 외부 API 실패 테스트
- [ ] AI가 잘못된 의류 ID를 반환하는 경우 테스트
- [ ] 아바타 레이어 순서와 경계 이탈 테스트
- [ ] 추천·착장 성능 지표 수집
- [ ] 모바일 반응형 및 접근성 점검
- [ ] Docker 기반 개발·운영 환경 분리
- [ ] 데모용 시드 사용자·옷장·날씨 시나리오 준비

## 4. 목표 데이터 모델

| 테이블 | 핵심 필드 |
|---|---|
| `users` | `id`, `email`, `password_hash`, `nickname`, `personal_color`, `style_preference`, `created_at`, `deleted_at` |
| `refresh_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `revoked_at` |
| `body_profiles` | `user_id`, `height_cm`, `body_type`, `gender_expression`, `consent_at`, `updated_at` |
| `avatars` | `id`, `user_id`, `template_id`, `parameters_json`, `image_url`, `version`, `created_at` |
| `wardrobe_items` | `id`, `user_id`, `name`, `category`, `color`, `season`, `warmth`, `formality`, `fit`, `length`, `image_url`, `mask_url`, `anchor_json` |
| `recommendations` | `id`, `user_id`, `request_json`, `weather_json`, `status`, `created_at` |
| `recommendation_outfits` | `id`, `recommendation_id`, `rank`, `score`, `reason`, `weather_tip`, `fit_tip` |
| `outfit_items` | `outfit_id`, `wardrobe_item_id`, `layer_order`, `role` |
| `try_on_results` | `id`, `user_id`, `avatar_id`, `outfit_id`, `preview_url`, `render_type`, `status`, `expires_at` |
| `favorites` | `id`, `user_id`, `outfit_id`, `outfit_snapshot_json`, `preview_url`, `created_at` |
| `feedback` | `id`, `user_id`, `recommendation_id`, `outfit_id`, `rating`, `reason_code`, `comment`, `created_at` |
| `weather_cache` | `grid_x`, `grid_y`, `forecast_at`, `payload_json`, `expires_at` |

## 5. API 설계 원칙

- 모든 신규 API의 기본 경로는 `/api/v1`을 사용한다.
- 인증이 필요한 API는 `Authorization: Bearer <access-token>`을 사용한다.
- 요청에서 `userId`를 받지 않고 토큰의 사용자 ID를 사용한다.
- 사용자 소유 리소스는 조회·수정·삭제 전에 항상 소유권을 검증한다.
- AI, 날씨, 이미지 처리의 긴 작업은 상태값과 재시도 정책을 둔다.
- 날짜·시간은 ISO 8601, 서버 저장은 UTC를 사용한다.
- 목록 API는 `page`, `size`, `sort`를 지원한다.
- AI 결과는 서버에서 스키마와 실제 의류 ID를 검증한 뒤 반환한다.

공통 성공 응답 예시:

```json
{
  "data": {},
  "meta": {
    "requestId": "req_123"
  }
}
```

공통 오류 응답 예시:

```json
{
  "code": "WARDROBE_ITEM_NOT_FOUND",
  "message": "의류를 찾을 수 없습니다.",
  "fieldErrors": [],
  "requestId": "req_123"
}
```

## 6. 새로 만들어야 하는 API

### 6.1 인증·사용자

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P0 | POST | `/api/v1/auth/signup` | 회원가입과 기본 사용자 생성 |
| P0 | POST | `/api/v1/auth/login` | 비밀번호 검증 및 토큰 발급 |
| P0 | POST | `/api/v1/auth/refresh` | access token 재발급 |
| P0 | POST | `/api/v1/auth/logout` | refresh token 폐기 |
| P0 | GET | `/api/v1/users/me` | 내 기본 프로필 조회 |
| P0 | PUT | `/api/v1/users/me` | 닉네임·퍼스널 컬러·선호 스타일 수정 |
| P0 | DELETE | `/api/v1/users/me` | 회원 탈퇴 및 파생 데이터 삭제 요청 |

### 6.2 신체 프로필

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P0 | GET | `/api/v1/body-profile` | 내 신체 프로필 조회 |
| P0 | PUT | `/api/v1/body-profile` | 키·체형·성별 표현·동의 정보 저장/수정 |
| P0 | DELETE | `/api/v1/body-profile` | 신체 프로필과 관련 아바타 제거 |

### 6.3 아바타

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P0 | POST | `/api/v1/avatar/generate` | 현재 신체 프로필로 아바타 생성·재생성 |
| P0 | GET | `/api/v1/avatar` | 현재 아바타와 버전 조회 |
| P0 | PUT | `/api/v1/avatar` | 템플릿·표현 옵션 수정 |
| P0 | DELETE | `/api/v1/avatar` | 아바타 및 파생 미리보기 삭제 |

### 6.4 옷장

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P0 | GET | `/api/v1/wardrobe` | 필터·페이지네이션 기반 옷장 조회 |
| P0 | POST | `/api/v1/wardrobe` | 의류 이미지·기본 정보 등록 및 분석 |
| P0 | GET | `/api/v1/wardrobe/{itemId}` | 의류 상세 조회 |
| P0 | PUT | `/api/v1/wardrobe/{itemId}` | AI 분석 결과와 의류 속성 수정 |
| P0 | DELETE | `/api/v1/wardrobe/{itemId}` | 의류 원본·마스크·DB 데이터 삭제 |
| P0 | POST | `/api/v1/wardrobe/{itemId}/reanalyze` | 이미지 속성·마스크 재분석 |

### 6.5 TPO와 날씨

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P0 | POST | `/api/v1/tpo/parse` | 자연어 일정을 구조화된 TPO로 변환 |
| P0 | GET | `/api/v1/weather/forecast` | 위·경도·시간 기준 예보 조회 |

`POST /api/v1/tpo/parse` 요청 예시:

```json
{
  "text": "오후 수업 후 저녁에 해운대에서 데이트",
  "baseDate": "2026-08-14",
  "timezone": "Asia/Seoul"
}
```

응답 핵심 필드:

```json
{
  "segments": [
    {
      "startAt": "2026-08-14T13:00:00+09:00",
      "locationText": "학교",
      "activity": "수업",
      "formality": "CASUAL"
    },
    {
      "startAt": "2026-08-14T19:00:00+09:00",
      "locationText": "해운대",
      "activity": "데이트",
      "formality": "SMART_CASUAL"
    }
  ],
  "needsUserConfirmation": true
}
```

### 6.6 추천

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P0 | POST | `/api/v1/recommendations` | TPO·날씨·옷장·프로필 기반 추천 생성 |
| P0 | GET | `/api/v1/recommendations/{id}` | 추천 결과 재조회 |
| P0 | POST | `/api/v1/recommendations/{id}/regenerate` | 조건을 유지하고 후보 재생성 |

추천 요청 예시:

```json
{
  "tpoSegments": [],
  "location": {
    "latitude": 35.1587,
    "longitude": 129.1604
  },
  "desiredMood": "깔끔하고 편안하게",
  "maxOutfits": 3
}
```

추천 응답의 필수 요소:

- 추천 ID
- 분석된 TPO와 날씨 요약
- 1~3개 코디
- 보유 의류 ID 목록
- 순위와 종합 점수
- 추천 이유
- 날씨 팁
- 체형·핏 주의사항
- 대체 가능한 보유 의류 ID

### 6.7 가상 착장

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P0 | POST | `/api/v1/try-on/preview` | 2D 빠른 아바타 착장 생성 |
| P0 | GET | `/api/v1/try-on/{resultId}` | 착장 결과와 처리 상태 조회 |
| P1 | POST | `/api/v1/try-on/render` | 선택 코디의 고품질 AI 보정 요청 |
| P1 | DELETE | `/api/v1/try-on/{resultId}` | 저장된 착장 결과 삭제 |

### 6.8 찜과 평가

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P1 | GET | `/api/v1/favorites` | 내 찜 목록 조회 |
| P1 | POST | `/api/v1/favorites` | 추천 코디 스냅샷 저장 |
| P1 | DELETE | `/api/v1/favorites/{favoriteId}` | 내 찜 삭제 |
| P1 | POST | `/api/v1/recommendations/{id}/feedback` | 좋아요·별로예요와 사유 저장 |

### 6.9 직접 코디 피드백

| 우선순위 | Method | Endpoint | 용도 |
|---|---|---|---|
| P1 | POST | `/api/v1/outfits/feedback` | 사용자가 직접 고른 의류 조합 평가 |

요청에는 다음 정보가 필요하다.

- `wardrobeItemIds`
- 확인된 TPO
- 위치 또는 날씨 스냅샷
- 원하는 분위기

응답에는 종합 점수 외에 색상·핏·격식·날씨 점수와 개선 제안을 포함한다.

## 7. 기존 API에서 개선해야 하는 항목

| 현재 API | 문제 | 개선 방향 | 목표 API |
|---|---|---|---|
| `POST /api/codi/user/signup` | Firebase 모델에 직접 결합, 응답 계약 불명확 | DTO 검증, 중복 검사, 비밀번호 해시, 표준 응답 | `POST /api/v1/auth/signup` |
| `POST /api/codi/user/login` | 비밀번호 미검증, 토큰 없음 | 실제 인증 후 access/refresh token 발급 | `POST /api/v1/auth/login` |
| `GET /api/codi/closet?userId=` | 사용자 ID 위조 가능 | 토큰 사용자로 조회, 필터·페이지네이션 | `GET /api/v1/wardrobe` |
| `POST /api/codi/closet?userId=` | 속성 부족, 파일 검증 부족 | 토큰 사용자, 분석 상태, 마스크 생성, 사용자 확인 | `POST /api/v1/wardrobe` |
| `DELETE /api/codi/closet/{id}?userId=` | query의 사용자 ID 신뢰 | 토큰 소유권 검사, 파생 파일까지 삭제 | `DELETE /api/v1/wardrobe/{itemId}` |
| 수정 API 없음 | CRUD 미완성 | 의류 속성 수정 API 추가 | `PUT /api/v1/wardrobe/{itemId}` |
| `GET /api/codi/recommend?userId=&tpo=` | GET으로 긴 AI 작업 실행, 날씨 없음, 코디 1개 | POST body, 구조화 TPO·날씨·1~3개 후보·이유·검증 | `POST /api/v1/recommendations` |
| `POST /api/codi/feedback?userId=` | 의류 정보만 평가, TPO·날씨·프로필 누락 | 평가 문맥과 항목별 점수 추가 | `POST /api/v1/outfits/feedback` |
| `GET /api/codi/favorites/{userId}` | 다른 사용자 ID 조회 가능 | 토큰 사용자 기준 조회 | `GET /api/v1/favorites` |
| `POST /api/codi/favorites` | body의 `userId` 신뢰, 임의 스냅샷 저장 가능 | 추천/코디 ID 검증 후 서버가 스냅샷 생성 | `POST /api/v1/favorites` |
| `DELETE /api/codi/favorites/{outfitId}` | 소유권 검사 없음, 찜과 outfit ID 혼용 | favorite ID와 소유권 검사 | `DELETE /api/v1/favorites/{favoriteId}` |
| 프로필 API 없음 | 조회·수정 불가 | 사용자·신체 프로필 API 분리 | `/api/v1/users/me`, `/api/v1/body-profile` |

## 8. 폐기하거나 분리해야 하는 현재 구현

- query parameter의 `userId`는 전부 제거한다.
- `CodiController` 한 곳에 회원·옷장·추천·찜을 모은 구조를 도메인별 Controller로 분리한다.
- `User` 모델을 API 요청/응답 DTO와 DB 모델로 동시에 사용하지 않는다.
- 추천할 때마다 고해상도 이미지를 생성하는 흐름을 제거한다.
- `Outfit.isFavorite` 플래그 대신 별도 `favorites` 테이블을 사용한다.
- 프롬프트 문구만으로 “현재 날씨 반영”을 주장하지 않는다.
- AI가 반환한 ID를 그대로 신뢰하지 않고 서버에서 소유권과 존재 여부를 검증한다.
- public ACL 이미지 공개를 기본값으로 사용하지 않는다.
- Firebase/Gemini를 제거한다면 관련 Config, SDK 의존성, 키 파일, Firestore 모델 annotation을 정리한다.

## 9. 권장 백엔드 패키지 구조

```text
com.clothcodi.ai
├── common
│   ├── auth
│   ├── error
│   ├── response
│   └── config
├── user
├── bodyprofile
├── avatar
├── wardrobe
├── tpo
├── weather
├── recommendation
├── tryon
├── favorite
├── feedback
└── integration
    ├── ai
    ├── weather
    └── storage
```

각 도메인은 가능하면 `controller`, `service`, `repository/mapper`, `dto`, `model`을 분리한다.

## 10. 핵심 테스트 목록

### 인증·권한

- [ ] 잘못된 비밀번호로 로그인할 수 없다.
- [ ] 토큰 없이 보호 API를 호출할 수 없다.
- [ ] 다른 사용자의 의류·아바타·찜을 조회·수정·삭제할 수 없다.

### 옷장·이미지

- [ ] 지원하지 않는 파일과 용량 초과 파일을 거부한다.
- [ ] 의류 삭제 시 원본·마스크·DB 데이터가 함께 삭제된다.
- [ ] AI 분석 실패 후 사용자가 속성을 직접 입력할 수 있다.

### 아바타·착장

- [ ] 같은 프로필로 재생성할 때 포즈와 기준점이 유지된다.
- [ ] 상의·하의·아우터 레이어 순서가 올바르다.
- [ ] 체형 변경 시 실루엣과 기장 표현이 예상 방향으로 달라진다.
- [ ] 빠른 미리보기가 3초 안에 표시된다.

### 날씨·추천

- [ ] 비가 오는 시간대에 우천 팁 또는 적절한 신발 대안이 포함된다.
- [ ] 저녁 기온이 낮으면 아우터 후보가 포함된다.
- [ ] 서로 다른 복합 TPO를 시간 구간별로 구분한다.
- [ ] AI가 사용자 옷장에 없는 의류 ID를 반환해도 서버가 차단한다.
- [ ] AI 또는 날씨 API 실패 시 기본 결과로 대체한다.

## 11. MVP 완료 판정

아래 흐름이 실제 데이터로 끊김 없이 동작해야 P0 완료로 판단한다.

1. 사용자가 회원가입하고 로그인한다.
2. 키·체형·성별 표현·선호 스타일·퍼스널 컬러를 저장한다.
3. 표준 포즈 아바타를 생성한다.
4. 상의·하의·아우터를 등록하고 AI 속성과 마스크를 확인한다.
5. 복합 일정을 입력하고 분석된 TPO를 수정·확정한다.
6. 위치와 시간대별 날씨를 조회한다.
7. 실제 보유 의류로 구성된 1~3개 추천과 이유를 받는다.
8. 같은 아바타에서 후보별 빠른 착장 이미지를 비교한다.
9. 추천을 찜하거나 평가한다.
10. 외부 AI 또는 날씨 API가 실패해도 데모 흐름이 중단되지 않는다.

## 12. 첫 개발 착수 순서

1. 프론트엔드 삭제 상태와 목표 기술 스택 확정
2. 비밀값 폐기·재발급 및 저장소 정리
3. MySQL/MyBatis/Flyway와 공통 API 응답 기반 구성
4. Spring Security JWT 회원·프로필 API 완성
5. 옷장 CRUD와 확장 속성·마스크 처리
6. 아바타 템플릿과 빠른 2D 합성 프로토타입
7. TPO 구조화와 기상청 API 연결
8. 규칙 필터 및 구조화된 AI 추천
9. 찜·평가·직접 조합 피드백
10. 고해상도 보정·캐시·Docker·E2E 테스트

P0 기능이 완료되기 전에는 고해상도 렌더나 추천 학습 고도화보다 로그인→프로필→옷장→날씨/TPO→추천→빠른 착장의 기본 흐름을 우선한다.
