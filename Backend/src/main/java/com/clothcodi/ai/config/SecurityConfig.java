package com.clothcodi.ai.config;

import com.clothcodi.ai.security.JwtAuthFilter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.*;
import org.springframework.web.servlet.config.annotation.*;
import java.util.List;

@Configuration
public class SecurityConfig implements WebMvcConfigurer {
    @Value("${app.storage-dir}") String storageDir;
    @Value("${app.cors-origin}") String corsOrigin;
    @Bean PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(); }
    @Bean
    SecurityFilterChain security(HttpSecurity http, JwtAuthFilter jwt) throws Exception {
        return http.csrf(c->c.disable()).cors(c->c.configurationSource(cors()))
            .sessionManagement(s->s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(e->e.authenticationEntryPoint((req,res,ex)->{
                res.setStatus(401);res.setContentType("application/json;charset=UTF-8");
                res.getWriter().write("{\"code\":\"UNAUTHORIZED\",\"message\":\"인증이 필요합니다.\",\"fieldErrors\":[]}");
            }).accessDeniedHandler((req,res,ex)->{
                res.setStatus(403);res.setContentType("application/json;charset=UTF-8");
                res.getWriter().write("{\"code\":\"FORBIDDEN\",\"message\":\"접근 권한이 없습니다.\",\"fieldErrors\":[]}");
            }))
            .authorizeHttpRequests(a->a
                .requestMatchers("/api/v1/auth/**","/swagger-ui/**","/swagger-ui.html","/v3/api-docs/**","/error").permitAll()
                .requestMatchers(HttpMethod.GET,"/files/**").permitAll()
                .anyRequest().authenticated())
            .addFilterBefore(jwt, UsernamePasswordAuthenticationFilter.class).build();
    }
    CorsConfigurationSource cors() {
        var c=new CorsConfiguration(); c.setAllowedOrigins(List.of(corsOrigin));
        c.setAllowedMethods(List.of("GET","POST","PUT","DELETE","OPTIONS"));
        c.setAllowedHeaders(List.of("*")); c.setAllowCredentials(true);
        var source=new UrlBasedCorsConfigurationSource(); source.registerCorsConfiguration("/**",c); return source;
    }
    @Override public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/files/**").addResourceLocations("file:"+java.nio.file.Path.of(storageDir).toAbsolutePath()+"/");
    }
}
