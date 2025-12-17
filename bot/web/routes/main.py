"""
Основные роуты веб-приложения
"""

from fastapi import APIRouter, Request, Response, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bot.core.models import User
from bot.web.dependencies import (
    get_current_user_optional,
    get_current_user,
    get_password_hash,
    verify_password,
    get_user_by_email
)
from bot.web.flash_messages import get_flash_message, set_flash_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/about", response_class=HTMLResponse)
async def about(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional)
):
    """Страница "О приложении" """
    context = {
        "request": request,
        "user": current_user,
        "title": "О приложении"
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("about.html", context)


@router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """Профиль пользователя"""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Получаем статистику пользователя
    recipes_count = await current_user.recipes.all().count()
    meal_plans_count = await current_user.meal_plans.all().count()

    context = {
        "request": request,
        "user": current_user,
        "title": "Профиль",
        "recipes_count": recipes_count,
        "meal_plans_count": meal_plans_count
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]

    return templates.TemplateResponse("profile.html", context)


@router.get("/profile/edit", response_class=HTMLResponse)
async def profile_edit_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница редактирования профиля"""
    from bot.web.csrf import get_csrf_token, generate_csrf_token, set_csrf_token
    
    context = {
        "request": request,
        "user": current_user,
        "title": "Редактировать профиль"
    }
    
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
    
    response = templates.TemplateResponse("profile/edit.html", context)
    
    # Устанавливаем CSRF токен в cookie если его нет
    if not get_csrf_token(request):
        set_csrf_token(response, csrf_token)
    
    return response


@router.post("/profile/edit")
async def profile_edit(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    email: str = Form(...),
    username: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None),
    csrf_token: str = Form(None)
):
    """Обновление данных профиля"""
    from bot.web.csrf import require_csrf_token
    
    # Проверка CSRF токена
    require_csrf_token(request, csrf_token)
    
    try:
        # Проверка, что email не занят другим пользователем
        if email and email != current_user.email:
            existing = await get_user_by_email(email)
            if existing:
                set_flash_message(response, "Email уже используется другим пользователем", "error")
                return RedirectResponse(url="/profile/edit", status_code=302)
            current_user.email = email
        
        if username:
            current_user.username = username
        if first_name:
            current_user.first_name = first_name
        if last_name:
            current_user.last_name = last_name
        
        await current_user.save()
        set_flash_message(response, "Профиль успешно обновлен", "success")
        
        return RedirectResponse(url="/profile", status_code=302)
    except Exception as e:
        set_flash_message(response, f"Ошибка при обновлении профиля: {str(e)}", "error")
        return RedirectResponse(url="/profile/edit", status_code=302)


@router.get("/profile/change-password", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница смены пароля"""
    from bot.web.csrf import get_csrf_token, generate_csrf_token, set_csrf_token
    
    context = {
        "request": request,
        "user": current_user,
        "title": "Сменить пароль"
    }
    
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
    
    response = templates.TemplateResponse("profile/change_password.html", context)
    
    # Устанавливаем CSRF токен в cookie если его нет
    if not get_csrf_token(request):
        set_csrf_token(response, csrf_token)
    
    return response


@router.post("/profile/change-password")
async def change_password(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(None)
):
    """Смена пароля"""
    from bot.web.csrf import require_csrf_token
    
    # Проверка CSRF токена
    require_csrf_token(request, csrf_token)
    
    # Проверка старого пароля
    if not verify_password(old_password, current_user.password_hash):
        set_flash_message(response, "Неверный текущий пароль", "error")
        return RedirectResponse(url="/profile/change-password", status_code=302)
    
    # Проверка совпадения новых паролей
    if new_password != confirm_password:
        set_flash_message(response, "Новые пароли не совпадают", "error")
        return RedirectResponse(url="/profile/change-password", status_code=302)
    
    # Проверка минимальной длины пароля
    if len(new_password) < 8:
        set_flash_message(response, "Пароль должен быть не менее 8 символов", "error")
        return RedirectResponse(url="/profile/change-password", status_code=302)
    
    try:
        # Обновление пароля
        current_user.password_hash = get_password_hash(new_password)
        await current_user.save()
        set_flash_message(response, "Пароль успешно изменен", "success")
        
        return RedirectResponse(url="/profile", status_code=302)
    except Exception as e:
        set_flash_message(response, f"Ошибка при смене пароля: {str(e)}", "error")
        return RedirectResponse(url="/profile/change-password", status_code=302)



