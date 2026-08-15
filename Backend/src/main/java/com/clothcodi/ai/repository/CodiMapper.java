package com.clothcodi.ai.repository;

import com.clothcodi.ai.model.DbModels.*;
import org.apache.ibatis.annotations.*;
import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface CodiMapper {
    @Select("SELECT * FROM users WHERE email=#{email} AND deleted_at IS NULL") User findUserByEmail(String email);
    @Select("SELECT * FROM users WHERE id=#{id} AND deleted_at IS NULL") User findUser(String id);
    @Insert("INSERT INTO users(id,email,password_hash,nickname,created_at) VALUES(#{id},#{email},#{passwordHash},#{nickname},#{createdAt})") void insertUser(User u);
    @Update("UPDATE users SET nickname=#{nickname},personal_color=#{personalColor},style_preference=#{stylePreference} WHERE id=#{id} AND deleted_at IS NULL") int updateUser(User u);
    @Update("UPDATE users SET deleted_at=#{at} WHERE id=#{id} AND deleted_at IS NULL") int softDeleteUser(@Param("id") String id,@Param("at") LocalDateTime at);
    @Delete("DELETE FROM users WHERE id=#{id}") int hardDeleteUser(String id);

    @Insert("INSERT INTO refresh_tokens(id,user_id,token_hash,expires_at) VALUES(#{id},#{userId},#{hash},#{expiresAt})") void insertRefresh(@Param("id") String id,@Param("userId") String userId,@Param("hash") String hash,@Param("expiresAt") LocalDateTime expiresAt);
    @Select("SELECT user_id FROM refresh_tokens WHERE token_hash=#{hash} AND revoked_at IS NULL AND expires_at>CURRENT_TIMESTAMP") String validRefreshUser(String hash);
    @Update("UPDATE refresh_tokens SET revoked_at=CURRENT_TIMESTAMP WHERE token_hash=#{hash} AND revoked_at IS NULL") int revokeRefresh(String hash);
    @Delete("DELETE FROM refresh_tokens WHERE user_id=#{userId}") void deleteRefreshes(String userId);

    @Select("SELECT * FROM body_profiles WHERE user_id=#{userId}") BodyProfile findBody(String userId);
    @Insert("INSERT INTO body_profiles(user_id,height_cm,body_type,gender_expression,consent_at,updated_at) VALUES(#{userId},#{heightCm},#{bodyType},#{genderExpression},#{consentAt},#{updatedAt})") void insertBody(BodyProfile b);
    @Update("UPDATE body_profiles SET height_cm=#{heightCm},body_type=#{bodyType},gender_expression=#{genderExpression},updated_at=#{updatedAt} WHERE user_id=#{userId}") void updateBody(BodyProfile b);
    @Delete("DELETE FROM body_profiles WHERE user_id=#{userId}") int deleteBody(String userId);

    @Select("SELECT * FROM avatars WHERE user_id=#{userId} ORDER BY version DESC LIMIT 1") Avatar findAvatar(String userId);
    @Insert("INSERT INTO avatars(id,user_id,template_id,parameters_json,image_url,version,created_at) VALUES(#{id},#{userId},#{templateId},#{parametersJson},#{imageUrl},#{version},#{createdAt})") void insertAvatar(Avatar a);
    @Delete("DELETE FROM avatars WHERE user_id=#{userId}") int deleteAvatars(String userId);

    @Select("<script>SELECT * FROM wardrobe_items WHERE user_id=#{userId}"+
      "<if test='category!=null and category!="+"\"\""+"'> AND category=#{category}</if>"+
      "<if test='season!=null and season!="+"\"\""+"'> AND season=#{season}</if>"+
      "<if test='color!=null and color!="+"\"\""+"'> AND color=#{color}</if>"+
      " ORDER BY created_at DESC LIMIT #{size} OFFSET #{offset}</script>")
    List<WardrobeItem> listWardrobe(@Param("userId") String userId,@Param("category") String category,@Param("season") String season,@Param("color") String color,@Param("size") int size,@Param("offset") int offset);
    @Select("SELECT * FROM wardrobe_items WHERE id=#{id}") WardrobeItem findWardrobeRaw(String id);
    @Select("SELECT * FROM wardrobe_items WHERE id=#{id} AND user_id=#{userId}") WardrobeItem findWardrobe(@Param("userId") String userId,@Param("id") String id);
    @Select("SELECT * FROM wardrobe_items WHERE user_id=#{userId} ORDER BY created_at") List<WardrobeItem> allWardrobe(String userId);
    @Insert("INSERT INTO wardrobe_items(id,user_id,name,category,color,season,warmth,formality,fit,item_length,description,image_url,mask_url,anchor_json,analysis_status,created_at,updated_at) VALUES(#{id},#{userId},#{name},#{category},#{color},#{season},#{warmth},#{formality},#{fit},#{itemLength},#{description},#{imageUrl},#{maskUrl},#{anchorJson},#{analysisStatus},#{createdAt},#{updatedAt})") void insertWardrobe(WardrobeItem w);
    @Update("UPDATE wardrobe_items SET name=#{name},category=#{category},color=#{color},season=#{season},warmth=#{warmth},formality=#{formality},fit=#{fit},item_length=#{itemLength},description=#{description},analysis_status=#{analysisStatus},updated_at=#{updatedAt} WHERE id=#{id} AND user_id=#{userId}") int updateWardrobe(WardrobeItem w);
    @Delete("DELETE FROM wardrobe_items WHERE id=#{id} AND user_id=#{userId}") int deleteWardrobe(@Param("userId") String userId,@Param("id") String id);

    @Insert("INSERT INTO recommendations(id,user_id,request_json,weather_json,status,created_at) VALUES(#{id},#{userId},#{requestJson},#{weatherJson},#{status},#{createdAt})") void insertRecommendation(Recommendation r);
    @Select("SELECT * FROM recommendations WHERE id=#{id} AND user_id=#{userId}") Recommendation findRecommendation(@Param("userId") String userId,@Param("id") String id);
    @Insert("INSERT INTO recommendation_outfits(id,recommendation_id,outfit_rank,score,reason,weather_tip,fit_tip,alternatives_json) VALUES(#{id},#{recommendationId},#{outfitRank},#{score},#{reason},#{weatherTip},#{fitTip},#{alternativesJson})") void insertOutfit(Outfit o);
    @Select("SELECT o.* FROM recommendation_outfits o JOIN recommendations r ON r.id=o.recommendation_id WHERE o.recommendation_id=#{recommendationId} AND r.user_id=#{userId} ORDER BY outfit_rank") List<Outfit> listOutfits(@Param("userId") String userId,@Param("recommendationId") String recommendationId);
    @Select("SELECT o.* FROM recommendation_outfits o JOIN recommendations r ON r.id=o.recommendation_id WHERE o.id=#{id} AND r.user_id=#{userId}") Outfit findOutfit(@Param("userId") String userId,@Param("id") String id);
    @Insert("INSERT INTO outfit_items(outfit_id,wardrobe_item_id,layer_order,role) VALUES(#{outfitId},#{wardrobeItemId},#{layerOrder},#{role})") void insertOutfitItem(OutfitItem i);
    @Select("SELECT * FROM outfit_items WHERE outfit_id=#{outfitId} ORDER BY layer_order") List<OutfitItem> listOutfitItems(String outfitId);

    @Insert("INSERT INTO try_on_results(id,user_id,avatar_id,outfit_id,preview_url,render_type,status,expires_at,created_at) VALUES(#{id},#{userId},#{avatarId},#{outfitId},#{previewUrl},#{renderType},#{status},#{expiresAt},#{createdAt})") void insertTryOn(TryOn t);
    @Select("SELECT * FROM try_on_results WHERE id=#{id} AND user_id=#{userId}") TryOn findTryOn(@Param("userId") String userId,@Param("id") String id);
    @Update("UPDATE try_on_results SET preview_url=#{previewUrl},status=#{status} WHERE id=#{id} AND user_id=#{userId}") int updateTryOn(TryOn t);
    @Delete("DELETE FROM try_on_results WHERE id=#{id} AND user_id=#{userId}") int deleteTryOn(@Param("userId") String userId,@Param("id") String id);

    @Insert("INSERT INTO favorites(id,user_id,outfit_id,outfit_snapshot_json,preview_url,created_at) VALUES(#{id},#{userId},#{outfitId},#{outfitSnapshotJson},#{previewUrl},#{createdAt})") void insertFavorite(Favorite f);
    @Select("SELECT * FROM favorites WHERE user_id=#{userId} ORDER BY created_at DESC") List<Favorite> listFavorites(String userId);
    @Select("SELECT * FROM favorites WHERE user_id=#{userId} AND outfit_id=#{outfitId}") Favorite findFavoriteByOutfit(@Param("userId")String userId,@Param("outfitId")String outfitId);
    @Delete("DELETE FROM favorites WHERE id=#{id} AND user_id=#{userId}") int deleteFavorite(@Param("userId") String userId,@Param("id") String id);
    @Insert("INSERT INTO feedback(id,user_id,recommendation_id,outfit_id,rating,reason_code,comment,details_json,created_at) VALUES(#{id},#{userId},#{recommendationId},#{outfitId},#{rating},#{reasonCode},#{comment},#{detailsJson},#{createdAt})") void insertFeedback(Feedback f);
    @Select("SELECT * FROM weather_cache WHERE cache_key=#{key} AND expires_at>CURRENT_TIMESTAMP") WeatherCache findWeatherCache(String key);
    @Delete("DELETE FROM weather_cache WHERE cache_key=#{key}") void deleteWeatherCache(String key);
    @Insert("INSERT INTO weather_cache(cache_key,grid_x,grid_y,forecast_at,payload_json,expires_at) VALUES(#{cacheKey},#{gridX},#{gridY},#{forecastAt},#{payloadJson},#{expiresAt})") void insertWeatherCache(WeatherCache c);
}
