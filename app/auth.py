from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin
from app.security import decode_access_token, hash_password, verify_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def find_user(db: Session, identifier: str) -> User | None:
    normalized = identifier.strip().lower()
    return db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == normalized,
                func.lower(User.email) == normalized,
            )
        )
    )


def create_user(db: Session, user_data: UserCreate) -> User:
    """Validate uniqueness and persist a user with a bcrypt hash."""

    duplicate = db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == user_data.username.lower(),
                func.lower(User.email) == str(user_data.email).lower(),
            )
        )
    )
    if duplicate:
        raise ValueError("An account with that username or email already exists")

    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        username=user_data.username.lower(),
        email=str(user_data.email).lower(),
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, credentials: UserLogin) -> User | None:
    """Return an active user when the identifier and password are valid."""

    user = find_user(db, credentials.identifier)
    if (
        user is None
        or not user.is_active
        or not verify_password(credentials.password, user.password_hash)
    ):
        return None

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise credentials_error
    return user
