package com.clothcodi.ai.security;

import org.springframework.security.core.context.SecurityContextHolder;

public final class CurrentUser {
    private CurrentUser() {}
    public static String id() { return SecurityContextHolder.getContext().getAuthentication().getName(); }
}

