"""
CSRF защита для форм
"""

import secrets
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from typing import Optional


def generate_csrf_token() -> str:
    """Генерирует случайный CSRF токен"""
    return secrets.token_urlsafe(32)


def get_csrf_token(request: Request) -> Optional[str]:
    """Получает CSRF токен из cookie"""
    return request.cookies.get("csrf_token")


def set_csrf_token(response: Response, token: str):
    """Устанавливает CSRF токен в cookie"""
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=True,
        secure=False,  # Для разработки, в продакшене должно быть True
        samesite="lax",
        max_age=3600 * 24,  # 24 часа
        path="/"
    )


def validate_csrf_token(request: Request, token: Optional[str] = None) -> bool:
    """
    Проверяет CSRF токен
    
    Args:
        request: Request объект
        token: Токен из формы (если None, берется из заголовка X-CSRF-Token)
    
    Returns:
        True если токен валиден, False иначе
    """
    # Получаем токен из cookie
    cookie_token = get_csrf_token(request)
    if not cookie_token:
        return False
    
    # Получаем токен из формы или заголовка
    if token is None:
        # Пробуем получить из заголовка
        token = request.headers.get("X-CSRF-Token")
        if not token:
            # Пробуем получить из формы
            form_data = request.form()
            if hasattr(form_data, 'get'):
                token = form_data.get("csrf_token")
    
    if not token:
        return False
    
    # Сравниваем токены
    return secrets.compare_digest(cookie_token, token)


def require_csrf_token(request: Request, token: Optional[str] = None):
    """
    Проверяет CSRF токен и выбрасывает исключение если невалиден
    
    Args:
        request: Request объект
        token: Токен из формы
    
    Raises:
        HTTPException: Если токен невалиден
    """
    if not validate_csrf_token(request, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token"
        )

