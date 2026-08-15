package com.clothcodi.ai.security;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import javax.crypto.SecretKey;
import java.time.Instant;
import java.util.*;

@Service
public class JwtService {
    private final SecretKey key; private final long accessSeconds;
    public JwtService(@Value("${app.jwt.secret}") String secret,@Value("${app.jwt.access-seconds}") long accessSeconds) {
        this.key=Keys.hmacShaKeyFor(Base64.getDecoder().decode(secret)); this.accessSeconds=accessSeconds;
    }
    public String issue(String userId) {
        Instant now=Instant.now();
        return Jwts.builder().subject(userId).issuedAt(Date.from(now)).expiration(Date.from(now.plusSeconds(accessSeconds)))
            .signWith(key).compact();
    }
    public String subject(String token) { return Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload().getSubject(); }
    public long accessSeconds() { return accessSeconds; }
}

