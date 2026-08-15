package com.clothcodi.ai.service;

import org.springframework.core.io.Resource;
import org.springframework.web.multipart.MultipartFile;

public interface ImageStorageService {
    String saveImage(String userId, String folder, MultipartFile file);
    String copyAsMask(String imageUrl, String userId);
    String writeSvg(String userId, String folder, String svg);
    String saveBytes(String userId, String folder, String extension, byte[] bytes);
    Resource resourceForUrl(String url);
    void deleteUrl(String url);
    void deleteUser(String userId);
}
