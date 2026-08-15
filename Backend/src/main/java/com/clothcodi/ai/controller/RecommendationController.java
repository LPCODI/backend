package com.clothcodi.ai.controller;

import com.clothcodi.ai.common.ApiResponse;import com.clothcodi.ai.dto.ApiDtos.*;import com.clothcodi.ai.security.CurrentUser;import com.clothcodi.ai.service.RecommendationService;import jakarta.validation.Valid;import org.springframework.http.*;import org.springframework.web.bind.annotation.*;

@RestController @RequestMapping("/api/v1/recommendations")
public class RecommendationController {private final RecommendationService s;public RecommendationController(RecommendationService s){this.s=s;}
 @PostMapping ResponseEntity<ApiResponse<RecommendationResponse>> create(@Valid @RequestBody RecommendationRequest r){return ResponseEntity.status(201).body(ApiResponse.of(s.create(CurrentUser.id(),r)));}
 @GetMapping("/{id}") ApiResponse<RecommendationResponse> get(@PathVariable String id){return ApiResponse.of(s.get(CurrentUser.id(),id));}
 @PostMapping("/{id}/regenerate") ResponseEntity<ApiResponse<RecommendationResponse>> regen(@PathVariable String id){return ResponseEntity.status(201).body(ApiResponse.of(s.regenerate(CurrentUser.id(),id)));}
}
