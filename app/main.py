"""FastAPI application for JWT-secured calculation BREAD operations."""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_user, get_current_user
from app.calculations import Calculation
from app.database import Base, engine, get_db
from app.insights import build_user_insights
from app.models import User
from app.schemas import (
    CalculationCreate,
    CalculationInsights,
    CalculationRead,
    CalculationUpdate,
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
    description="Module 14 JWT-secured calculation BREAD application",
    version="14.0.0",
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


@app.get(
    "/dashboard/view/{calculation_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def calculation_detail_page(request: Request, calculation_id: str):
    return templates.TemplateResponse(
        request,
        "view_calculation.html",
        {"calculation_id": calculation_id},
    )


@app.get(
    "/dashboard/edit/{calculation_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def calculation_edit_page(request: Request, calculation_id: str):
    return templates.TemplateResponse(
        request,
        "edit_calculation.html",
        {"calculation_id": calculation_id},
    )


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


def owned_calculation(
    calculation_id: str,
    current_user: User,
    db: Session,
) -> Calculation:
    try:
        canonical_id = str(UUID(calculation_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calculation ID format",
        ) from exc

    calculation = db.scalar(
        select(Calculation).where(
            Calculation.id == canonical_id,
            Calculation.user_id == current_user.id,
        )
    )
    if calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found",
        )
    return calculation


@app.post(
    "/calculations",
    response_model=CalculationRead,
    status_code=status.HTTP_201_CREATED,
    tags=["calculations"],
)
def add_calculation(
    payload: CalculationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calculation = Calculation.create(
        payload.type.value,
        current_user.id,
        payload.inputs,
    )
    db.add(calculation)
    db.commit()
    db.refresh(calculation)
    return calculation


@app.get(
    "/calculations",
    response_model=list[CalculationRead],
    tags=["calculations"],
)
def browse_calculations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Calculation)
        .where(Calculation.user_id == current_user.id)
        .order_by(Calculation.created_at)
    ).all()


@app.get(
    "/insights",
    response_model=CalculationInsights,
    tags=["calculations"],
)
def calculation_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_user_insights(db, current_user.id)


@app.get(
    "/calculations/{calculation_id}",
    response_model=CalculationRead,
    tags=["calculations"],
)
def read_calculation(
    calculation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return owned_calculation(calculation_id, current_user, db)


@app.put(
    "/calculations/{calculation_id}",
    response_model=CalculationRead,
    tags=["calculations"],
)
def edit_calculation(
    calculation_id: str,
    payload: CalculationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calculation = owned_calculation(calculation_id, current_user, db)
    try:
        calculation.replace_inputs(payload.inputs)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    db.commit()
    db.refresh(calculation)
    return calculation


@app.delete(
    "/calculations/{calculation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["calculations"],
)
def delete_calculation(
    calculation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calculation = owned_calculation(calculation_id, current_user, db)
    db.delete(calculation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
