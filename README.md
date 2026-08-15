# 👕 Codi AI: 옷장 기반 AI 스타일링 플랫폼

## 💡 프로젝트 소개 (Introduction)

Codi AI는 대학생들의 **'오늘 뭐 입지?' 고민과 '나 이렇게 입어도 괜찮나?' 불안감**을 해결하기 위해 기획된 **AI 스타일링 플랫폼**입니다.

기존 국내 주요 패션 앱들은 '새 옷 판매'나 '트렌드 노출'에 집중하고 있습니다. 정작 사용자의 **보유한 옷(내 옷장)**을 기반으로 **TPO(시간/장소/상황)**를 계획하고 코디 조합을 평가해 주는 'AI 스타일리스트'는 부재합니다.

| 차별점 | 기존 패션 앱 (무신사, 에이블리 등) | Codi AI (본 프로젝트) |
| :--- | :--- | :--- |
| **코디 대상** | 판매 중인 '새 옷' | **사용자가 보유한 옷 (내 옷장)** |
| **AI 활용 범위** | 상품 추천 (제한적) | **코디 계획, 생성, 평가** |
| **복합 TPO 플래닝** | X | **◎ (핵심 기능)** |

---

## 🚀 주요 기능 (Key Features)

Codi AI는 Java Spring Boot와 Google Gemini API를 결합하여 다음의 핵심 기능을 제공합니다.

### 1. 👚 옷장 아이템 등록 및 AI 라벨링
* **기능**: 사용자가 자신의 옷 이미지를 등록하면, AI(Gemini Vision)가 이미지를 분석하여 **색상(Color)** 및 **상세 설명(Content)**을 자동으로 라벨링하여 저장합니다.
* **API 경로**: `POST /api/codi/closet`

### 2. 🤖 AI 코디 자동 추천 (핵심 기능 1)
* **기능**: AI가 **내 옷장 DB**, **날씨 API**, **퍼스널 컬러** 정보를 복합 분석하여 TPO에 맞는 하루 전체의 코디 조합을 생성합니다. 사용자는 "낮엔 학교, 저녁엔 소개팅"처럼 **복합적인 하루 일정(TPO)**을 텍스트로 입력할 수 있습니다.
* **결과**: AI가 추천한 코디 조합을 기반으로 **가상의 마네킹 착장 이미지**를 생성하여 시각화된 결과로 제공합니다.
* **API 경로**: `GET /api/codi/recommend?userId=&tpo=`

### 3. 💬 사용자 코디 AI 피드백 (핵심 기능 2)
* **기능**: 사용자가 직접 조합한 아이템 정보, TPO 문맥, 퍼스널 컬러를 AI가 종합적으로 분석하여 평가합니다.
* **결과**: 코디의 적합도 **점수**(`aiScore`), 구체적인 **평가 코멘트**(`aiComment`), 그리고 **개선 제안**(`aiSuggestion`)을 제공합니다.
* **API 경로**: `POST /api/codi/feedback?userId=`

### 4. ❤️ 코디 북마크 및 관리
* **기능**: 'AI 코디 자동 추천' 결과 중 마음에 드는 코디를 선택하여 찜 목록에 보관하고 조회합니다.
* **API 경로**: `POST /api/codi/favorites`, `GET /api/codi/favorites/{userId}`

---

## ⚙️ 기술 스택 (Tech Stack)

| 구분 | 기술 | 역할 |
| :--- | :--- | :--- |
| **Backend** | **Spring Boot (Java)** | REST API 서버, AI 및 날씨 연동 로직 |
| **AI/ML** | **Google Gemini** | 텍스트 분석 및 이미지 생성 |
| **Database** | **Firebase Firestore** | 사용자, 옷장, 코디, 피드백 데이터 저장 |
| **Storage** | **Google Cloud Storage (GCS)** | 이미지 파일 저장 (옷 이미지, AI 생성 이미지) |
| **외부 API** | 공공데이터포털 날씨 API | 날씨 정보 기반 TPO 분석에 활용 |
| **Frontend** | React (Vite) | UI 렌더링, API 호출, 코디 결과 표시 |

---

## 💾 데이터베이스 구조 (DB Structure - Firestore Collections)

