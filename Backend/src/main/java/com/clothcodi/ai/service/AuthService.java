package com.clothcodi.ai.service;

import com.clothcodi.ai.common.AppException;
import com.clothcodi.ai.dto.ApiDtos.*;
import com.clothcodi.ai.model.DbModels.User;
import com.clothcodi.ai.repository.CodiMapper;
import com.clothcodi.ai.security.JwtService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.*;
import java.util.*;

@Service
public class AuthService {
    private final CodiMapper db; private final PasswordEncoder passwords; private final JwtService jwt; private final long refreshSeconds;
    public AuthService(CodiMapper db,PasswordEncoder passwords,JwtService jwt,@Value("${app.jwt.refresh-seconds}") long refreshSeconds) {
        this.db=db; this.passwords=passwords; this.jwt=jwt; this.refreshSeconds=refreshSeconds;
    }
    @Transactional public UserResponse signup(SignupRequest r) {
        if(db.findUserByEmail(r.email().toLowerCase())!=null) throw new AppException("EMAIL_ALREADY_EXISTS","이미 가입된 이메일입니다.",HttpStatus.CONFLICT);
        User u=new User(); u.setId(UUID.randomUUID().toString()); u.setEmail(r.email().toLowerCase());
        u.setPasswordHash(passwords.encode(r.password())); u.setNickname(r.nickname()); u.setCreatedAt(LocalDateTime.now()); db.insertUser(u); return user(u);
    }
    public TokenResponse login(LoginRequest r) {
        User u=db.findUserByEmail(r.email().toLowerCase());
        if(u==null||!passwords.matches(r.password(),u.getPasswordHash())) throw new BadCredentialsException("invalid");
        return tokens(u.getId());
    }
    public TokenResponse refresh(RefreshRequest r) {
        String userId=db.validRefreshUser(hash(r.refreshToken())); if(userId==null) throw new AppException("INVALID_REFRESH_TOKEN","유효하지 않은 refresh token입니다.",HttpStatus.UNAUTHORIZED);
        db.revokeRefresh(hash(r.refreshToken())); return tokens(userId);
    }
    public void logout(LogoutRequest r) { db.revokeRefresh(hash(r.refreshToken())); }
    private TokenResponse tokens(String userId) {
        String refresh=UUID.randomUUID()+"."+UUID.randomUUID();
        db.insertRefresh(UUID.randomUUID().toString(),userId,hash(refresh),LocalDateTime.now().plusSeconds(refreshSeconds));
        return new TokenResponse("Bearer",jwt.issue(userId),jwt.accessSeconds(),refresh,refreshSeconds);
    }
    public static UserResponse user(User u) { return new UserResponse(u.getId(),u.getEmail(),u.getNickname(),u.getPersonalColor(),u.getStylePreference(),u.getCreatedAt().toInstant(ZoneOffset.UTC)); }
    private String hash(String value) { try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); } catch(Exception e){ throw new IllegalStateException(e); } }
}

