"""Password hashing and admin sessions."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

ITERATIONS = 600_000
SESSION_LENGTH = timedelta(hours=8)


def hash_password(password: str) -> str:
    # Never store the password itself: store a salted, slow hash of it
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    _, iterations, salt, expected = stored.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)


# Checked when the username doesn't exist, so a wrong username takes as long as a
# wrong password and response times don't reveal which usernames are real
DUMMY_HASH = hash_password(secrets.token_hex(16))


def new_session(db, username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(UTC) + SESSION_LENGTH).isoformat()
    with db.transaction():
        db.execute("DELETE FROM sessions WHERE expires_at < %s", (now(),))
        db.execute(
            "INSERT INTO sessions (token, username, expires_at) VALUES (%s, %s, %s)",
            (token, username, expires_at),
        )
    return token


def now() -> str:
    return datetime.now(UTC).isoformat()
