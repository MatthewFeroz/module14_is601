import pytest
from pydantic import ValidationError

from app.schemas import UserCreate, UserLogin


def valid_registration(**overrides):
    data = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "username": "ada_l",
        "email": "ada@example.com",
        "password": "CipherPass13!",
        "confirm_password": "CipherPass13!",
    }
    data.update(overrides)
    return data


def test_registration_schema_normalizes_username():
    user = UserCreate(**valid_registration(username="  ADA_L  "))

    assert user.username == "ada_l"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("email", "not-an-email", "valid email"),
        ("username", "bad username", "Username may contain"),
        ("password", "short", "at least 8"),
        ("password", "alllowercase13!", "uppercase"),
        ("password", "ALLUPPERCASE13!", "lowercase"),
        ("password", "NoNumberHere!", "number"),
        ("password", "NoSpecial13", "special"),
        ("confirm_password", "DifferentPass13!", "Passwords do not match"),
    ],
)
def test_registration_schema_rejects_invalid_input(field, value, message):
    data = valid_registration(**{field: value})
    if field == "password" and value != "short":
        data["confirm_password"] = value

    with pytest.raises(ValidationError, match=message):
        UserCreate(**data)


def test_login_accepts_email_or_username_keys():
    by_email = UserLogin(email="ada@example.com", password="CipherPass13!")
    by_username = UserLogin(username="ada_l", password="CipherPass13!")

    assert by_email.identifier == "ada@example.com"
    assert by_username.identifier == "ada_l"
