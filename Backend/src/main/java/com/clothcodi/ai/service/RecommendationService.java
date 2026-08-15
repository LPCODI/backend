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
import java.util.stream.Collectors;

@Service
public class RecommendationService {
    private final CodiMapper db;private final ObjectMapper json;private final WeatherService weather;
    public RecommendationService(CodiMapper db,ObjectMapper json,WeatherService weather){this.db=db;this.json=json;this.weather=weather;}
    @Transactional public RecommendationResponse create(String userId,RecommendationRequest request){
        List<WardrobeItem> wardrobe=db.allWardrobe(userId);if(wardrobe.size()<2)throw AppException.badRequest("INSUFFICIENT_WARDROBE","추천을 위해 서로 다른 카테고리의 의류를 2개 이상 등록해 주세요.");
        OffsetDateTime at=request.tpoSegments().getFirst().startAt();WeatherResponse w=weather.forecast(request.location().latitude(),request.location().longitude(),at);
        Recommendation rec=new Recommendation();rec.setId(UUID.randomUUID().toString());rec.setUserId(userId);rec.setRequestJson(write(request));rec.setWeatherJson(write(w));rec.setStatus("COMPLETED");rec.setCreatedAt(LocalDateTime.now());db.insertRecommendation(rec);
        int max=request.maxOutfits()==null?3:request.maxOutfits();List<List<WardrobeItem>> combinations=combine(wardrobe,max,w);
        int rank=1;for(List<WardrobeItem> combo:combinations){saveOutfit(rec,combo,rank++,w,request);}
        return response(userId,rec);
    }
    @Transactional public RecommendationResponse regenerate(String userId,String id){Recommendation old=ownedRec(userId,id);try{return create(userId,json.readValue(old.getRequestJson(),RecommendationRequest.class));}catch(Exception e){throw AppException.badRequest("INVALID_RECOMMENDATION_SNAPSHOT","저장된 추천 조건을 읽을 수 없습니다.");}}
    public RecommendationResponse get(String userId,String id){return response(userId,ownedRec(userId,id));}
    public Outfit ownedOutfit(String userId,String id){Outfit o=db.findOutfit(userId,id);if(o==null)throw AppException.notFound("OUTFIT_NOT_FOUND","코디를 찾을 수 없습니다.");return o;}
    public OutfitResponse outfitResponse(String userId,Outfit o){List<String> ids=db.listOutfitItems(o.getId()).stream().map(OutfitItem::getWardrobeItemId).toList();return new OutfitResponse(o.getId(),o.getOutfitRank(),o.getScore(),ids,o.getReason(),o.getWeatherTip(),o.getFitTip(),readList(o.getAlternativesJson()));}
    @Transactional public Outfit createDirectOutfit(String userId,List<String> ids){
        List<WardrobeItem> items=ids.stream().map(id->{WardrobeItem w=db.findWardrobe(userId,id);if(w==null)throw AppException.forbidden();return w;}).toList();
        Recommendation r=new Recommendation();r.setId(UUID.randomUUID().toString());r.setUserId(userId);r.setRequestJson("{}");r.setWeatherJson("{}");r.setStatus("DIRECT");r.setCreatedAt(LocalDateTime.now());db.insertRecommendation(r);
        Outfit o=new Outfit();o.setId(UUID.randomUUID().toString());o.setRecommendationId(r.getId());o.setOutfitRank(1);o.setScore(80);o.setReason("사용자가 직접 선택한 조합");o.setWeatherTip("입기 전 실제 날씨를 확인하세요.");o.setFitTip("아바타는 스타일·비율 참고용입니다.");o.setAlternativesJson("[]");db.insertOutfit(o);insertItems(o,items);return o;
    }
    private RecommendationResponse response(String userId,Recommendation r){try{List<TpoSegment> tpos=json.readValue(r.getRequestJson(),RecommendationRequest.class).tpoSegments();WeatherResponse w=json.readValue(r.getWeatherJson(),WeatherResponse.class);List<OutfitResponse> outfits=db.listOutfits(userId,r.getId()).stream().map(o->outfitResponse(userId,o)).toList();return new RecommendationResponse(r.getId(),tpos,w,r.getStatus(),outfits,r.getCreatedAt().toInstant(ZoneOffset.UTC));}catch(Exception e){if("DIRECT".equals(r.getStatus()))return new RecommendationResponse(r.getId(),List.of(),null,r.getStatus(),db.listOutfits(userId,r.getId()).stream().map(o->outfitResponse(userId,o)).toList(),r.getCreatedAt().toInstant(ZoneOffset.UTC));throw new IllegalStateException(e);}}
    private void saveOutfit(Recommendation r,List<WardrobeItem> items,int rank,WeatherResponse w,RecommendationRequest req){Outfit o=new Outfit();o.setId(UUID.randomUUID().toString());o.setRecommendationId(r.getId());o.setOutfitRank(rank);int weatherScore=weatherScore(items,w),tpoScore=tpoScore(items,req.tpoSegments());int color=82-rank*2,fit=80,preference=78,usage=85;o.setScore((int)Math.round(weatherScore*.25+tpoScore*.25+color*.20+fit*.15+preference*.10+usage*.05));o.setReason(req.desiredMood()==null?"일정의 격식과 보유 의류 조화를 반영했습니다.":"'"+req.desiredMood()+"' 분위기와 일정의 격식을 반영했습니다.");o.setWeatherTip(w.precipitationMm()>0?"비가 예상되어 방수 신발이나 우산을 준비하세요.":w.feelsLikeC()<12?"체감온도가 낮아 아우터를 권장합니다.":"현재 기온에 무난한 구성입니다.");o.setFitTip("체형 프로필과 기본 핏 정보를 반영했으며 실제 사이즈는 착용 전 확인하세요.");Set<String> used=items.stream().map(WardrobeItem::getId).collect(Collectors.toSet());o.setAlternativesJson(write(db.allWardrobe(r.getUserId()).stream().map(WardrobeItem::getId).filter(id->!used.contains(id)).limit(3).toList()));db.insertOutfit(o);insertItems(o,items);}
    private void insertItems(Outfit o,List<WardrobeItem> items){int index=0;for(WardrobeItem w:items){OutfitItem oi=new OutfitItem();oi.setOutfitId(o.getId());oi.setWardrobeItemId(w.getId());oi.setRole(w.getCategory());oi.setLayerOrder(layer(w.getCategory())+index++);db.insertOutfitItem(oi);}}
    private List<List<WardrobeItem>> combine(List<WardrobeItem> all,int max,WeatherResponse w){Map<String,List<WardrobeItem>> by=all.stream().collect(Collectors.groupingBy(WardrobeItem::getCategory));List<List<WardrobeItem>> result=new ArrayList<>();for(int i=0;i<max;i++){List<WardrobeItem> c=new ArrayList<>();for(String cat:List.of("BOTTOM","TOP","OUTER","SHOES")){List<WardrobeItem> items=by.getOrDefault(cat,List.of());if(!items.isEmpty()&&(!cat.equals("OUTER")||w.feelsLikeC()<24))c.add(items.get(i%items.size()));}if(c.size()<2)c=all.stream().skip(i%all.size()).limit(Math.min(4,all.size())).toList();List<String> signature=c.stream().map(WardrobeItem::getId).sorted().toList();if(result.stream().noneMatch(x->x.stream().map(WardrobeItem::getId).sorted().toList().equals(signature)))result.add(c);}if(result.isEmpty())result.add(all.stream().limit(3).toList());return result;}
    private int weatherScore(List<WardrobeItem> items,WeatherResponse w){double avg=items.stream().map(WardrobeItem::getWarmth).filter(Objects::nonNull).mapToInt(Integer::intValue).average().orElse(3);double target=w.feelsLikeC()<8?5:w.feelsLikeC()<16?4:w.feelsLikeC()<24?3:1;return Math.max(50,100-(int)Math.abs(avg-target)*12);}
    private int tpoScore(List<WardrobeItem> items,List<TpoSegment> tpos){boolean formal=tpos.stream().anyMatch(t->"FORMAL".equals(t.formality()));long matches=items.stream().filter(i->formal?"FORMAL".equals(i.getFormality()):!"FORMAL".equals(i.getFormality())).count();return 65+(int)(30.0*matches/items.size());}
    private int layer(String category){return switch(category){case "BOTTOM"->20;case "TOP"->30;case "OUTER"->40;case "SHOES"->50;default->10;};}
    private Recommendation ownedRec(String userId,String id){Recommendation r=db.findRecommendation(userId,id);if(r==null)throw AppException.notFound("RECOMMENDATION_NOT_FOUND","추천 결과를 찾을 수 없습니다.");return r;}
    private String write(Object o){try{return json.writeValueAsString(o);}catch(Exception e){throw new IllegalStateException(e);}}private List<String> readList(String s){try{return json.readValue(s,new TypeReference<>(){});}catch(Exception e){return List.of();}}
}

