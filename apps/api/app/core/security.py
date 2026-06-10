"""Password hashing + HMAC helpers shared by auth and sharing."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from passlib.context import CryptContext

# Argon2id is the OWASP-recommended password hasher.
_PWD_CTX = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plaintext: str) -> str:
    return _PWD_CTX.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    return _PWD_CTX.verify(plaintext, hashed)


def random_token(num_bytes: int = 32) -> str:
    """Return a URL-safe random token."""
    return secrets.token_urlsafe(num_bytes)


def hmac_sha256(secret: str, message: str) -> bytes:
    """Keyed HMAC used for stored share-token lookups (defense in depth).

    A leaked DB without the HMAC key is useless for replaying tokens.
    """
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()


def constant_time_equals(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)
