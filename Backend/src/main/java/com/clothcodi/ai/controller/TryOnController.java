package com.clothcodi.ai.controller;

import com.clothcodi.ai.common.ApiResponse;import com.clothcodi.ai.dto.ApiDtos.*;import com.clothcodi.ai.security.CurrentUser;import com.clothcodi.ai.service.TryOnService;import jakarta.validation.Valid;import org.springframework.http.*;import org.springframework.web.bind.annotation.*;

@RestController @RequestMapping("/api/v1/try-on")
public class TryOnController {private final TryOnService s;public TryOnController(TryOnService s){this.s=s;}
 @PostMapping("/preview") ResponseEntity<ApiResponse<TryOnResponse>> preview(@Valid @RequestBody TryOnRequest r){return ResponseEntity.status(201).body(ApiResponse.of(s.preview(CurrentUser.id(),r.outfitId())));}
 @PostMapping("/render") ResponseEntity<ApiResponse<TryOnResponse>> render(@Valid @RequestBody TryOnRequest r){return ResponseEntity.accepted().body(ApiResponse.of(s.render(CurrentUser.id(),r.outfitId())));}
 @GetMapping("/{resultId}") ApiResponse<TryOnResponse> get(@PathVariable String resultId){return ApiResponse.of(s.get(CurrentUser.id(),resultId));}
 @DeleteMapping("/{resultId}") ResponseEntity<Void> delete(@PathVariable String resultId){s.delete(CurrentUser.id(),resultId);return ResponseEntity.noContent().build();}
}

