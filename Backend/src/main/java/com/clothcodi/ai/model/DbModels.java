package com.clothcodi.ai.model;

import lombok.Data;
import java.time.LocalDateTime;

public final class DbModels {
    private DbModels() {}
    @Data public static class User { String id,email,passwordHash,nickname,personalColor,stylePreference; LocalDateTime createdAt,deletedAt; }
    @Data public static class BodyProfile { String userId,bodyType,genderExpression; int heightCm; LocalDateTime consentAt,updatedAt; }
    @Data public static class Avatar { String id,userId,templateId,parametersJson,imageUrl; int version; LocalDateTime createdAt; }
    @Data public static class WardrobeItem { String id,userId,name,category,color,season,formality,fit,itemLength,description,imageUrl,maskUrl,anchorJson,analysisStatus; Integer warmth; LocalDateTime createdAt,updatedAt; }
    @Data public static class Recommendation { String id,userId,requestJson,weatherJson,status; LocalDateTime createdAt; }
    @Data public static class Outfit { String id,recommendationId,reason,weatherTip,fitTip,alternativesJson; int outfitRank,score; }
    @Data public static class OutfitItem { String outfitId,wardrobeItemId,role; int layerOrder; }
    @Data public static class TryOn { String id,userId,avatarId,outfitId,previewUrl,renderType,status; LocalDateTime expiresAt,createdAt; }
    @Data public static class Favorite { String id,userId,outfitId,outfitSnapshotJson,previewUrl; LocalDateTime createdAt; }
    @Data public static class Feedback { String id,userId,recommendationId,outfitId,rating,reasonCode,comment,detailsJson; LocalDateTime createdAt; }
    @Data public static class WeatherCache { String cacheKey,payloadJson; int gridX,gridY; LocalDateTime forecastAt,expiresAt; }
}