| 컬렉션 | 주요 역할 | 주요 필드 |
| :--- | :--- | :--- |
| **`users`** | 사용자 인증 및 상세 프로필 | `email`, `nickname`, **`personalColor`**, **`bodyShape`**, `height`, `weight` |
| **`closetItems`** | 사용자 보유 옷 정보 | `category`, `imgUrl`, **`color`**, **`content`** (옷 상세 설명) |
| **`outfits`** | 코디 조합 및 찜 목록 | `coordiItems` (아이템 ID 목록), **`generatedImageUrl`**, `isFavorite` |
| **`aiFeedbacks`** | AI 코디 평가 결과 | **`aiScore`**, **`aiComment`**, **`aiSuggestion`**, `outfitId` |

---

## 💡 기대 효과 (Expected Outcomes)

* **코디 고민 해결**: AI가 TPO, 퍼스널 컬러, 날씨를 종합 분석하여 최적의 코디 계획을 제안함으로써, 매일의 고민을 효과적으로 줄여줍니다.
* **스타일링 능력 향상**: AI가 구체적인 피드백을 제공함으로써 사용자는 스스로 스타일링을 발전시킬 수 있습니다.
* **합리적인 소비**: ‘내 옷장'에 등록된 보유 옷의 활용률을 극대화하여, 불필요한 의류 구매를 줄이고 합리적인 소비를 할 수 있도록 돕습니다.

---

## 👥 팀 (Team)

| 이름 |
| :--- |
| 최국진 팀장 백엔드|
| 최정원 팀원 문서 및 PPT 발표|
| 이규빈 팀원 백엔드|
| 김홍인 팀원 프론트 엔드|


```java

 * AI 코디 관련 API 엔드포인트를 처리하는 컨트롤러.
 * 모든 기능은 @RequestParam String userId를 통해 실제 사용자 ID를 받도록 수정되었습니다.
 
@RestController
@RequestMapping("/api/codi")
@RequiredArgsConstructor
public class CodiController {

    private final ClosetService closetService;
    private final AiService aiService;
    private final UserService userService;
    private final FavoriteService favoriteService;

    // --- 회원가입/로그인 기능 ---

    /** 기능 9: 회원가입 (POST /api/codi/user/signup) */
    @PostMapping("/user/signup")
    public User signup(@RequestBody User user) {
        return userService.signupUser(user);
    }

    /** 기능 10: 로그인 (POST /api/codi/user/login) */
    @PostMapping("/user/login")
    public User login(@RequestBody User loginRequest) {
        return userService.loginUser(loginRequest.getEmail(), loginRequest.getPassword());
    }


    // --- 옷장/코디 기능 (userId 강제 주입 제거 완료) ---

    /** 기능 1: 옷장에 옷 추가 (AI 라벨링) */
    @PostMapping("/closet")
    public ClosetItem addClosetItem(
            @RequestParam String userId,
            @RequestParam("category") String category,
            @RequestParam("name") String name,
            @RequestParam("image") MultipartFile imageFile
    ) {
        return closetService.addClosetItem(userId, category, null, name, imageFile);
    }

    /** * 기능 4: 내 옷장 목록 조회 */
    @GetMapping("/closet")
    public List<ClosetItem> getMyCloset(@RequestParam String userId) {
        return closetService.getClosetItems(userId);
    }

    /** 기능 6: 옷장 아이템 삭제 */
    @DeleteMapping("/closet/{closetItemId}")
    public ClosetItem deleteClosetItem(@PathVariable String closetItemId, @RequestParam String userId) {
        return closetService.deleteItem(userId, closetItemId);
    }


    /** 기능 2: 옷장 기반 코디 추천 (마네킹 이미지 생성) */
    @GetMapping("/recommend")
    public Outfit recommendOutfit(
            @RequestParam String userId, // 👈 필수 파라미터로 추가됨
            @RequestParam(value = "tpo", defaultValue = "데일리 룩") String targetTpo
    ) {
        return aiService.recommendOutfit(userId, targetTpo);
    }

    /** 기능 3: 사용자 선택 조합 피드백 */
    @PostMapping("/feedback")
    public AiFeedback getFeedback(@RequestBody List<String> itemIds, @RequestParam String userId) {
        return aiService.getFeedbackForOutfit(userId, itemIds);
    }

    // --- 찜 목록 기능 ---

    /** 기능 7: 추천 코디 찜하기 */
    @PostMapping("/favorites")
    public Outfit addFavorite(@RequestBody Outfit outfit) {
        return favoriteService.addFavorite(outfit);
    }

    /** 기능 8: 찜한 코디 목록 조회 */
    @GetMapping("/favorites/{userId}")
    public List<Outfit> getFavorites(@PathVariable String userId) {
        return favoriteService.getFavorites(userId);
    }

    /** 기능 9: 찜한 코디 취소 */
    @DeleteMapping("/favorites/{outfitId}")
    public ResponseEntity<Void> removeFavorite(@PathVariable String outfitId) {
        favoriteService.removeFavorite(outfitId);
        return ResponseEntity.noContent().build();
    }
}
```

