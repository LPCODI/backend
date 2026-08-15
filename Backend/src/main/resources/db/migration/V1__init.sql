CREATE TABLE users (
  id VARCHAR(36) PRIMARY KEY, email VARCHAR(190) NOT NULL UNIQUE, password_hash VARCHAR(100) NOT NULL,
  nickname VARCHAR(60) NOT NULL, personal_color VARCHAR(40), style_preference VARCHAR(100),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TIMESTAMP NULL
);
CREATE TABLE refresh_tokens (
  id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, token_hash VARCHAR(64) NOT NULL UNIQUE,
  expires_at TIMESTAMP NOT NULL, revoked_at TIMESTAMP NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE body_profiles (
  user_id VARCHAR(36) PRIMARY KEY, height_cm INT NOT NULL, body_type VARCHAR(40) NOT NULL,
  gender_expression VARCHAR(40) NOT NULL, consent_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE avatars (
  id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, template_id VARCHAR(40) NOT NULL,
  parameters_json TEXT NOT NULL, image_url VARCHAR(500) NOT NULL, version INT NOT NULL, created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE wardrobe_items (
  id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, name VARCHAR(100) NOT NULL,
  category VARCHAR(30) NOT NULL, color VARCHAR(40), season VARCHAR(30), warmth INT,
  formality VARCHAR(30), fit VARCHAR(30), item_length VARCHAR(30), description VARCHAR(500),
  image_url VARCHAR(500) NOT NULL, mask_url VARCHAR(500), anchor_json TEXT, analysis_status VARCHAR(20) NOT NULL,
  created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE recommendations (
  id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, request_json TEXT NOT NULL,
  weather_json TEXT, status VARCHAR(20) NOT NULL, created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE recommendation_outfits (
  id VARCHAR(36) PRIMARY KEY, recommendation_id VARCHAR(36) NOT NULL, outfit_rank INT NOT NULL,
  score INT NOT NULL, reason VARCHAR(1000), weather_tip VARCHAR(500), fit_tip VARCHAR(500), alternatives_json TEXT,
  FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE CASCADE
);
CREATE TABLE outfit_items (
  outfit_id VARCHAR(36) NOT NULL, wardrobe_item_id VARCHAR(36) NOT NULL, layer_order INT NOT NULL, role VARCHAR(30) NOT NULL,
  PRIMARY KEY(outfit_id, wardrobe_item_id),
  FOREIGN KEY (outfit_id) REFERENCES recommendation_outfits(id) ON DELETE CASCADE,
  FOREIGN KEY (wardrobe_item_id) REFERENCES wardrobe_items(id) ON DELETE CASCADE
);
CREATE TABLE try_on_results (
  id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, avatar_id VARCHAR(36) NOT NULL,
  outfit_id VARCHAR(36) NOT NULL, preview_url VARCHAR(500), render_type VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL, expires_at TIMESTAMP, created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (avatar_id) REFERENCES avatars(id) ON DELETE CASCADE,
  FOREIGN KEY (outfit_id) REFERENCES recommendation_outfits(id) ON DELETE CASCADE
);
CREATE TABLE favorites (
  id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, outfit_id VARCHAR(36) NOT NULL,
  outfit_snapshot_json TEXT NOT NULL, preview_url VARCHAR(500), created_at TIMESTAMP NOT NULL,
  UNIQUE(user_id, outfit_id), FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (outfit_id) REFERENCES recommendation_outfits(id) ON DELETE CASCADE
);
CREATE TABLE feedback (
  id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, recommendation_id VARCHAR(36), outfit_id VARCHAR(36),
  rating VARCHAR(20) NOT NULL, reason_code VARCHAR(30), comment VARCHAR(500), details_json TEXT, created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE weather_cache (
  cache_key VARCHAR(120) PRIMARY KEY, grid_x INT NOT NULL, grid_y INT NOT NULL,
  forecast_at TIMESTAMP NOT NULL, payload_json TEXT NOT NULL, expires_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_wardrobe_user ON wardrobe_items(user_id);
CREATE INDEX idx_recommendation_user ON recommendations(user_id);
CREATE INDEX idx_tryon_user ON try_on_results(user_id);

