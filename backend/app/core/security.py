"""Password hashing (Argon2 via pwdlib) and JWT session tokens (PyJWT)."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response
from pwdlib import PasswordHash

from app.core.config import get_settings

_hasher = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password, password_hash)
    except Exception:
        return False


def create_token(user_id: int, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def _cookie_kwargs() -> dict:
    s = get_settings()
    return {"httponly": True, "samesite": "lax", "secure": s.cookie_secure, "path": "/"}


def set_session_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(s.cookie_name, token, max_age=s.jwt_expire_hours * 3600, **_cookie_kwargs())


def clear_session_cookie(response: Response) -> None:
    # Must use the same attributes as set_session_cookie, or browsers keep the cookie.
    response.delete_cookie(get_settings().cookie_name, **_cookie_kwargs())
