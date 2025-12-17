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
from bot.core.config import settings
from bot.web.dependencies import (
    authenticate_user,
    get_password_hash,
    create_access_token,
    get_current_user_optional,
    get_user_by_email
)
from bot.web.flash_messages import set_flash_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional)
):
    """Страница входа"""
    if current_user:
        return RedirectResponse(url="/", status_code=302)

    from bot.web.flash_messages import get_flash_message
    from bot.web.csrf import get_csrf_token, generate_csrf_token, set_csrf_token
    
    context = {"request": request, "title": "Вход"}
    
    # Получаем или генерируем CSRF токен
    csrf_token = get_csrf_token(request)
    if not csrf_token:
        csrf_token = generate_csrf_token()
    context["csrf_token"] = csrf_token
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]

    response = templates.TemplateResponse("auth/login.html", context)
    
    # Устанавливаем CSRF токен в cookie если его нет
    if not get_csrf_token(request):
        set_csrf_token(response, csrf_token)
    
    return response


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(None)
):
    """Вход в систему"""
    from bot.web.csrf import require_csrf_token
    
    # Проверка CSRF токена
    require_csrf_token(request, csrf_token)
    
    user = await authenticate_user(email, password)
    if not user:
        response = RedirectResponse(url="/auth/login", status_code=302)
        set_flash_message(response, "Неверный email или пароль", "error")
        return response

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
        secure=not settings.debug,  # HTTPS только в продакшене
        samesite="lax",  # Защита от CSRF
        max_age=24 * 60 * 60,  # 24 часа
    )
    
    set_flash_message(response, f"Добро пожаловать, {user.email}!", "success")

    return RedirectResponse(url="/", status_code=302)


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional)
):
    """Страница регистрации"""
    if current_user:
        return RedirectResponse(url="/", status_code=302)

    from bot.web.flash_messages import get_flash_message
    from bot.web.csrf import get_csrf_token, generate_csrf_token, set_csrf_token
    
    context = {"request": request, "title": "Регистрация"}
    
    # Получаем или генерируем CSRF токен
    csrf_token = get_csrf_token(request)
    if not csrf_token:
        csrf_token = generate_csrf_token()
    context["csrf_token"] = csrf_token
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]

    response = templates.TemplateResponse("auth/register.html", context)
    
    # Устанавливаем CSRF токен в cookie если его нет
    if not get_csrf_token(request):
        set_csrf_token(response, csrf_token)
    
    return response


def validate_password(password: str) -> tuple[bool, str]:
    """Проверяет пароль и возвращает (валиден, сообщение об ошибке)"""
    import re
    
    if len(password) < 8:
        return False, "Пароль должен быть не менее 8 символов"
    
    if len(password) > 128:
        return False, "Пароль слишком длинный (максимум 128 символов)"
    
    # Требуем буквы и цифры
    if not re.search(r'[A-Za-z]', password):
        return False, "Пароль должен содержать хотя бы одну букву"
    
    if not re.search(r'[0-9]', password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    
    return True, ""


@router.post("/register")
async def register(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    username: str = Form(...),
    csrf_token: str = Form(None)
):
    """Регистрация нового пользователя"""
    from bot.web.csrf import require_csrf_token
    
    # Проверка CSRF токена
    require_csrf_token(request, csrf_token)
    
    # Валидация пароля
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        response = RedirectResponse(url="/auth/register", status_code=302)
        set_flash_message(response, error_msg, "error")
        return response
    
    # Валидация username
    username = username.strip()
    if not username:
        response = RedirectResponse(url="/auth/register", status_code=302)
        set_flash_message(response, "Имя пользователя не может быть пустым", "error")
        return response
    
    # Проверяем, существует ли пользователь с таким email
    existing_user = await get_user_by_email(email)
    if existing_user:
        response = RedirectResponse(url="/auth/register", status_code=302)
        set_flash_message(response, "Пользователь с таким email уже существует", "error")
        return response
    
    # Проверяем, существует ли пользователь с таким username
    existing_username = await User.get_or_none(username=username)
    if existing_username:
        response = RedirectResponse(url="/auth/register", status_code=302)
        set_flash_message(response, "Пользователь с таким именем уже существует", "error")
        return response

    try:
        # Хэшируем пароль
        password_hash = get_password_hash(password)

        # Создаем пользователя
        user = await User.create(
            email=email,
            password_hash=password_hash,
            username=username
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
            secure=not settings.debug,  # HTTPS только в продакшене
            samesite="lax",  # Защита от CSRF
            max_age=24 * 60 * 60,
        )
        
        set_flash_message(response, "Регистрация успешна! Добро пожаловать!", "success")

        return RedirectResponse(url="/", status_code=302)
    except Exception as e:
        response = RedirectResponse(url="/auth/register", status_code=302)
        set_flash_message(response, f"Ошибка при регистрации: {str(e)}", "error")
        return response


@router.post("/logout")
async def logout(response: Response):
    """Выход из системы"""
    response.delete_cookie(key="access_token")
    set_flash_message(response, "Вы успешно вышли из системы", "info")
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
    # Валидация username
    username = register_data.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя пользователя не может быть пустым"
        )
    
    # Проверяем, существует ли пользователь с таким email
    existing_user = await get_user_by_email(register_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    # Проверяем, существует ли пользователь с таким username
    existing_username = await User.get_or_none(username=username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )

    # Валидация пароля
    is_valid, error_msg = validate_password(register_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Хэшируем пароль
    password_hash = get_password_hash(register_data.password)

    # Создаем пользователя
    user = await User.create(
        email=register_data.email,
        password_hash=password_hash,
        username=username
    )

    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}



