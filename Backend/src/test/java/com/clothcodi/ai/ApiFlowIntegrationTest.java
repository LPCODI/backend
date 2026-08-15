package com.clothcodi.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import java.util.UUID;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(properties = {
    "spring.profiles.active=test",
    "spring.datasource.url=jdbc:h2:mem:codi-ai-test;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "app.storage-provider=local",
    "app.storage-dir=./target/test-uploads"
})
@AutoConfigureMockMvc
class ApiFlowIntegrationTest {
    @Autowired MockMvc mvc; @Autowired ObjectMapper json;
    @Test void authProfileAndSwaggerFlow() throws Exception {
        String email="test-"+UUID.randomUUID()+"@example.com";
        mvc.perform(get("/v3/api-docs")).andExpect(status().isOk()).andExpect(jsonPath("$.paths").isMap());
        mvc.perform(get("/api/v1/users/me")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/auth/signup").contentType(MediaType.APPLICATION_JSON)
            .content("{\"email\":\""+email+"\",\"password\":\"TestPass123!\",\"nickname\":\"tester\"}"))
            .andExpect(status().isCreated()).andExpect(jsonPath("$.data.email").value(email));
        String body=mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
            .content("{\"email\":\""+email+"\",\"password\":\"TestPass123!\"}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.data.accessToken").isString()).andReturn().getResponse().getContentAsString();
        JsonNode token=json.readTree(body).path("data").path("accessToken");
        mvc.perform(put("/api/v1/body-profile").header("Authorization","Bearer "+token.asText()).contentType(MediaType.APPLICATION_JSON)
            .content("{\"heightCm\":170,\"bodyType\":\"RECTANGLE\",\"genderExpression\":\"NEUTRAL\",\"consent\":true}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.data.heightCm").value(170));

        MockMultipartFile image=new MockMultipartFile("image","shirt.png","image/png",new byte[]{1,2,3,4});
        String itemBody=mvc.perform(multipart("/api/v1/wardrobe").file(image)
            .param("name","test shirt").param("category","TOP")
            .header("Authorization","Bearer "+token.asText()))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.data.imageUrl").isString())
            .andExpect(jsonPath("$.data.maskUrl").isString())
            .andReturn().getResponse().getContentAsString();
        String itemId=json.readTree(itemBody).path("data").path("id").asText();
        mvc.perform(delete("/api/v1/wardrobe/{itemId}",itemId)
            .header("Authorization","Bearer "+token.asText()))
            .andExpect(status().isNoContent());
    }
}
