package com.clothcodi.ai.controller;

import com.clothcodi.ai.common.ApiResponse;import com.clothcodi.ai.dto.ApiDtos.*;import com.clothcodi.ai.security.CurrentUser;import com.clothcodi.ai.service.WardrobeService;
import jakarta.validation.Valid;import org.springframework.http.*;import org.springframework.web.bind.annotation.*;import org.springframework.web.multipart.MultipartFile;import java.util.List;

@RestController @RequestMapping("/api/v1/wardrobe")
public class WardrobeController {
 private final WardrobeService s;public WardrobeController(WardrobeService s){this.s=s;}
 @GetMapping ApiResponse<List<WardrobeItemResponse>> list(@RequestParam(required=false)String category,@RequestParam(required=false)String season,@RequestParam(required=false)String color,@RequestParam(defaultValue="0")int page,@RequestParam(defaultValue="20")int size){return ApiResponse.of(s.list(CurrentUser.id(),category,season,color,page,size));}
 @PostMapping(consumes=MediaType.MULTIPART_FORM_DATA_VALUE) ResponseEntity<ApiResponse<WardrobeItemResponse>> create(@RequestParam String name,@RequestParam String category,@RequestParam(required=false)String color,@RequestParam(required=false)String season,@RequestParam(required=false)Integer warmth,@RequestParam(required=false)String formality,@RequestParam(required=false)String fit,@RequestParam(required=false)String length,@RequestPart MultipartFile image){return ResponseEntity.status(201).body(ApiResponse.of(s.create(CurrentUser.id(),name,category,color,season,warmth,formality,fit,length,image)));}
 @GetMapping("/{itemId}") ApiResponse<WardrobeItemResponse> get(@PathVariable String itemId){return ApiResponse.of(s.get(CurrentUser.id(),itemId));}
 @PutMapping("/{itemId}") ApiResponse<WardrobeItemResponse> update(@PathVariable String itemId,@Valid @RequestBody WardrobeUpdateRequest r){return ApiResponse.of(s.update(CurrentUser.id(),itemId,r));}
 @DeleteMapping("/{itemId}") ResponseEntity<Void> delete(@PathVariable String itemId){s.delete(CurrentUser.id(),itemId);return ResponseEntity.noContent().build();}
 @PostMapping("/{itemId}/reanalyze") ApiResponse<WardrobeItemResponse> reanalyze(@PathVariable String itemId){return ApiResponse.of(s.reanalyze(CurrentUser.id(),itemId));}
}
