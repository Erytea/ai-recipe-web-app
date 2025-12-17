"""
Админ панель для управления приложением
"""

from fastapi import APIRouter, Depends, HTTPException, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
from tortoise.expressions import Q

from bot.core.models import User, Recipe, RecipeBase, MealPlan
from bot.web.dependencies import get_current_admin_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_admin: User = Depends(get_current_admin_user)
):
    """Главная страница админ панели"""

    # Статистика
    users_count = await User.all().count()
    recipes_count = await Recipe.all().count()
    recipes_base_count = await RecipeBase.all().count()
    meal_plans_count = await MealPlan.all().count()

    # Последние действия
    recent_users = await User.all().order_by("-created_at").limit(5)
    recent_recipes = await Recipe.all().order_by("-created_at").limit(5).prefetch_related("user")
    recent_meal_plans = await MealPlan.all().order_by("-created_at").limit(5).prefetch_related("user")

    context = {
        "request": request,
        "user": current_admin,
        "title": "Админ панель",
        "stats": {
            "users": users_count,
            "recipes": recipes_count,
            "recipes_base": recipes_base_count,
            "meal_plans": meal_plans_count
        },
        "recent_users": recent_users,
        "recent_recipes": recent_recipes,
        "recent_meal_plans": recent_meal_plans
    }

    return templates.TemplateResponse("admin/dashboard.html", context)


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    page: int = 1,
    search: str = ""
):
    """Управление пользователями"""

    limit = 20
    offset = (page - 1) * limit

    # Базовый запрос
    query = User.all()

    # Поиск
    if search:
        query = query.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    # Пагинация
    users = await query.offset(offset).limit(limit).order_by("-created_at")
    total_users = await query.count()
    total_pages = (total_users + limit - 1) // limit

    context = {
        "request": request,
        "user": current_admin,
        "title": "Управление пользователями",
        "users": users,
        "page": page,
        "total_pages": total_pages,
        "search": search
    }

    return templates.TemplateResponse("admin/users.html", context)


@router.post("/users/{user_id}/toggle-admin")
async def toggle_admin_status(
    request: Request,
    user_id: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """Переключение статуса администратора"""

    target_user = await User.get_or_none(id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Нельзя снять права админа с самого себя
    if str(target_user.id) == str(current_admin.id):
        raise HTTPException(status_code=400, detail="Нельзя изменить свои права")

    target_user.is_admin = not target_user.is_admin
    await target_user.save()

    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    request: Request,
    user_id: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """Переключение статуса активности пользователя"""

    target_user = await User.get_or_none(id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Нельзя деактивировать самого себя
    if str(target_user.id) == str(current_admin.id):
        raise HTTPException(status_code=400, detail="Нельзя деактивировать себя")

    target_user.is_active = not target_user.is_active
    await target_user.save()

    return RedirectResponse(url="/admin/users", status_code=302)


@router.get("/recipes", response_class=HTMLResponse)
async def admin_recipes(
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    page: int = 1,
    search: str = ""
):
    """Управление личными рецептами пользователей"""

    limit = 20
    offset = (page - 1) * limit

    # Базовый запрос с загрузкой пользователя
    query = Recipe.all().prefetch_related("user")

    # Поиск
    if search:
        query = query.filter(recipe_text__icontains=search)

    # Пагинация
    recipes = await query.offset(offset).limit(limit).order_by("-created_at")
    total_recipes = await query.count()
    total_pages = (total_recipes + limit - 1) // limit

    context = {
        "request": request,
        "user": current_admin,
        "title": "Управление рецептами",
        "recipes": recipes,
        "page": page,
        "total_pages": total_pages,
        "search": search
    }

    return templates.TemplateResponse("admin/recipes.html", context)


@router.get("/recipes-base", response_class=HTMLResponse)
async def admin_recipes_base(
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    page: int = 1,
    search: str = ""
):
    """Управление базой рецептов"""

    limit = 20
    offset = (page - 1) * limit

    # Базовый запрос
    query = RecipeBase.all()

    # Поиск
    if search:
        query = query.filter(
            Q(title__icontains=search) |
            Q(tags__icontains=search) |
            Q(ingredients__icontains=search)
        )

    # Пагинация
    recipes = await query.offset(offset).limit(limit).order_by("-created_at")
    total_recipes = await query.count()
    total_pages = (total_recipes + limit - 1) // limit

    context = {
        "request": request,
        "user": current_admin,
        "title": "Управление базой рецептов",
        "recipes": recipes,
        "page": page,
        "total_pages": total_pages,
        "search": search
    }

    return templates.TemplateResponse("admin/recipes_base.html", context)


@router.get("/meal-plans", response_class=HTMLResponse)
async def admin_meal_plans(
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    page: int = 1,
    search: str = ""
):
    """Управление планами питания"""

    limit = 20
    offset = (page - 1) * limit

    # Базовый запрос с загрузкой пользователя
    query = MealPlan.all().prefetch_related("user")

    # Поиск
    if search:
        query = query.filter(meal_plan_text__icontains=search)

    # Пагинация
    meal_plans = await query.offset(offset).limit(limit).order_by("-created_at")
    total_meal_plans = await query.count()
    total_pages = (total_meal_plans + limit - 1) // limit

    context = {
        "request": request,
        "user": current_admin,
        "title": "Управление планами питания",
        "meal_plans": meal_plans,
        "page": page,
        "total_pages": total_pages,
        "search": search
    }

    return templates.TemplateResponse("admin/meal_plans.html", context)


@router.get("/stats", response_class=HTMLResponse)
async def admin_stats(
    request: Request,
    current_admin: User = Depends(get_current_admin_user)
):
    """Статистика приложения"""

    # Подробная статистика
    stats = {
        "total_users": await User.all().count(),
        "active_users": await User.filter(is_active=True).count(),
        "admin_users": await User.filter(is_admin=True).count(),
        "total_recipes": await Recipe.all().count(),
        "total_recipes_base": await RecipeBase.all().count(),
        "total_meal_plans": await MealPlan.all().count(),
    }

    # Статистика за последний месяц (примерно)
    from datetime import datetime, timedelta
    month_ago = datetime.now() - timedelta(days=30)

    stats.update({
        "new_users_month": await User.filter(created_at__gte=month_ago).count(),
        "new_recipes_month": await Recipe.filter(created_at__gte=month_ago).count(),
        "new_meal_plans_month": await MealPlan.filter(created_at__gte=month_ago).count(),
    })

    context = {
        "request": request,
        "user": current_admin,
        "title": "Статистика",
        "stats": stats
    }

    return templates.TemplateResponse("admin/stats.html", context)
