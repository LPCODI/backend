package com.clothcodi.ai.service;

import com.clothcodi.ai.dto.ApiDtos.WeatherResponse;
import com.clothcodi.ai.model.DbModels.WeatherCache;
import com.clothcodi.ai.repository.CodiMapper;
import com.fasterxml.jackson.databind.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Service
public class WeatherService {
    private final CodiMapper db;private final ObjectMapper json;private final String key;private final RestClient http=RestClient.create();
    public WeatherService(CodiMapper db,ObjectMapper json,@Value("${app.weather.service-key:}")String key){this.db=db;this.json=json;this.key=key;}
    public WeatherResponse forecast(double lat,double lon,OffsetDateTime at){
        OffsetDateTime target=at==null?OffsetDateTime.now(ZoneOffset.ofHours(9)):at;int[] grid=grid(lat,lon);String cacheKey=grid[0]+":"+grid[1]+":"+target.format(DateTimeFormatter.ofPattern("yyyyMMddHH"));
        WeatherCache cached=db.findWeatherCache(cacheKey);if(cached!=null)try{return json.readValue(cached.getPayloadJson(),WeatherResponse.class);}catch(Exception ignored){}
        WeatherResponse result;
        try{result=key.isBlank()?fallback(lat,lon,target):kma(lat,lon,target,grid);}catch(Exception e){result=fallback(lat,lon,target);}
        WeatherCache c=new WeatherCache();c.setCacheKey(cacheKey);c.setGridX(grid[0]);c.setGridY(grid[1]);c.setForecastAt(target.toLocalDateTime());c.setPayloadJson(write(result));c.setExpiresAt(LocalDateTime.now().plusMinutes(30));db.deleteWeatherCache(cacheKey);db.insertWeatherCache(c);return result;
    }
    private WeatherResponse kma(double lat,double lon,OffsetDateTime at,int[] g)throws Exception{
        ZonedDateTime now=ZonedDateTime.now(ZoneId.of("Asia/Seoul")).minusMinutes(15);int[] times={2,5,8,11,14,17,20,23};int base=2;for(int t:times)if(now.getHour()>=t)base=t;LocalDate baseDate=now.toLocalDate();if(now.getHour()<2){base=23;baseDate=baseDate.minusDays(1);}
        String url="https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst?serviceKey="+key+"&pageNo=1&numOfRows=1000&dataType=JSON&base_date="+baseDate.format(DateTimeFormatter.BASIC_ISO_DATE)+"&base_time="+String.format("%02d00",base)+"&nx="+g[0]+"&ny="+g[1];
        JsonNode items=http.get().uri(url).retrieve().body(JsonNode.class).path("response").path("body").path("items").path("item");Map<String,Double> values=new HashMap<>();
        String targetDate=at.format(DateTimeFormatter.ofPattern("yyyyMMdd")),targetTime=at.format(DateTimeFormatter.ofPattern("HH00"));
        for(JsonNode item:items)if(item.path("fcstDate").asText().equals(targetDate)&&item.path("fcstTime").asText().equals(targetTime))values.put(item.path("category").asText(),item.path("fcstValue").asDouble());
        if(!values.containsKey("TMP"))throw new IllegalStateException("forecast unavailable");int temp=values.get("TMP").intValue(),humidity=values.getOrDefault("REH",60d).intValue();double wind=values.getOrDefault("WSD",1.5),rain=values.getOrDefault("PCP",0d);int feels=(int)Math.round(temp-(wind>4?2:0)+(humidity>80&&temp>25?2:0));String condition=values.getOrDefault("PTY",0d)>0?"RAIN":"CLEAR";
        return new WeatherResponse(lat,lon,at,temp,feels,humidity,rain,wind,8,condition,"KMA",false);
    }
    private WeatherResponse fallback(double lat,double lon,OffsetDateTime at){int month=at.getMonthValue();int base=switch(month){case 12,1,2->4;case 3,4,11->14;case 5,6,9,10->22;default->29;};int temp=base+(at.getHour()>=12&&at.getHour()<=16?3:0);return new WeatherResponse(lat,lon,at,temp,temp,60,0,1.8,8,"SEASONAL_DEFAULT","FALLBACK",true);}
    private int[] grid(double lat,double lon){double RE=6371.00877,GRID=5.0,SLAT1=30.0,SLAT2=60.0,OLON=126.0,OLAT=38.0,XO=43,YO=136;double DEGRAD=Math.PI/180,re=RE/GRID,slat1=SLAT1*DEGRAD,slat2=SLAT2*DEGRAD,olon=OLON*DEGRAD,olat=OLAT*DEGRAD;double sn=Math.tan(Math.PI*.25+slat2*.5)/Math.tan(Math.PI*.25+slat1*.5);sn=Math.log(Math.cos(slat1)/Math.cos(slat2))/Math.log(sn);double sf=Math.tan(Math.PI*.25+slat1*.5);sf=Math.pow(sf,sn)*Math.cos(slat1)/sn;double ro=Math.tan(Math.PI*.25+olat*.5);ro=re*sf/Math.pow(ro,sn);double ra=Math.tan(Math.PI*.25+lat*DEGRAD*.5);ra=re*sf/Math.pow(ra,sn);double theta=lon*DEGRAD-olon;if(theta>Math.PI)theta-=2*Math.PI;if(theta< -Math.PI)theta+=2*Math.PI;theta*=sn;return new int[]{(int)Math.floor(ra*Math.sin(theta)+XO+.5),(int)Math.floor(ro-ra*Math.cos(theta)+YO+.5)};}
    private String write(Object o){try{return json.writeValueAsString(o);}catch(Exception e){throw new IllegalStateException(e);}}
}