1. 🤖 AiService.java (AI 코디 추천 및 이미지 생성)
핵심: Gemini 텍스트 모델을 이용해 코디 아이템을 추천받고, 이 정보를 기반으로 Gemini 이미지 모델을 호출하여 마네킹 착장 이미지를 생성하는 로직입니다.

```java
// 📂 AiService.java: 코디 추천 및 이미지 생성 (recommendOutfit)

public Outfit recommendOutfit(String userId, String targetTpo) {
    // 1. 옷장 및 사용자 프로필 데이터 획득
    List<ClosetItem> items = closetService.getClosetItems(userId);
    User userProfile = userService.getUserProfile(userId).orElseThrow(...);

    // 2. AI 텍스트 모델 호출 -> 코디 아이템 ID 목록 획득
    String prompt = codiHelper.buildRecommendationPrompt(items, targetTpo, userProfile);
    GenerateContentResponse response = geminiClient.models.generateContent(geminiModelName, prompt, null);
    CodiHelper.RecommendationResponse recommendation = codiHelper.parseRecommendationResponse(response.text());

    // 3. 이미지 생성 프롬프트 생성 (AI 추천 결과를 바탕으로)
    String imagePrompt = createCombinedImagePrompt(recommendedItems, recommendation.getTpoText(), userProfile);

    // 4. AI 이미지 모델 호출 -> 마네킹 이미지 바이트 획득
    byte[] imageBytes = generateImageBytes(imagePrompt);

    // 5. GCS에 저장 후 Outfit 객체에 URL 포함하여 반환
    String generatedImageUrl = uploadGeneratedImage(imageBytes);
    
    Outfit outfit = new Outfit();
    outfit.setUserId(userId);
    outfit.setGeneratedImageUrl(generatedImageUrl); 
    // ...
    return outfit;
}

// 📂 AiService.java: 사용자 선택 조합 피드백 (getFeedbackForOutfit)

public AiFeedback getFeedbackForOutfit(String userId, List<String> itemIds) {
    // ... Outfit 객체 생성 및 Firestore 저장 (조합 기록) ...
    
    // 1. AI 피드백 요청
    String prompt = codiHelper.buildFeedbackPrompt(selectedItems);
    GenerateContentResponse response = geminiClient.models.generateContent(geminiModelName, prompt, null);
    CodiHelper.AiFeedbackResponse feedbackResponse = codiHelper.parseFeedbackResponse(response.text());

    // 2. AiFeedback 객체 생성 및 Firestore 저장
    AiFeedback feedback = new AiFeedback();
    feedback.setAiScore(feedbackResponse.getAiScore());
    feedback.setAiComment(feedbackResponse.getAiComment());
    // ...
    db.collection("aiFeedbacks").document(feedback.getId()).set(feedback).get();

    return feedback;
}
```

2. 🛍️ ClosetService.java (옷장 관리 및 AI 라벨링)
핵심: 이미지 업로드 시 GCS 저장과 Gemini Vision 모델을 이용한 자동 라벨링을 통합하여 처리합니다.
```java
// 📂 ClosetService.java: 옷장에 옷 추가 (AI 라벨링)

public ClosetItem addClosetItem(String userId, String category, String color, String name, MultipartFile imageFile) {
    try {
        // 1. GCS에 파일 업로드 및 Public URL 획득
        String storagePath = userId + "/" + UUID.randomUUID() + extension;
        // ... GCS 업로드 및 권한 설정 ...
        String imgUrl = String.format("https://storage.googleapis.com/%s/%s", bucket.getName(), storagePath);

        // 2. AI 이미지 분석 및 라벨링 요청 (Gemini Vision)
        CodiHelper.ImageLabelingResponse aiLabels = analyzeImage(imageFile.getBytes(), imageFile.getContentType());

        // 3. ClosetItem 객체에 AI 결과를 반영하여 Firestore 저장
        ClosetItem item = new ClosetItem();
        item.setUserId(userId);
        item.setColor(aiLabels.getDominantColor()); // AI 결과 반영
        item.setContent(aiLabels.getDescription()); // AI 결과 반영
        item.setImgUrl(imgUrl);
        // ... 기타 필드 설정 및 Firestore 저장 ...

        return item;
    } catch (Exception e) { 
        // ... 예외 처리 ...
    }
}
```
3. 📝 CodiHelper.java (AI 통신 보조 및 프롬프트 관리)
핵심: AI 모델에게 원하는 역할과 JSON 응답 형식을 명확히 지시하는 프롬프트 생성 로직을 담당합니다.

