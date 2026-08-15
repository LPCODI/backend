package com.clothcodi.ai.service;

import com.clothcodi.ai.common.AppException;
import com.clothcodi.ai.dto.ApiDtos.*;
import com.clothcodi.ai.model.DbModels.*;
import com.clothcodi.ai.repository.CodiMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.*;
import java.util.*;

@Service
public class ProfileService {
    private final CodiMapper db; private final ObjectMapper json; private final ImageStorageService storage;
    public ProfileService(CodiMapper db,ObjectMapper json,ImageStorageService storage){this.db=db;this.json=json;this.storage=storage;}
    public UserResponse user(String id){User u=db.findUser(id);if(u==null)throw AppException.notFound("USER_NOT_FOUND","사용자를 찾을 수 없습니다.");return AuthService.user(u);}
    public UserResponse updateUser(String id,UserUpdateRequest r){User u=db.findUser(id);if(u==null)throw AppException.notFound("USER_NOT_FOUND","사용자를 찾을 수 없습니다.");u.setNickname(r.nickname());u.setPersonalColor(r.personalColor());u.setStylePreference(r.stylePreference());db.updateUser(u);return AuthService.user(u);}
    @Transactional public void deleteUser(String id){db.deleteRefreshes(id);db.hardDeleteUser(id);storage.deleteUser(id);}
    public BodyProfileResponse body(String id){BodyProfile b=db.findBody(id);if(b==null)throw AppException.notFound("BODY_PROFILE_NOT_FOUND","신체 프로필을 찾을 수 없습니다.");return bodyResponse(b);}
    @Transactional public BodyProfileResponse saveBody(String id,BodyProfileRequest r){
        BodyProfile b=db.findBody(id);LocalDateTime now=LocalDateTime.now();
        if(b==null){b=new BodyProfile();b.setUserId(id);b.setConsentAt(now);} b.setHeightCm(r.heightCm());b.setBodyType(r.bodyType());b.setGenderExpression(r.genderExpression());b.setUpdatedAt(now);
        if(db.findBody(id)==null)db.insertBody(b);else db.updateBody(b); return bodyResponse(b);
    }
    @Transactional public void deleteBody(String id){Avatar avatar=db.findAvatar(id);db.deleteAvatars(id);db.deleteBody(id);if(avatar!=null)storage.deleteUrl(avatar.getImageUrl());}
    public AvatarResponse avatar(String id){Avatar a=db.findAvatar(id);if(a==null)throw AppException.notFound("AVATAR_NOT_FOUND","아바타를 찾을 수 없습니다.");return avatarResponse(a);}
    @Transactional public AvatarResponse generateAvatar(String id,String template,Map<String,Object> options){
        BodyProfile b=db.findBody(id);if(b==null)throw AppException.badRequest("BODY_PROFILE_REQUIRED","먼저 신체 프로필을 등록해 주세요.");
        Avatar old=db.findAvatar(id);int version=old==null?1:old.getVersion()+1;String templateId=template==null?"STANDARD_FRONT":template;
        Map<String,Object> params=new LinkedHashMap<>();params.put("heightCm",b.getHeightCm());params.put("bodyType",b.getBodyType());params.put("genderExpression",b.getGenderExpression());if(options!=null)params.putAll(options);
        double scale=Math.max(.82,Math.min(1.18,b.getHeightCm()/170.0));String svg=avatarSvg(b,scale);
        Avatar a=new Avatar();a.setId(UUID.randomUUID().toString());a.setUserId(id);a.setTemplateId(templateId);a.setParametersJson(write(params));a.setImageUrl(storage.writeSvg(id,"avatars",svg));a.setVersion(version);a.setCreatedAt(LocalDateTime.now());db.insertAvatar(a);if(old!=null)storage.deleteUrl(old.getImageUrl());return avatarResponse(a);
    }
    @Transactional public void deleteAvatar(String id){Avatar avatar=db.findAvatar(id);db.deleteAvatars(id);if(avatar!=null)storage.deleteUrl(avatar.getImageUrl());}
    private String avatarSvg(BodyProfile b,double scale){int shoulder=switch(b.getBodyType().toUpperCase()){case "INVERTED_TRIANGLE"->92;case "TRIANGLE"->68;default->80;};return "<svg xmlns='http://www.w3.org/2000/svg' width='400' height='700' viewBox='0 0 400 700'><rect width='400' height='700' fill='#f6f3ef'/><g transform='translate(200 30) scale("+scale+")' fill='#d8b49c' stroke='#775f52' stroke-width='3'><circle cx='0' cy='55' r='42'/><rect x='-16' y='96' width='32' height='28' rx='8'/><path d='M-"+shoulder+" 125 Q0 105 "+shoulder+" 125 L58 355 L42 600 L5 600 L0 370 L-5 600 L-42 600 L-58 355 Z'/></g><text x='200' y='675' text-anchor='middle' font-family='sans-serif' fill='#555'>스타일·비율 참고용</text></svg>";}
    private BodyProfileResponse bodyResponse(BodyProfile b){return new BodyProfileResponse(b.getUserId(),b.getHeightCm(),b.getBodyType(),b.getGenderExpression(),instant(b.getConsentAt()),instant(b.getUpdatedAt()));}
    private AvatarResponse avatarResponse(Avatar a){return new AvatarResponse(a.getId(),a.getTemplateId(),read(a.getParametersJson()),a.getImageUrl(),a.getVersion(),instant(a.getCreatedAt()));}
    private Instant instant(LocalDateTime t){return t.toInstant(ZoneOffset.UTC);} private String write(Object o){try{return json.writeValueAsString(o);}catch(Exception e){throw new IllegalStateException(e);}}
    private Map<String,Object> read(String s){try{return json.readValue(s,new TypeReference<>(){});}catch(Exception e){return Map.of();}}
}
