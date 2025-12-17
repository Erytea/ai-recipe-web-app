"""
Middleware для обработки flash сообщений
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from bot.web.flash_messages import get_flash_message


class FlashMessageMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления flash сообщений в контекст шаблонов"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Если это HTML ответ, добавляем flash сообщения в cookies для JavaScript
        # (они уже установлены в роутах через set_flash_message)
        return response


