package com.clothcodi.ai.controller;

import com.clothcodi.ai.common.ApiResponse;import com.clothcodi.ai.dto.ApiDtos.*;import com.clothcodi.ai.security.CurrentUser;import com.clothcodi.ai.service.EngagementService;import jakarta.validation.Valid;import org.springframework.http.*;import org.springframework.web.bind.annotation.*;import java.util.List;

@RestController @RequestMapping("/api/v1")
public class EngagementController {private final EngagementService s;public EngagementController(EngagementService s){this.s=s;}
 @GetMapping("/favorites") ApiResponse<List<FavoriteResponse>> list(){return ApiResponse.of(s.favorites(CurrentUser.id()));}
 @PostMapping("/favorites") ResponseEntity<ApiResponse<FavoriteResponse>> favorite(@Valid @RequestBody FavoriteRequest r){return ResponseEntity.status(201).body(ApiResponse.of(s.favorite(CurrentUser.id(),r)));}
 @DeleteMapping("/favorites/{favoriteId}") ResponseEntity<Void> delete(@PathVariable String favoriteId){s.deleteFavorite(CurrentUser.id(),favoriteId);return ResponseEntity.noContent().build();}
 @PostMapping("/recommendations/{id}/feedback") ResponseEntity<Void> feedback(@PathVariable String id,@Valid @RequestBody RecommendationFeedbackRequest r){s.recommendationFeedback(CurrentUser.id(),id,r);return ResponseEntity.status(201).build();}
 @PostMapping("/outfits/feedback") ResponseEntity<ApiResponse<OutfitFeedbackResponse>> outfit(@Valid @RequestBody OutfitFeedbackRequest r){return ResponseEntity.status(201).body(ApiResponse.of(s.outfitFeedback(CurrentUser.id(),r)));}
}
