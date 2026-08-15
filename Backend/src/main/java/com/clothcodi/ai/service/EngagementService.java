package com.clothcodi.ai.service;

import com.clothcodi.ai.common.AppException;
import com.clothcodi.ai.dto.ApiDtos.*;
import com.clothcodi.ai.model.DbModels.*;
import com.clothcodi.ai.repository.CodiMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.*;
import java.util.*;

@Service
public class EngagementService {
    private final CodiMapper db;private final RecommendationService recommendations;private final TryOnService tryOn;private final ObjectMapper json;
    public EngagementService(CodiMapper db,RecommendationService recommendations,TryOnService tryOn,ObjectMapper json){this.db=db;this.recommendations=recommendations;this.tryOn=tryOn;this.json=json;}
    @Transactional public FavoriteResponse favorite(String userId,FavoriteRequest r){Outfit o=recommendations.ownedOutfit(userId,r.outfitId());if(db.findFavoriteByOutfit(userId,r.outfitId())!=null)throw new AppException("FAVORITE_ALREADY_EXISTS","이미 찜한 코디입니다.",HttpStatus.CONFLICT);OutfitResponse snapshot=recommendations.outfitResponse(userId,o);Favorite f=new Favorite();f.setId(UUID.randomUUID().toString());f.setUserId(userId);f.setOutfitId(o.getId());f.setOutfitSnapshotJson(write(snapshot));f.setPreviewUrl(r.previewUrl());f.setCreatedAt(LocalDateTime.now());db.insertFavorite(f);return favoriteResponse(f);}
    public List<FavoriteResponse> favorites(String userId){return db.listFavorites(userId).stream().map(this::favoriteResponse).toList();}
    public void deleteFavorite(String userId,String id){if(db.deleteFavorite(userId,id)==0)throw AppException.notFound("FAVORITE_NOT_FOUND","찜을 찾을 수 없습니다.");}
    public void recommendationFeedback(String userId,String recommendationId,RecommendationFeedbackRequest r){recommendations.get(userId,recommendationId);if(r.outfitId()!=null)recommendations.ownedOutfit(userId,r.outfitId());Feedback f=new Feedback();f.setId(UUID.randomUUID().toString());f.setUserId(userId);f.setRecommendationId(recommendationId);f.setOutfitId(r.outfitId());f.setRating(r.rating());f.setReasonCode(r.reasonCode());f.setComment(r.comment());f.setDetailsJson("{}");f.setCreatedAt(LocalDateTime.now());db.insertFeedback(f);}
    @Transactional public OutfitFeedbackResponse outfitFeedback(String userId,OutfitFeedbackRequest r){if(r.wardrobeItemIds()==null||r.wardrobeItemIds().size()<2)throw AppException.badRequest("OUTFIT_ITEMS_REQUIRED","의류를 2개 이상 선택해 주세요.");List<WardrobeItem> items=r.wardrobeItemIds().stream().map(id->{WardrobeItem w=db.findWardrobe(userId,id);if(w==null)throw AppException.forbidden();return w;}).toList();int color=items.stream().map(WardrobeItem::getColor).distinct().count()<=3?88:72;int fit=82;int formality=r.tpoSegments()==null||r.tpoSegments().isEmpty()?78:86;int weather=r.weather()==null?75:weatherScore(items,r.weather());int total=(color+fit+formality+weather)/4;Outfit o=recommendations.createDirectOutfit(userId,r.wardrobeItemIds());TryOnResponse preview=null;try{preview=tryOn.preview(userId,o.getId());}catch(AppException ignored){}Feedback f=new Feedback();f.setId(UUID.randomUUID().toString());f.setUserId(userId);f.setOutfitId(o.getId());f.setRating("AI_SCORE");f.setDetailsJson(write(Map.of("total",total,"color",color,"fit",fit,"formality",formality,"weather",weather)));f.setComment("색상과 격식의 균형을 유지한 조합입니다.");f.setCreatedAt(LocalDateTime.now());db.insertFeedback(f);return new OutfitFeedbackResponse(f.getId(),total,color,fit,formality,weather,f.getComment(),List.of("신발 또는 아우터로 포인트를 조절해 보세요.","실제 기온과 착용감을 마지막으로 확인하세요."),preview);}
    private int weatherScore(List<WardrobeItem> items,WeatherResponse w){double avg=items.stream().map(WardrobeItem::getWarmth).filter(Objects::nonNull).mapToInt(Integer::intValue).average().orElse(3);double target=w.feelsLikeC()<10?5:w.feelsLikeC()<18?4:w.feelsLikeC()<25?3:1;return Math.max(50,100-(int)Math.abs(avg-target)*13);}
    private FavoriteResponse favoriteResponse(Favorite f){try{return new FavoriteResponse(f.getId(),f.getOutfitId(),json.readValue(f.getOutfitSnapshotJson(),OutfitResponse.class),f.getPreviewUrl(),f.getCreatedAt().toInstant(ZoneOffset.UTC));}catch(Exception e){throw new IllegalStateException(e);}}
    private String write(Object o){try{return json.writeValueAsString(o);}catch(Exception e){throw new IllegalStateException(e);}}
}

