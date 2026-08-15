package com.clothcodi.ai.config;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.cloud.storage.Bucket;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.cloud.StorageClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

@Configuration
@ConditionalOnProperty(name = "app.storage-provider", havingValue = "firebase", matchIfMissing = true)
public class FirebaseStorageConfig {
    private static final String APP_NAME = "codi-ai-storage";

    @Bean
    FirebaseApp firebaseStorageApp(
        @Value("${app.firebase.storage-bucket}") String bucketName,
        @Value("${app.firebase.credentials-path:}") String credentialsPath
    ) throws IOException {
        if (bucketName == null || bucketName.isBlank()) {
            throw new IllegalStateException("FIREBASE_STORAGE_BUCKET을 설정해야 합니다.");
        }

        GoogleCredentials credentials = credentials(credentialsPath);
        FirebaseOptions options = FirebaseOptions.builder()
            .setCredentials(credentials)
            .setStorageBucket(bucketName)
            .build();

        return FirebaseApp.getApps().stream()
            .filter(app -> APP_NAME.equals(app.getName()))
            .findFirst()
            .orElseGet(() -> FirebaseApp.initializeApp(options, APP_NAME));
    }

    @Bean
    Bucket firebaseStorageBucket(FirebaseApp firebaseStorageApp) {
        Bucket bucket = StorageClient.getInstance(firebaseStorageApp).bucket();
        if (bucket == null) {
            throw new IllegalStateException("설정한 Firebase Storage 버킷을 찾을 수 없습니다.");
        }
        return bucket;
    }

    private GoogleCredentials credentials(String credentialsPath) throws IOException {
        if (credentialsPath == null || credentialsPath.isBlank()) {
            return GoogleCredentials.getApplicationDefault();
        }
        Path path = Path.of(credentialsPath).toAbsolutePath().normalize();
        if (!Files.isRegularFile(path)) {
            throw new IllegalStateException("Firebase 서비스 계정 파일을 찾을 수 없습니다: " + path);
        }
        try (InputStream input = Files.newInputStream(path)) {
            return GoogleCredentials.fromStream(input);
        }
    }
}
