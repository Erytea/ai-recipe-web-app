"""
Утилиты для flash сообщений (временных уведомлений пользователю)
"""

from fastapi import Response, Request
from typing import Optional


def set_flash_message(response: Response, message: str, message_type: str = "success"):
    """
    Устанавливает flash сообщение в cookie
    
    Args:
        response: Response объект FastAPI
        message: Текст сообщения
        message_type: Тип сообщения (success, error, warning, info)
    """
    response.set_cookie(
        key="flash_message",
        value=message,
        max_age=5,  # 5 секунд
        httponly=False,  # Нужно читать в JavaScript
        path="/"
    )
    response.set_cookie(
        key="flash_type",
        value=message_type,
        max_age=5,
        httponly=False,
        path="/"
    )


def get_flash_message(request: Request) -> Optional[tuple[str, str]]:
    """
    Получает flash сообщение из cookie
    
    Args:
        request: Request объект FastAPI
        
    Returns:
        Tuple (message, type) или None
    """
    message = request.cookies.get("flash_message")
    message_type = request.cookies.get("flash_type", "success")
    if message:
        return (message, message_type)
    return None


def clear_flash_message(response: Response):
    """Удаляет flash сообщения из cookie"""
    response.delete_cookie(key="flash_message", path="/")
    response.delete_cookie(key="flash_type", path="/")


