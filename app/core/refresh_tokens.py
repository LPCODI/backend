"""Opaque refresh token generation and hashing helpers."""

from __future__ import annotations

from hashlib import sha256
from secrets import token_urlsafe

REFRESH_TOKEN_BYTES = 48
REFRESH_TOKEN_HASH_LENGTH = 64


def generate_refresh_token() -> str:
    """Create a high-entropy opaque refresh token for one-time client delivery."""

    return token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(refresh_token: str) -> str:
    """Return the stable database hash for a raw refresh token."""

    if not refresh_token:
        raise ValueError("refresh_token must not be empty")
    return sha256(refresh_token.encode("utf-8")).hexdigest()


__all__ = [
    "REFRESH_TOKEN_BYTES",
    "REFRESH_TOKEN_HASH_LENGTH",
    "generate_refresh_token",
    "hash_refresh_token",
]
