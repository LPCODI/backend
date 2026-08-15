# Codi AI Backend v2

Java 21, Spring Boot, Spring Security/JWT, MyBatis, Flyway 기반 REST API입니다.

## 실행

```bash
cd Backend
./mvnw spring-boot:run
```

`.env`에 Neon과 Firebase 설정이 있으면 해당 서비스로 자동 연결됩니다. Firebase 없이 로컬 파일 저장으로만 실행하려면 `STORAGE_PROVIDER=local ./mvnw spring-boot:run`을 사용합니다.

- Swagger UI: http://localhost:8080/swagger-ui.html
- OpenAPI JSON: http://localhost:8080/v3/api-docs

Swagger 사용 순서:

1. `POST /api/v1/auth/signup`
2. `POST /api/v1/auth/login`
3. 응답의 `accessToken`을 복사
4. 우측 상단 `Authorize`에 토큰 입력
5. 프로필, 옷장, 추천 API 호출

## MySQL과 Docker로 실행

프로젝트 루트에서 실행합니다.

```bash
docker compose up --build
```

## Neon PostgreSQL로 실행

Neon 대시보드의 `Connect` 화면에서 Direct connection 정보를 확인한 다음, `.env.example`을 `.env`로 복사하고 Neon 값을 입력합니다. `.env`는 Git에서 제외됩니다.

```bash
cp .env.example .env
# .env의 DB_URL, DB_USERNAME, DB_PASSWORD를 Neon 값으로 수정
./mvnw spring-boot:run
```

Neon이 복사해 준 `postgresql://USER:PASSWORD@HOST/neondb?...` 문자열을 그대로 `DB_URL`에 넣지 않고, 위처럼 `jdbc:postgresql://HOST/neondb?sslmode=require`로 변환합니다. 애플리케이션이 시작될 때 Flyway가 `db/migration/V1__init.sql`을 실행해 필요한 테이블을 자동으로 생성합니다.

## Firebase Storage

Firebase Admin SDK 서비스 계정 JSON을 `Backend/secrets/firebase-service-account.json`에 두고 `.env`에 다음 값을 설정합니다. 서비스 계정 파일과 `.env`는 Git에서 제외됩니다.

```properties
STORAGE_PROVIDER=firebase
FIREBASE_STORAGE_BUCKET=YOUR_PROJECT_ID.firebasestorage.app
GOOGLE_APPLICATION_CREDENTIALS=./secrets/firebase-service-account.json
```

업로드 파일은 `users/{userId}/{folder}/...`에 저장됩니다. API는 Firebase 다운로드 URL을 DB에 저장하고, 의류·착장 결과·아바타 삭제 및 회원 탈퇴 시 관련 객체도 정리합니다. OpenAI 이미지 편집 요청은 저장된 Firebase 객체를 백엔드가 다시 읽어 multipart 파일로 전달합니다.

## 선택 외부 연동

- `KMA_SERVICE_KEY`: 기상청 단기예보 키. 없거나 호출 실패 시 계절 기반 기본 날씨를 반환합니다.
- `OPENAI_API_KEY`: 선택 코디 고품질 이미지 렌더. 없거나 호출 실패 시 2D SVG 착장으로 자동 대체합니다.
- `OPENAI_IMAGE_MODEL`: 기본값 `gpt-image-2`.

환경변수 예시는 `.env.example`을 참고하세요. 운영에서는 반드시 `JWT_SECRET`과 DB 비밀번호를 변경해야 합니다.

## 검증

```bash
./mvnw clean test
./mvnw clean package
```
