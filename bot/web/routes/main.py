"""
Основные роуты веб-приложения
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bot.core.models import User
from bot.web.dependencies import get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/about", response_class=HTMLResponse)
async def about(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional)
):
    """Страница "О приложении" """
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "user": current_user,
            "title": "О приложении"
        }
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """Профиль пользователя"""
    if not current_user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login", status_code=302)

    # Получаем статистику пользователя
    recipes_count = await current_user.recipes.all().count()
    meal_plans_count = await current_user.meal_plans.all().count()

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": current_user,
            "title": "Профиль",
            "recipes_count": recipes_count,
            "meal_plans_count": meal_plans_count
        }
    )


