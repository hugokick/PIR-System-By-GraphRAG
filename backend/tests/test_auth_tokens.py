import json

from app.services.auth import DEMO_USERS, issue_access_token, verify_access_token


def token_payload(token: str) -> dict:
    encoded_payload, _ = token.split(".")
    padding = "=" * (-len(encoded_payload) % 4)
    import base64

    return json.loads(base64.urlsafe_b64decode(encoded_payload + padding).decode())


def test_access_token_includes_expiration(monkeypatch):
    monkeypatch.setenv("AUTH_TOKEN_TTL_SECONDS", "120")

    token = issue_access_token(DEMO_USERS["editor"], now=1_700_000_000)

    assert token_payload(token)["exp"] == 1_700_000_120


def test_verify_access_token_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("AUTH_TOKEN_TTL_SECONDS", "60")
    token = issue_access_token(DEMO_USERS["viewer"], now=1_700_000_000)

    assert verify_access_token(token, now=1_700_000_059) == DEMO_USERS["viewer"]
    assert verify_access_token(token, now=1_700_000_060) is None


def test_invalid_auth_token_ttl_falls_back_to_demo_default(monkeypatch):
    monkeypatch.setenv("AUTH_TOKEN_TTL_SECONDS", "not-a-number")

    token = issue_access_token(DEMO_USERS["admin"], now=1_700_000_000)

    assert token_payload(token)["exp"] == 1_700_028_800
