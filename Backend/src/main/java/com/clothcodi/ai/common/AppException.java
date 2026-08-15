package com.clothcodi.ai.common;

import org.springframework.http.HttpStatus;

public class AppException extends RuntimeException {
    private final String code;
    private final HttpStatus status;
    public AppException(String code, String message, HttpStatus status) { super(message); this.code=code; this.status=status; }
    public String code() { return code; }
    public HttpStatus status() { return status; }
    public static AppException notFound(String code, String message) { return new AppException(code,message,HttpStatus.NOT_FOUND); }
    public static AppException badRequest(String code, String message) { return new AppException(code,message,HttpStatus.BAD_REQUEST); }
    public static AppException forbidden() { return new AppException("FORBIDDEN","접근 권한이 없습니다.",HttpStatus.FORBIDDEN); }
}

