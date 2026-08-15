package com.clothcodi.ai.common;

import java.util.Map;
import java.util.UUID;

public record ApiResponse<T>(T data, Map<String,Object> meta) {
    public static <T> ApiResponse<T> of(T data) {
        return new ApiResponse<>(data, Map.of("requestId", "req_" + UUID.randomUUID()));
    }
}

