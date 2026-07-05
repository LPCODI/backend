import unittest

from app.core import PASSWORD_HASH_PREFIX, hash_password, verify_password


class PasswordHashingTest(unittest.TestCase):
    def test_hash_password_uses_versioned_bcrypt_sha256_format(self) -> None:
        password_hash = hash_password("correct horse battery staple")

        self.assertTrue(password_hash.startswith(PASSWORD_HASH_PREFIX))
        self.assertIn("$2b$12$", password_hash)
        self.assertLessEqual(len(password_hash), 255)
        self.assertNotIn("correct horse battery staple", password_hash)

    def test_hash_password_uses_unique_salt_for_same_password(self) -> None:
        first_hash = hash_password("same-password")
        second_hash = hash_password("same-password")

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(verify_password("same-password", first_hash))
        self.assertTrue(verify_password("same-password", second_hash))

    def test_verify_password_rejects_wrong_password_and_unknown_hash_format(self) -> None:
        password_hash = hash_password("right-password")

        self.assertFalse(verify_password("wrong-password", password_hash))
        self.assertFalse(verify_password("right-password", "$2b$12$unknown-format"))
        self.assertFalse(verify_password("right-password", "bcrypt_sha256$v1$not-a-bcrypt-hash"))

    def test_verify_password_supports_long_unicode_passwords_without_truncation(self) -> None:
        long_password = "발표연습" * 30
        password_hash = hash_password(long_password)

        self.assertTrue(verify_password(long_password, password_hash))
        self.assertFalse(verify_password(f"{long_password}x", password_hash))


if __name__ == "__main__":
    unittest.main()
