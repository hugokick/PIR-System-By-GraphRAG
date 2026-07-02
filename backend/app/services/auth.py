import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class DemoUser:
    username: str
    password: str
    role: str
    display_name: str


DEMO_USERS = {
    "admin": DemoUser("admin", "admin123", "admin", "管理员"),
    "editor": DemoUser("editor", "editor123", "editor", "编辑员"),
    "viewer": DemoUser("viewer", "viewer123", "viewer", "只读访客"),
}


def authenticate_demo_user(username: str, password: str) -> DemoUser | None:
    user = DEMO_USERS.get(username.strip().lower())
    if user is None:
        return None
    if not hmac.compare_digest(user.password, password):
        return None
    return user


default_token_ttl_seconds = 8 * 60 * 60


def issue_access_token(user: DemoUser, *, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = {
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
        "exp": issued_at + token_ttl_seconds(),
    }
    encoded_payload = _urlsafe_b64encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def verify_access_token(token: str, *, now: int | None = None) -> DemoUser | None:
    parts = token.split(".")
    if len(parts) != 2:
        return None
    encoded_payload, signature = parts
    if not hmac.compare_digest(_sign(encoded_payload), signature):
        return None
    try:
        payload = json.loads(_urlsafe_b64decode(encoded_payload).decode())
    except (ValueError, UnicodeDecodeError):
        return None
    try:
        expires_at = int(payload.get("exp"))
    except (TypeError, ValueError):
        return None
    current_time = int(time.time() if now is None else now)
    if current_time >= expires_at:
        return None
    username = str(payload.get("username", ""))
    role = str(payload.get("role", ""))
    user = DEMO_USERS.get(username)
    if user is None or user.role != role:
        return None
    return user


def _sign(payload: str) -> str:
    digest = hmac.new(_token_secret(), payload.encode(), hashlib.sha256).digest()
    return _urlsafe_b64encode(digest)


def _token_secret() -> bytes:
    return os.environ.get("AUTH_TOKEN_SECRET", "exhibit-atlas-demo-secret").encode()


def token_ttl_seconds() -> int:
    try:
        ttl = int(os.environ.get("AUTH_TOKEN_TTL_SECONDS", str(default_token_ttl_seconds)))
    except ValueError:
        return default_token_ttl_seconds
    if ttl <= 0:
        return default_token_ttl_seconds
    return ttl


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
