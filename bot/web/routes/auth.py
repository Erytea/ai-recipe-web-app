"""
Роуты аутентификации
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Form, Response, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr

from bot.core.models import User
from bot.web.dependencies import (
    authenticate_user,
    get_password_hash,
    create_access_token,
    get_current_user_optional,
    get_user_by_email
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional)
):
    """Страница входа"""
    if current_user:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "title": "Вход"}
    )


@router.post("/login")
async def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    """Вход в систему"""
    user = await authenticate_user(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    # Создаем токен
    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    # Устанавливаем cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=24 * 60 * 60,  # 24 часа
        expires=24 * 60 * 60,
    )

    return RedirectResponse(url="/", status_code=302)


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional)
):
    """Страница регистрации"""
    if current_user:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request, "title": "Регистрация"}
    )


@router.post("/register")
async def register(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    username: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None)
):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь
    existing_user = await get_user_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )

    # Хэшируем пароль
    password_hash = get_password_hash(password)

    # Создаем пользователя
    user = await User.create(
        email=email,
        password_hash=password_hash,
        username=username,
        first_name=first_name,
        last_name=last_name
    )

    # Создаем токен и логиним
    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    # Устанавливаем cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=24 * 60 * 60,
        expires=24 * 60 * 60,
    )

    return RedirectResponse(url="/", status_code=302)


@router.post("/logout")
async def logout(response: Response):
    """Выход из системы"""
    response.delete_cookie(key="access_token")
    return RedirectResponse(url="/", status_code=302)


# API endpoints для мобильных приложений/SPA
@router.post("/api/login")
async def api_login(login_data: LoginRequest):
    """API вход в систему"""
    user = await authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/api/register")
async def api_register(register_data: RegisterRequest):
    """API регистрация"""
    # Проверяем, существует ли пользователь
    existing_user = await get_user_by_email(register_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )

    # Хэшируем пароль
    password_hash = get_password_hash(register_data.password)

    # Создаем пользователя
    user = await User.create(
        email=register_data.email,
        password_hash=password_hash,
        username=register_data.username,
        first_name=register_data.first_name,
        last_name=register_data.last_name
    )

    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

