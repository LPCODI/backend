package com.clothcodi.ai.common;

import org.springframework.http.*;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import java.util.*;

@RestControllerAdvice
public class GlobalExceptionHandler {
    record ErrorBody(String code, String message, List<Map<String,String>> fieldErrors, String requestId) {}
    @ExceptionHandler(AppException.class)
    ResponseEntity<ErrorBody> app(AppException e) { return body(e.status(),e.code(),e.getMessage(),List.of()); }
    @ExceptionHandler(BadCredentialsException.class)
    ResponseEntity<ErrorBody> auth() { return body(HttpStatus.UNAUTHORIZED,"INVALID_CREDENTIALS","이메일 또는 비밀번호가 올바르지 않습니다.",List.of()); }
    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ErrorBody> validation(MethodArgumentNotValidException e) {
        var errors=e.getBindingResult().getFieldErrors().stream().map(this::field).toList();
        return body(HttpStatus.BAD_REQUEST,"VALIDATION_ERROR","요청값을 확인해 주세요.",errors);
    }
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    ResponseEntity<ErrorBody> tooLarge() { return body(HttpStatus.PAYLOAD_TOO_LARGE,"FILE_TOO_LARGE","파일은 10MB 이하여야 합니다.",List.of()); }
    @ExceptionHandler(Exception.class)
    ResponseEntity<ErrorBody> unknown(Exception e) { return body(HttpStatus.INTERNAL_SERVER_ERROR,"INTERNAL_ERROR",e.getMessage()==null?"서버 오류가 발생했습니다.":e.getMessage(),List.of()); }
    private Map<String,String> field(FieldError e) { return Map.of("field",e.getField(),"message",Objects.toString(e.getDefaultMessage(),"invalid")); }
    private ResponseEntity<ErrorBody> body(HttpStatus s,String c,String m,List<Map<String,String>> f) {
        return ResponseEntity.status(s).body(new ErrorBody(c,m,f,"req_"+UUID.randomUUID()));
    }
}
