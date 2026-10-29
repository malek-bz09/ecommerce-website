"""Password hashing and login tokens (JWT)."""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

# Argon2id with the library's recommended settings: deliberately slow and memory-hungry,
# so guessing passwords from a stolen hash is very expensive
password_hash = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"

# Checked when an email doesn't exist, so a wrong email takes as long as a wrong
# password and response times don't reveal which emails have accounts
DUMMY_HASH = password_hash.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(admin_id: int, role: str) -> tuple[str, int]:
    """Returns (token, seconds until it expires)."""
    settings = get_settings()
    now = datetime.now(UTC)
    lifetime = timedelta(minutes=settings.access_token_minutes)
    claims = {
        "sub": str(admin_id),  # who the token belongs to ("subject")
        "role": role,
        "iat": now,  # issued at
        "exp": now + lifetime,  # expires at; jwt.decode() rejects it afterwards
    }
    token = jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm=JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict | None:
    """The token's claims, or None if it is forged, damaged or expired."""
    try:
        return jwt.decode(
            token,
            get_settings().jwt_secret_key.get_secret_value(),
            # Only accept the algorithm we sign with: never let the token choose
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.InvalidTokenError:
        return None
