package com.clothcodi.ai.controller;

import com.clothcodi.ai.common.ApiResponse;import com.clothcodi.ai.dto.ApiDtos.*;import com.clothcodi.ai.service.*;import jakarta.validation.Valid;import org.springframework.format.annotation.DateTimeFormat;import org.springframework.web.bind.annotation.*;import java.time.OffsetDateTime;

@RestController @RequestMapping("/api/v1")
public class ContextController {
 private final TpoService tpo;private final WeatherService weather;public ContextController(TpoService tpo,WeatherService weather){this.tpo=tpo;this.weather=weather;}
 @PostMapping("/tpo/parse") ApiResponse<TpoParseResponse> parse(@Valid @RequestBody TpoParseRequest r){return ApiResponse.of(tpo.parse(r));}
 @GetMapping("/weather/forecast") ApiResponse<WeatherResponse> weather(@RequestParam double latitude,@RequestParam double longitude,@RequestParam(required=false)@DateTimeFormat(iso=DateTimeFormat.ISO.DATE_TIME)OffsetDateTime at){return ApiResponse.of(weather.forecast(latitude,longitude,at));}
}
