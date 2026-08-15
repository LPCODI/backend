package com.clothcodi.ai.service;

import com.clothcodi.ai.common.AppException;
import com.clothcodi.ai.dto.ApiDtos.*;
import com.clothcodi.ai.model.DbModels.WardrobeItem;
import com.clothcodi.ai.repository.CodiMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import java.time.*;
import java.util.*;

@Service
public class WardrobeService {
    private final CodiMapper db;private final ImageStorageService storage;private final ObjectMapper json;
    public WardrobeService(CodiMapper db,ImageStorageService storage,ObjectMapper json){this.db=db;this.storage=storage;this.json=json;}
    public List<WardrobeItemResponse> list(String userId,String category,String season,String color,int page,int size){int safeSize=Math.min(Math.max(size,1),100);return db.listWardrobe(userId,category,season,color,safeSize,Math.max(page,0)*safeSize).stream().map(this::response).toList();}
    public WardrobeItemResponse get(String userId,String id){return response(owned(userId,id));}
    @Transactional public WardrobeItemResponse create(String userId,String name,String category,String color,String season,Integer warmth,String formality,String fit,String length,MultipartFile image){
        String imageUrl=storage.saveImage(userId,"wardrobe",image);String maskUrl=storage.copyAsMask(imageUrl,userId);LocalDateTime now=LocalDateTime.now();
        WardrobeItem w=new WardrobeItem();w.setId(UUID.randomUUID().toString());w.setUserId(userId);w.setName(name);w.setCategory(normalize(category));w.setColor(defaultText(color,"미분류"));w.setSeason(defaultText(season,"ALL"));w.setWarmth(warmth==null?3:warmth);w.setFormality(defaultText(formality,"CASUAL"));w.setFit(defaultText(fit,"REGULAR"));w.setItemLength(defaultText(length,"REGULAR"));w.setDescription(name+" 이미지의 로컬 기본 분석 결과입니다. 속성을 확인해 주세요.");w.setImageUrl(imageUrl);w.setMaskUrl(maskUrl);w.setAnchorJson(write(anchor(w.getCategory())));w.setAnalysisStatus("NEEDS_CONFIRMATION");w.setCreatedAt(now);w.setUpdatedAt(now);db.insertWardrobe(w);return response(w);
    }
    public WardrobeItemResponse update(String userId,String id,WardrobeUpdateRequest r){WardrobeItem w=owned(userId,id);w.setName(r.name());w.setCategory(normalize(r.category()));w.setColor(r.color());w.setSeason(r.season());w.setWarmth(r.warmth());w.setFormality(r.formality());w.setFit(r.fit());w.setItemLength(r.length());w.setDescription(r.description());w.setAnchorJson(write(anchor(w.getCategory())));w.setAnalysisStatus("CONFIRMED");w.setUpdatedAt(LocalDateTime.now());db.updateWardrobe(w);return response(w);}
    @Transactional public void delete(String userId,String id){WardrobeItem w=owned(userId,id);if(db.deleteWardrobe(userId,id)==0)throw AppException.notFound("WARDROBE_ITEM_NOT_FOUND","의류를 찾을 수 없습니다.");storage.deleteUrl(w.getImageUrl());storage.deleteUrl(w.getMaskUrl());}
    public WardrobeItemResponse reanalyze(String userId,String id){WardrobeItem w=owned(userId,id);w.setDescription(w.getName()+" 재분석 완료: "+w.getColor()+" "+w.getCategory());w.setAnalysisStatus("NEEDS_CONFIRMATION");w.setUpdatedAt(LocalDateTime.now());db.updateWardrobe(w);return response(w);}
    public WardrobeItem owned(String userId,String id){WardrobeItem w=db.findWardrobe(userId,id);if(w==null){if(db.findWardrobeRaw(id)!=null)throw AppException.forbidden();throw AppException.notFound("WARDROBE_ITEM_NOT_FOUND","의류를 찾을 수 없습니다.");}return w;}
    public WardrobeItemResponse response(WardrobeItem w){return new WardrobeItemResponse(w.getId(),w.getName(),w.getCategory(),w.getColor(),w.getSeason(),w.getWarmth(),w.getFormality(),w.getFit(),w.getItemLength(),w.getDescription(),w.getImageUrl(),w.getMaskUrl(),read(w.getAnchorJson()),w.getAnalysisStatus(),w.getCreatedAt().toInstant(ZoneOffset.UTC));}
    private Map<String,Object> anchor(String category){return switch(category){case "TOP"->Map.of("x",200,"y",180,"width",190,"height",210,"layer",30);case "BOTTOM"->Map.of("x",200,"y",340,"width",170,"height",250,"layer",20);case "OUTER"->Map.of("x",200,"y",170,"width",230,"height",300,"layer",40);case "SHOES"->Map.of("x",200,"y",600,"width",160,"height",70,"layer",50);default->Map.of("x",200,"y",300,"width",180,"height",220,"layer",10);};}
    private String normalize(String s){return s==null?"OTHER":s.trim().toUpperCase();}private String defaultText(String s,String d){return s==null||s.isBlank()?d:s.toUpperCase();}
    private String write(Object o){try{return json.writeValueAsString(o);}catch(Exception e){throw new IllegalStateException(e);}}private Map<String,Object> read(String s){try{return json.readValue(s,new TypeReference<>(){});}catch(Exception e){return Map.of();}}
}
