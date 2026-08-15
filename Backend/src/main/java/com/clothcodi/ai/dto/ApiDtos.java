package com.clothcodi.ai.dto;

import jakarta.validation.constraints.*;
import jakarta.validation.Valid;
import java.time.*;
import java.util.List;
import java.util.Map;

public final class ApiDtos {
    private ApiDtos() {}

    public record SignupRequest(@Email @NotBlank String email, @NotBlank @Size(min=8,max=72) String password,
                                @NotBlank @Size(max=60) String nickname) {}
    public record LoginRequest(@Email @NotBlank String email, @NotBlank String password) {}
    public record RefreshRequest(@NotBlank String refreshToken) {}
    public record LogoutRequest(@NotBlank String refreshToken) {}
    public record TokenResponse(String tokenType, String accessToken, long accessExpiresIn,
                                String refreshToken, long refreshExpiresIn) {}
    public record UserResponse(String id, String email, String nickname, String personalColor,
                               String stylePreference, Instant createdAt) {}
    public record UserUpdateRequest(@NotBlank @Size(max=60) String nickname,
                                    @Size(max=40) String personalColor, @Size(max=100) String stylePreference) {}
    public record BodyProfileRequest(@Min(100) @Max(230) int heightCm, @NotBlank String bodyType,
                                     @NotBlank String genderExpression, @AssertTrue boolean consent) {}
    public record BodyProfileResponse(String userId, int heightCm, String bodyType,
                                      String genderExpression, Instant consentAt, Instant updatedAt) {}
    public record AvatarUpdateRequest(@NotBlank String templateId, Map<String,Object> options) {}
    public record AvatarResponse(String id, String templateId, Map<String,Object> parameters,
                                 String imageUrl, int version, Instant createdAt) {}
    public record WardrobeUpdateRequest(@NotBlank String name, @NotBlank String category, String color,
                                        String season, @Min(1) @Max(5) Integer warmth, String formality,
                                        String fit, String length, String description) {}
    public record WardrobeItemResponse(String id, String name, String category, String color, String season,
                                       Integer warmth, String formality, String fit, String length,
                                       String description, String imageUrl, String maskUrl,
                                       Map<String,Object> anchor, String analysisStatus, Instant createdAt) {}
    public record TpoParseRequest(@NotBlank String text, LocalDate baseDate, String timezone) {}
    public record TpoSegment(OffsetDateTime startAt, String locationText, String activity, String formality) {}
    public record TpoParseResponse(List<TpoSegment> segments, boolean needsUserConfirmation) {}
    public record Location(@DecimalMin("-90") @DecimalMax("90") double latitude,
                           @DecimalMin("-180") @DecimalMax("180") double longitude) {}
    public record WeatherResponse(double latitude, double longitude, OffsetDateTime forecastAt,
                                  int temperatureC, int feelsLikeC, int humidityPercent,
                                  double precipitationMm, double windSpeedMs, int dailyRangeC,
                                  String condition, String source, boolean fallback) {}
    public record RecommendationRequest(@NotEmpty List<TpoSegment> tpoSegments, @NotNull @Valid Location location,
                                        String desiredMood, @Min(1) @Max(3) Integer maxOutfits) {}
    public record OutfitResponse(String id, int rank, int score, List<String> wardrobeItemIds,
                                 String reason, String weatherTip, String fitTip, List<String> alternativeItemIds) {}
    public record RecommendationResponse(String id, List<TpoSegment> tpoSegments, WeatherResponse weather,
                                         String status, List<OutfitResponse> outfits, Instant createdAt) {}
    public record TryOnRequest(@NotBlank String outfitId) {}
    public record TryOnResponse(String id, String avatarId, String outfitId, String previewUrl,
                                String renderType, String status, Instant expiresAt) {}
    public record FavoriteRequest(@NotBlank String outfitId, String previewUrl) {}
    public record FavoriteResponse(String id, String outfitId, OutfitResponse outfit,
                                   String previewUrl, Instant createdAt) {}
    public record RecommendationFeedbackRequest(@NotBlank @Pattern(regexp="LIKE|DISLIKE") String rating,
                                                String reasonCode, @Size(max=500) String comment,
                                                String outfitId) {}
    public record OutfitFeedbackRequest(@Size(min=2) List<String> wardrobeItemIds,
                                        List<TpoSegment> tpoSegments, Location location,
                                        WeatherResponse weather, String desiredMood) {}
    public record OutfitFeedbackResponse(String id, int totalScore, int colorScore, int fitScore,
                                         int formalityScore, int weatherScore, String comment,
                                         List<String> suggestions, TryOnResponse preview) {}
}
