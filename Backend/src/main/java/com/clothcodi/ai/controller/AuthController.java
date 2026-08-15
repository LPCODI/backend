package com.clothcodi.ai.controller;

import com.clothcodi.ai.common.ApiResponse;
import com.clothcodi.ai.dto.ApiDtos.*;
import com.clothcodi.ai.service.AuthService;
import io.swagger.v3.oas.annotations.security.SecurityRequirements;
import jakarta.validation.Valid;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

@RestController @RequestMapping("/api/v1/auth") @SecurityRequirements
public class AuthController {
    private final AuthService service; public AuthController(AuthService service){this.service=service;}
    @PostMapping("/signup") ResponseEntity<ApiResponse<UserResponse>> signup(@Valid @RequestBody SignupRequest r){return ResponseEntity.status(201).body(ApiResponse.of(service.signup(r)));}
    @PostMapping("/login") ApiResponse<TokenResponse> login(@Valid @RequestBody LoginRequest r){return ApiResponse.of(service.login(r));}
    @PostMapping("/refresh") ApiResponse<TokenResponse> refresh(@Valid @RequestBody RefreshRequest r){return ApiResponse.of(service.refresh(r));}
    @PostMapping("/logout") ResponseEntity<Void> logout(@Valid @RequestBody LogoutRequest r){service.logout(r);return ResponseEntity.noContent().build();}
}
