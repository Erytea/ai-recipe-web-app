"""
Основные роуты веб-приложения
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bot.web.flash_messages import get_flash_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """Страница "О приложении" """
    context = {
        "request": request,
        "title": "О приложении"
    }

    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]

    return templates.TemplateResponse("about.html", context)



