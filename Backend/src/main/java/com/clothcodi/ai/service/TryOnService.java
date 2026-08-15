package com.clothcodi.ai.service;

import com.clothcodi.ai.common.AppException;
import com.clothcodi.ai.dto.ApiDtos.TryOnResponse;
import com.clothcodi.ai.model.DbModels.*;
import com.clothcodi.ai.repository.CodiMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.task.TaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.*;
import java.util.*;

@Service
public class TryOnService {
    private final CodiMapper db;private final RecommendationService recommendations;private final ImageStorageService storage;private final ObjectMapper json;private final TaskExecutor tasks;private final OpenAiImageService openAi;
    public TryOnService(CodiMapper db,RecommendationService recommendations,ImageStorageService storage,ObjectMapper json,TaskExecutor tasks,OpenAiImageService openAi){this.db=db;this.recommendations=recommendations;this.storage=storage;this.json=json;this.tasks=tasks;this.openAi=openAi;}
    @Transactional public TryOnResponse preview(String userId,String outfitId){return create(userId,outfitId,"PREVIEW",false);}
    @Transactional public TryOnResponse render(String userId,String outfitId){TryOnResponse response=create(userId,outfitId,"AI_FALLBACK",true);tasks.execute(()->finishRender(userId,response.id()));return response;}
    private TryOnResponse create(String userId,String outfitId,String type,boolean async){recommendations.ownedOutfit(userId,outfitId);Avatar avatar=db.findAvatar(userId);if(avatar==null)throw AppException.badRequest("AVATAR_REQUIRED","먼저 아바타를 생성해 주세요.");TryOn t=new TryOn();t.setId(UUID.randomUUID().toString());t.setUserId(userId);t.setAvatarId(avatar.getId());t.setOutfitId(outfitId);t.setRenderType(type);t.setStatus(async?"PROCESSING":"COMPLETED");t.setExpiresAt(LocalDateTime.now().plusDays(30));t.setCreatedAt(LocalDateTime.now());if(!async)t.setPreviewUrl(build(userId,avatar,outfitId,"빠른 2D 착장"));db.insertTryOn(t);return response(t);}
    private void finishRender(String userId,String id){TryOn t=db.findTryOn(userId,id);if(t==null)return;try{Avatar avatar=db.findAvatar(userId);List<WardrobeItem> items=db.listOutfitItems(t.getOutfitId()).stream().map(i->db.findWardrobe(userId,i.getWardrobeItemId())).filter(Objects::nonNull).toList();BodyProfile body=db.findBody(userId);String bodyText=body==null?"standard proportion":body.getHeightCm()+"cm "+body.getBodyType()+" "+body.getGenderExpression();Optional<String> ai=openAi.render(userId,items,bodyText);if(ai.isPresent()){t.setPreviewUrl(ai.get());t.setRenderType("AI");t.setStatus("COMPLETED");}else{t.setPreviewUrl(build(userId,avatar,t.getOutfitId(),"AI 사용 불가 · 2D 자동 대체"));t.setStatus("COMPLETED_FALLBACK");}}catch(Exception e){t.setStatus("FAILED");}db.updateTryOn(t);}
    public TryOnResponse get(String userId,String id){TryOn t=db.findTryOn(userId,id);if(t==null)throw AppException.notFound("TRY_ON_NOT_FOUND","착장 결과를 찾을 수 없습니다.");return response(t);}
    @Transactional public void delete(String userId,String id){TryOn t=db.findTryOn(userId,id);if(t==null)throw AppException.notFound("TRY_ON_NOT_FOUND","착장 결과를 찾을 수 없습니다.");db.deleteTryOn(userId,id);storage.deleteUrl(t.getPreviewUrl());}
    private String build(String userId,Avatar avatar,String outfitId,String label){StringBuilder svg=new StringBuilder("<svg xmlns='http://www.w3.org/2000/svg' width='400' height='700' viewBox='0 0 400 700'><rect width='400' height='700' fill='#f7f5f2'/><image href='").append(escape(avatar.getImageUrl())).append("' x='0' y='0' width='400' height='700'/>");for(OutfitItem oi:db.listOutfitItems(outfitId)){WardrobeItem w=db.findWardrobe(userId,oi.getWardrobeItemId());if(w==null)continue;Map<String,Object>a=read(w.getAnchorJson());double width=num(a,"width",180),height=num(a,"height",220),cx=num(a,"x",200),y=num(a,"y",250);svg.append("<image href='").append(escape(w.getMaskUrl())).append("' x='").append(cx-width/2).append("' y='").append(y).append("' width='").append(width).append("' height='").append(height).append("' preserveAspectRatio='xMidYMid meet'/>");}svg.append("<rect x='18' y='18' width='364' height='38' rx='12' fill='white' opacity='.86'/><text x='200' y='43' text-anchor='middle' font-family='sans-serif' font-size='14' fill='#444'>").append(label).append(" · 실제 사이즈 비보장</text></svg>");return storage.writeSvg(userId,"try-on",svg.toString());}
    private Map<String,Object> read(String s){try{return json.readValue(s,new TypeReference<>(){});}catch(Exception e){return Map.of();}}private double num(Map<String,Object>m,String k,double d){Object v=m.get(k);return v instanceof Number n?n.doubleValue():d;}private String escape(String s){return s.replace("&","&amp;").replace("'","&apos;");}
    private TryOnResponse response(TryOn t){return new TryOnResponse(t.getId(),t.getAvatarId(),t.getOutfitId(),t.getPreviewUrl(),t.getRenderType(),t.getStatus(),t.getExpiresAt().toInstant(ZoneOffset.UTC));}
}
