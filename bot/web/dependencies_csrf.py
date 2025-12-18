"""
Dependency для автоматического добавления CSRF токена в контекст шаблонов
"""

from fastapi import Request, Response
from bot.web.csrf import get_csrf_token, generate_csrf_token, set_csrf_token


async def add_csrf_to_context(request: Request, response: Response = None) -> dict:
    """
    Добавляет CSRF токен в контекст для шаблонов
    
    Args:
        request: Request объект
        response: Response объект (опционально, для установки cookie)
    
    Returns:
        Словарь с csrf_token для добавления в context
    """
    csrf_token = get_csrf_token(request)
    if not csrf_token:
        csrf_token = generate_csrf_token()
        if response:
            set_csrf_token(response, csrf_token)
    
    return {"csrf_token": csrf_token}