```java
// 📂 CodiHelper.java: TPO 반영 코디 추천 프롬프트 생성 (buildRecommendationPrompt)

public String buildRecommendationPrompt(List<ClosetItem> items, String targetTpo, User userProfile) {
    // 사용자 상세 프로필(체형, 퍼스널 컬러) 및 아이템 목록 구성
    String userDetails = String.format("사용자 정보: [성별: %s, 체형: %s, 퍼스널 컬러: %s].", ...);
    String itemList = items.stream().map(item -> String.format("- ID: %s, 카테고리: %s", ...)).collect(Collectors.joining("\n"));

    return "다음은 사용자의 옷장 정보입니다:\n" + userDetails + itemList +
           "\n\n이 아이템들 중에서 서로 잘 어울리는 코디 조합 1개를 JSON 형식으로 만들어주세요.\n" +
           "**사용자의 체형과 퍼스널 컬러에 잘 맞아야 합니다.** 요청 상황: [" + targetTpo + "]\n" +
           "응답은 반드시 다음 JSON 형식을 따라야 합니다:\n" +
           "{\"recommendedItemIds\": [\"id-abc\", \"id-xyz\"], \"tpoText\": \"...\"}";
}

// 📂 CodiHelper.java: JSON 응답 파싱 (parseRecommendationResponse)

public RecommendationResponse parseRecommendationResponse(String aiResponse) {
    try {
        String jsonResponse = aiResponse.replaceAll("(?s)```json\\s*|\\s*```", "").trim();
        return objectMapper.readValue(jsonResponse, RecommendationResponse.class);
    } catch (Exception e) {
        // ... 파싱 실패 처리 ...
    }
}
```
4. 🔒 UserService.java (사용자 인증 및 프로필 관리)
핵심: Firebase Authentication을 이용한 회원가입 및 UID 기반의 Firestore 프로필 연동 로직입니다.

```java
// 📂 UserService.java: 사용자 회원가입 (signupUser)

public User signupUser(User user) {
    try {
        // 1. Firebase Authentication에 계정 생성 -> Firebase UID 획득
        UserRecord.CreateRequest request = new UserRecord.CreateRequest()
                .setEmail(user.getEmail())
                .setPassword(user.getPassword());
        UserRecord userRecord = firebaseAuth.createUser(request);
        String firebaseUid = userRecord.getUid();

        // 2. Firestore에 상세 프로필 저장 (Firebase UID를 문서 ID로 사용)
        user.setId(firebaseUid);
        user.setPassword(null); 
        db.collection("users").document(firebaseUid).set(user).get();

        return user;
    } catch (Exception e) { 
        // ... 예외 처리 ... 
    }
}
```

5. ❤️ FavoriteService.java (찜 목록 관리)
핵심: 추천 코디를 Firestore의 outfits 컬렉션에 isFavorite=true로 설정하여 저장하는 로직입니다.
```java
// 📂 FavoriteService.java: 코디 찜하기 (addFavorite)

public Outfit addFavorite(Outfit outfit) {
    try {
        // 1. 새 문서 참조를 얻고 ID 할당
        DocumentReference docRef = db.collection("outfits").document();
        outfit.setId(docRef.getId());

        // 2. isFavorite 플래그를 true로 설정하고 문서 저장
        outfit.setIsFavorite(true);
        docRef.set(outfit).get();

        return outfit;
    } catch (Exception e) {
        // ... 예외 처리 ...
    }
}

// 📂 FavoriteService.java: 찜한 코디 조회 (getFavorites)

public List<Outfit> getFavorites(String userId) {
    // userId로 필터링하고 isFavorite이 true인 문서만 조회
    return db.collection("outfits")
             .whereEqualTo("userId", userId)
             .whereEqualTo("isFavorite", true)
             // ... Firestore 조회 및 매핑 로직 ...
             .collect(Collectors.toList());
}
```
