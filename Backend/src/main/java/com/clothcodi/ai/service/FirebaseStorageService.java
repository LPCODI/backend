package com.clothcodi.ai.service;

import com.clothcodi.ai.common.AppException;
import com.google.api.gax.paging.Page;
import com.google.cloud.storage.Blob;
import com.google.cloud.storage.BlobId;
import com.google.cloud.storage.BlobInfo;
import com.google.cloud.storage.Bucket;
import com.google.cloud.storage.Storage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URI;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

@Service
@ConditionalOnProperty(name = "app.storage-provider", havingValue = "firebase", matchIfMissing = true)
public class FirebaseStorageService implements ImageStorageService {
    private static final Logger log = LoggerFactory.getLogger(FirebaseStorageService.class);
    private static final long MAX_IMAGE_BYTES = 10L * 1024 * 1024;
    private static final List<String> IMAGE_TYPES = List.of("image/jpeg", "image/png", "image/webp");

    private final Bucket bucket;
    private final Storage storage;

    public FirebaseStorageService(Bucket bucket) {
        this.bucket = bucket;
        this.storage = bucket.getStorage();
    }

    @Override
    public String saveImage(String userId, String folder, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw AppException.badRequest("IMAGE_REQUIRED", "이미지 파일이 필요합니다.");
        }
        String contentType = Objects.toString(file.getContentType(), "");
        if (!IMAGE_TYPES.contains(contentType)) {
            throw new AppException("UNSUPPORTED_IMAGE", "JPEG, PNG, WebP 이미지만 업로드할 수 있습니다.", HttpStatus.UNSUPPORTED_MEDIA_TYPE);
        }
        if (file.getSize() > MAX_IMAGE_BYTES) {
            throw AppException.badRequest("IMAGE_TOO_LARGE", "이미지는 10MB 이하만 업로드할 수 있습니다.");
        }
        String extension = switch (contentType) {
            case "image/jpeg" -> ".jpg";
            case "image/webp" -> ".webp";
            default -> ".png";
        };
        return put(userId, folder, extension, bytes(file), contentType);
    }

    @Override
    public String copyAsMask(String imageUrl, String userId) {
        Blob source = requiredBlob(imageUrl);
        String extension = extension(source.getName());
        String contentType = Objects.requireNonNullElse(source.getContentType(), contentType(extension));
        return put(userId, "masks", extension, source.getContent(), contentType);
    }

    @Override
    public String writeSvg(String userId, String folder, String svg) {
        return put(userId, folder, ".svg", svg.getBytes(StandardCharsets.UTF_8), "image/svg+xml");
    }

    @Override
    public String saveBytes(String userId, String folder, String extension, byte[] bytes) {
        return put(userId, folder, extension, bytes, contentType(extension));
    }

    @Override
    public Resource resourceForUrl(String url) {
        Blob blob = requiredBlob(url);
        byte[] content = blob.getContent();
        String filename = blob.getName().substring(blob.getName().lastIndexOf('/') + 1);
        return new ByteArrayResource(content) {
            @Override public String getFilename() { return filename; }
        };
    }

    @Override
    public void deleteUrl(String url) {
        if (url == null || url.isBlank()) return;
        try {
            String objectName = objectName(url);
            storage.delete(BlobId.of(bucket.getName(), objectName));
        } catch (RuntimeException e) {
            log.warn("Firebase Storage 파일 삭제에 실패했습니다: {}", e.getMessage());
        }
    }

    @Override
    public void deleteUser(String userId) {
        String prefix = "users/" + segment(userId, "userId") + "/";
        Page<Blob> blobs = bucket.list(Storage.BlobListOption.prefix(prefix));
        for (Blob blob : blobs.iterateAll()) {
            try {
                blob.delete();
            } catch (RuntimeException e) {
                log.warn("Firebase Storage 사용자 파일 삭제에 실패했습니다: {}", blob.getName());
            }
        }
    }

    private String put(String userId, String folder, String extension, byte[] bytes, String contentType) {
        String safeExtension = extension == null ? "" : extension.toLowerCase();
        if (!safeExtension.matches("\\.[a-z0-9]{2,5}")) {
            throw new IllegalArgumentException("invalid extension");
        }
        String objectName = "users/" + segment(userId, "userId") + "/" + segment(folder, "folder") + "/" + UUID.randomUUID() + safeExtension;
        String downloadToken = UUID.randomUUID().toString();
        BlobInfo info = BlobInfo.newBuilder(BlobId.of(bucket.getName(), objectName))
            .setContentType(contentType)
            .setCacheControl("private, max-age=3600")
            .setMetadata(Map.of(
                "firebaseStorageDownloadTokens", downloadToken,
                "ownerId", userId
            ))
            .build();
        storage.create(info, bytes, Storage.BlobTargetOption.doesNotExist());
        return downloadUrl(objectName, downloadToken);
    }

    private Blob requiredBlob(String url) {
        String objectName = objectName(url);
        Blob blob = storage.get(BlobId.of(bucket.getName(), objectName));
        if (blob == null) throw new IllegalStateException("Firebase Storage 파일을 찾을 수 없습니다.");
        return blob;
    }

    private String objectName(String url) {
        URI uri = URI.create(url);
        String rawPath = uri.getRawPath();
        if ("firebasestorage.googleapis.com".equalsIgnoreCase(uri.getHost())) {
            String prefix = "/v0/b/" + bucket.getName() + "/o/";
            if (!rawPath.startsWith(prefix)) throw new IllegalArgumentException("invalid Firebase Storage URL");
            return URLDecoder.decode(rawPath.substring(prefix.length()), StandardCharsets.UTF_8);
        }
        if ("storage.googleapis.com".equalsIgnoreCase(uri.getHost())) {
            String prefix = "/" + bucket.getName() + "/";
            if (!rawPath.startsWith(prefix)) throw new IllegalArgumentException("invalid Google Storage URL");
            return URLDecoder.decode(rawPath.substring(prefix.length()), StandardCharsets.UTF_8);
        }
        throw new IllegalArgumentException("unsupported storage URL");
    }

    private String downloadUrl(String objectName, String token) {
        String encodedObject = URLEncoder.encode(objectName, StandardCharsets.UTF_8);
        return "https://firebasestorage.googleapis.com/v0/b/" + bucket.getName() + "/o/" + encodedObject + "?alt=media&token=" + token;
    }

    private String segment(String value, String name) {
        if (value == null || !value.matches("[A-Za-z0-9_-]+")) throw new IllegalArgumentException("invalid " + name);
        return value;
    }

    private String extension(String objectName) {
        int dot = objectName.lastIndexOf('.');
        return dot < 0 ? ".png" : objectName.substring(dot).toLowerCase();
    }

    private String contentType(String extension) {
        return switch (extension.toLowerCase()) {
            case ".jpg", ".jpeg" -> "image/jpeg";
            case ".webp" -> "image/webp";
            case ".svg" -> "image/svg+xml";
            default -> "image/png";
        };
    }

    private byte[] bytes(MultipartFile file) {
        try {
            return file.getBytes();
        } catch (IOException e) {
            throw new IllegalStateException("이미지 파일을 읽을 수 없습니다.", e);
        }
    }
}
