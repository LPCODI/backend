"""Password hashing and verification helpers for account authentication."""

from __future__ import annotations

from hashlib import sha256

import bcrypt

PASSWORD_HASH_SCHEME = "bcrypt_sha256"
PASSWORD_HASH_VERSION = "v1"
PASSWORD_HASH_PREFIX = f"{PASSWORD_HASH_SCHEME}${PASSWORD_HASH_VERSION}$"
PASSWORD_HASH_ROUNDS = 12


def _password_digest(plain_password: str) -> bytes:
    """Return a fixed-length digest so bcrypt never truncates long passwords."""

    return sha256(plain_password.encode("utf-8")).digest()


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password for storage in the users.password_hash column."""

    password_hash = bcrypt.hashpw(
        _password_digest(plain_password),
        bcrypt.gensalt(rounds=PASSWORD_HASH_ROUNDS),
    ).decode("ascii")
    return f"{PASSWORD_HASH_PREFIX}{password_hash}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return whether a plain-text password matches a stored password hash."""

    if not password_hash.startswith(PASSWORD_HASH_PREFIX):
        return False

    encoded_hash = password_hash.removeprefix(PASSWORD_HASH_PREFIX).encode("ascii")
    try:
        return bcrypt.checkpw(_password_digest(plain_password), encoded_hash)
    except ValueError:
        return False


__all__ = [
    "PASSWORD_HASH_PREFIX",
    "PASSWORD_HASH_ROUNDS",
    "PASSWORD_HASH_SCHEME",
    "PASSWORD_HASH_VERSION",
    "hash_password",
    "verify_password",
]
