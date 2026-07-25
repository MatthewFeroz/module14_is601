from datetime import timedelta

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_is_salted_hashed_and_verifiable():
    password = "CipherPass13!"
    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != password
    assert first_hash != second_hash
    assert verify_password(password, first_hash)
    assert not verify_password("WrongPass13!", first_hash)


def test_access_token_contains_user_subject():
    token, expires_at = create_access_token("user-123")
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert int(expires_at.timestamp()) == payload["exp"]


def test_expired_and_malformed_tokens_are_rejected():
    expired, _ = create_access_token(
        "user-123",
        expires_delta=timedelta(seconds=-1),
    )

    assert decode_access_token(expired) is None
    assert decode_access_token("not-a-jwt") is None
