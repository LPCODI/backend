package com.clothcodi.ai;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(properties = {
	"spring.profiles.active=test",
	"spring.datasource.url=jdbc:h2:mem:codi-ai-test;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
	"spring.datasource.username=sa",
	"spring.datasource.password=",
	"spring.datasource.driver-class-name=org.h2.Driver",
	"app.storage-provider=local",
	"app.storage-dir=./target/test-uploads"
})
class AiApplicationTests {

	@Test
	void contextLoads() {
	}

}
