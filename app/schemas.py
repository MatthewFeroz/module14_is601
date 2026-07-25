import re
from datetime import datetime

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
SPECIAL_CHARACTERS = set("!@#$%^&*()_+-=[]{}|;:,.<>?")


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    confirm_password: str = Field(min_length=8, max_length=72)

    model_config = ConfigDict(extra="forbid")

    @field_validator("first_name", "last_name", "username")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError(
                "Username may contain only letters, numbers, dots, dashes, and underscores"
            )
        return value.lower()

    @model_validator(mode="after")
    def validate_passwords(self) -> "UserCreate":
        password = self.password
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 bytes")
        if not any(character.isupper() for character in password):
            raise ValueError("Password must contain an uppercase letter")
        if not any(character.islower() for character in password):
            raise ValueError("Password must contain a lowercase letter")
        if not any(character.isdigit() for character in password):
            raise ValueError("Password must contain a number")
        if not any(character in SPECIAL_CHARACTERS for character in password):
            raise ValueError("Password must contain a special character")
        if password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserLogin(BaseModel):
    identifier: str = Field(
        min_length=3,
        max_length=254,
        validation_alias=AliasChoices("identifier", "email", "username"),
    )
    password: str = Field(min_length=8, max_length=72)

    model_config = ConfigDict(extra="forbid")

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip().lower()


class UserRead(BaseModel):
    id: str
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegistrationResponse(BaseModel):
    message: str
    user: UserRead


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserRead
