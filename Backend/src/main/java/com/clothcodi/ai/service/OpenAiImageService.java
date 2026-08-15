package com.clothcodi.ai.service;

import com.clothcodi.ai.model.DbModels.WardrobeItem;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.web.client.RestClient;
import java.util.*;

@Service
public class OpenAiImageService {
    private final String apiKey,model;private final ImageStorageService storage;
    public OpenAiImageService(@Value("${app.openai.api-key:}")String apiKey,@Value("${app.openai.image-model:gpt-image-2}")String model,ImageStorageService storage){this.apiKey=apiKey;this.model=model;this.storage=storage;}
    public Optional<String> render(String userId,List<WardrobeItem> items,String bodyDescription){
        if(apiKey.isBlank()||items.isEmpty())return Optional.empty();
        try{var form=new LinkedMultiValueMap<String,Object>();form.add("model",model);form.add("quality","medium");form.add("size","1024x1536");
            String clothes=items.stream().map(i->i.getColor()+" "+i.getName()+"("+i.getCategory()+")").reduce((a,b)->a+", "+b).orElse("");
            form.add("prompt","Create a full-body front-view fashion try-on on a clean studio background. Preserve the supplied garments' colors, patterns and silhouettes. Dress a "+bodyDescription+" avatar in: "+clothes+". No text, no logos added, neutral pose.");
            for(WardrobeItem item:items)form.add("image[]",storage.resourceForUrl(item.getImageUrl()));
            JsonNode response=RestClient.builder().baseUrl("https://api.openai.com/v1").defaultHeader("Authorization","Bearer "+apiKey).build().post().uri("/images/edits").contentType(MediaType.MULTIPART_FORM_DATA).body(form).retrieve().body(JsonNode.class);
            String b64=response.path("data").path(0).path("b64_json").asText();if(b64.isBlank())return Optional.empty();return Optional.of(storage.saveBytes(userId,"try-on",".png",Base64.getDecoder().decode(b64)));
        }catch(Exception e){return Optional.empty();}
    }
}
