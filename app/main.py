from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_user, get_current_user
from app.database import Base, engine, get_db
from app.models import User
from app.schemas import (
    RegistrationResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.security import create_access_token


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Cipher Calculations",
    description="Module 13 JWT registration and login application",
    version="13.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}


@app.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["authentication"],
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        user = create_user(db, user_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with that username or email already exists",
        ) from exc

    return RegistrationResponse(
        message="Registration successful",
        user=UserRead.model_validate(user),
    )


@app.post(
    "/login",
    response_model=TokenResponse,
    tags=["authentication"],
)
def login_user(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email, username, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, expires_at = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=UserRead.model_validate(user),
    )


@app.get(
    "/auth/me",
    response_model=UserRead,
    tags=["authentication"],
)
def current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
