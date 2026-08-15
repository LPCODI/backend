package com.clothcodi.ai.service;

import com.clothcodi.ai.dto.ApiDtos.*;
import org.springframework.stereotype.Service;
import java.time.*;
import java.util.*;

@Service
public class TpoService {
    public TpoParseResponse parse(TpoParseRequest r){
        LocalDate date=r.baseDate()==null?LocalDate.now():r.baseDate();ZoneId zone=ZoneId.of(r.timezone()==null?"Asia/Seoul":r.timezone());
        String[] chunks=r.text().split("\\s*(?:후|그리고|,|→)\\s*");List<TpoSegment> segments=new ArrayList<>();
        for(String c:chunks){if(c.isBlank())continue;int hour=c.contains("아침")?8:c.contains("오전")?10:c.contains("저녁")?19:c.contains("밤")?21:c.contains("오후")?14:12;
            String activity=c.contains("데이트")?"데이트":c.contains("수업")||c.contains("학교")?"수업":c.contains("면접")?"면접":c.contains("운동")?"운동":c.contains("결혼")?"행사":"일상";
            String formality=switch(activity){case "면접","행사"->"FORMAL";case "데이트"->"SMART_CASUAL";case "운동"->"SPORT";default->"CASUAL";};
            String location=c.contains("해운대")?"해운대":c.contains("학교")?"학교":c.contains("회사")?"회사":"장소 확인 필요";
            segments.add(new TpoSegment(ZonedDateTime.of(date,LocalTime.of(hour,0),zone).toOffsetDateTime(),location,activity,formality));}
        if(segments.isEmpty())segments.add(new TpoSegment(ZonedDateTime.of(date,LocalTime.NOON,zone).toOffsetDateTime(),"장소 확인 필요","일상","CASUAL"));
        return new TpoParseResponse(segments,true);
    }
}

