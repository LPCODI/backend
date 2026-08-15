package com.clothcodi.ai.controller;

import com.clothcodi.ai.common.ApiResponse;import com.clothcodi.ai.dto.ApiDtos.*;import com.clothcodi.ai.security.CurrentUser;import com.clothcodi.ai.service.ProfileService;
import jakarta.validation.Valid;import org.springframework.http.ResponseEntity;import org.springframework.web.bind.annotation.*;import java.util.Map;

@RestController
public class ProfileController {
 private final ProfileService s;public ProfileController(ProfileService s){this.s=s;}
 @GetMapping("/api/v1/users/me") ApiResponse<UserResponse> me(){return ApiResponse.of(s.user(CurrentUser.id()));}
 @PutMapping("/api/v1/users/me") ApiResponse<UserResponse> update(@Valid @RequestBody UserUpdateRequest r){return ApiResponse.of(s.updateUser(CurrentUser.id(),r));}
 @DeleteMapping("/api/v1/users/me") ResponseEntity<Void> delete(){s.deleteUser(CurrentUser.id());return ResponseEntity.noContent().build();}
 @GetMapping("/api/v1/body-profile") ApiResponse<BodyProfileResponse> body(){return ApiResponse.of(s.body(CurrentUser.id()));}
 @PutMapping("/api/v1/body-profile") ApiResponse<BodyProfileResponse> body(@Valid @RequestBody BodyProfileRequest r){return ApiResponse.of(s.saveBody(CurrentUser.id(),r));}
 @DeleteMapping("/api/v1/body-profile") ResponseEntity<Void> deleteBody(){s.deleteBody(CurrentUser.id());return ResponseEntity.noContent().build();}
 @PostMapping("/api/v1/avatar/generate") ApiResponse<AvatarResponse> generate(){return ApiResponse.of(s.generateAvatar(CurrentUser.id(),null,null));}
 @GetMapping("/api/v1/avatar") ApiResponse<AvatarResponse> avatar(){return ApiResponse.of(s.avatar(CurrentUser.id()));}
 @PutMapping("/api/v1/avatar") ApiResponse<AvatarResponse> avatar(@Valid @RequestBody AvatarUpdateRequest r){return ApiResponse.of(s.generateAvatar(CurrentUser.id(),r.templateId(),r.options()));}
 @DeleteMapping("/api/v1/avatar") ResponseEntity<Void> deleteAvatar(){s.deleteAvatar(CurrentUser.id());return ResponseEntity.noContent().build();}
}
