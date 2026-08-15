package com.clothcodi.ai.service;

import com.clothcodi.ai.common.AppException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;

@Service
@ConditionalOnProperty(name = "app.storage-provider", havingValue = "local")
public class LocalStorageService implements ImageStorageService {
    private final Path root; private final String baseUrl;
    public LocalStorageService(@Value("${app.storage-dir}") String dir,@Value("${app.public-base-url}") String baseUrl) {
        this.root=Path.of(dir).toAbsolutePath().normalize(); this.baseUrl=baseUrl;
        try { Files.createDirectories(root); } catch(IOException e){throw new IllegalStateException(e);}
    }
    @Override public String saveImage(String userId,String folder,MultipartFile file) {
        if(file==null||file.isEmpty()) throw AppException.badRequest("IMAGE_REQUIRED","이미지 파일이 필요합니다.");
        String mime=Objects.toString(file.getContentType(),"");
        if(!List.of("image/jpeg","image/png","image/webp").contains(mime)) throw new AppException("UNSUPPORTED_IMAGE","JPEG, PNG, WebP 이미지만 업로드할 수 있습니다.",HttpStatus.UNSUPPORTED_MEDIA_TYPE);
        String ext=switch(mime){case "image/jpeg"->".jpg";case "image/webp"->".webp";default->".png";};
        return write(userId+"/"+folder+"/"+UUID.randomUUID()+ext,bytes(file));
    }
    @Override public String copyAsMask(String imageUrl,String userId) {
        try { return write(userId+"/masks/"+UUID.randomUUID()+extension(imageUrl),Files.readAllBytes(path(imageUrl))); }
        catch(IOException e){throw new IllegalStateException("마스크 생성 실패",e);}
    }
    @Override public String writeSvg(String userId,String folder,String svg) { return write(userId+"/"+folder+"/"+UUID.randomUUID()+".svg",svg.getBytes(java.nio.charset.StandardCharsets.UTF_8)); }
    @Override public String saveBytes(String userId,String folder,String extension,byte[] bytes) { return write(userId+"/"+folder+"/"+UUID.randomUUID()+extension,bytes); }
    @Override public Resource resourceForUrl(String url) { return new FileSystemResource(path(url)); }
    @Override public void deleteUrl(String url) { if(url==null)return; try{Files.deleteIfExists(path(url));}catch(IOException ignored){} }
    @Override public void deleteUser(String userId) {
        Path dir=root.resolve(userId).normalize(); if(!dir.startsWith(root)||!Files.exists(dir))return;
        try(var paths=Files.walk(dir)){paths.sorted(Comparator.reverseOrder()).forEach(p->{try{Files.deleteIfExists(p);}catch(IOException ignored){}});}catch(IOException ignored){}
    }
    private String write(String relative,byte[] bytes) {
        Path out=root.resolve(relative).normalize(); if(!out.startsWith(root))throw new SecurityException("invalid path");
        try{Files.createDirectories(out.getParent());Files.write(out,bytes,StandardOpenOption.CREATE_NEW);return baseUrl+"/files/"+relative.replace('\\','/');}
        catch(IOException e){throw new IllegalStateException("파일 저장 실패",e);}
    }
    private Path path(String url) { String marker="/files/"; int i=url.indexOf(marker); if(i<0)throw new IllegalArgumentException("invalid file url"); Path p=root.resolve(url.substring(i+marker.length())).normalize(); if(!p.startsWith(root))throw new SecurityException("invalid path"); return p; }
    private byte[] bytes(MultipartFile f){try{return f.getBytes();}catch(IOException e){throw new IllegalStateException(e);}}
    private String extension(String url){int dot=url.lastIndexOf('.');return dot<0?".png":url.substring(dot);}
}
