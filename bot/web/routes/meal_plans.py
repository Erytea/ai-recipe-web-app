"""
Роуты для работы с планами питания
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bot.core.models import User, MealPlan
from bot.services.openai_service import openai_service
from bot.web.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Директория для загрузки изображений
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/", response_class=HTMLResponse)
async def meal_plans_home(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Главная страница планов питания"""
    # Получаем планы питания пользователя
    meal_plans = await MealPlan.filter(user=current_user).order_by("-created_at").limit(10)

    context = {
        "request": request,
        "user": current_user,
        "title": "Мои планы питания",
        "meal_plans": meal_plans
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]

    return templates.TemplateResponse("meal_plans/index.html", context)


@router.get("/create", response_class=HTMLResponse)
async def create_meal_plan_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница создания плана питания - шаг 1: загрузка фото"""
    context = {
        "request": request,
        "user": current_user,
        "title": "Создать план питания - Загрузка фото"
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("meal_plans/create/step1.html", context)


@router.post("/create/step1")
async def process_meal_plan_photo_upload(
    request: Request,
    current_user: User = Depends(get_current_user),
    photo: UploadFile = File(...)
):
    """Обработка загруженного фото продуктов"""
    from bot.core.config import settings
    
    # Проверка типа файла
    if not photo.content_type or not photo.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть изображением (JPEG, PNG, WebP)"
        )
    
    # Проверка расширения
    file_extension = os.path.splitext(photo.filename)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат. Разрешены: {', '.join(allowed_extensions)}"
        )
    
    # Читаем файл один раз для проверки размера и сохранения
    content = await photo.read()
    file_size = len(content)
    
    # Проверка размера
    if file_size > settings.max_upload_size:
        max_size_mb = settings.max_upload_size / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {max_size_mb:.1f} МБ"
        )

    # Сохраняем фото
    file_extension = os.path.splitext(photo.filename)[1]
    file_name = f"{current_user.id}_meal_plan_{request.url_for('create_meal_plan_page').path.replace('/', '_')}{file_extension}"
    file_path = UPLOAD_DIR / file_name

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Сохраняем путь к фото в сессии
    response = RedirectResponse(url="/meal-plans/create/step2", status_code=302)
    response.set_cookie(
        key=f"meal_plan_photo_{current_user.id}",
        value=str(file_path.relative_to("static")),
        max_age=3600  # 1 час
    )

    return response


@router.get("/create/step2", response_class=HTMLResponse)
async def analyze_meal_plan_photo_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Анализ фото продуктов для плана питания - шаг 2"""
    # Получаем фото из сессии
    photo_path = request.cookies.get(f"meal_plan_photo_{current_user.id}")
    if not photo_path:
        response = RedirectResponse(url="/meal-plans/create", status_code=302)
        set_flash_message(response, "Сначала загрузи фото продуктов", "warning")
        return response

    # Анализируем фото
    full_path = Path("static") / photo_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Фото не найдено")

    try:
        with open(full_path, "rb") as f:
            analysis = await openai_service.analyze_food_image(f.read())
    except Exception as e:
        error_msg = str(e)
        if "OpenAI" in error_msg or "rate_limit" in error_msg.lower():
            response = RedirectResponse(url="/meal-plans/create", status_code=302)
            set_flash_message(response, "Ошибка при анализе фото. Попробуй позже.", "error")
            return response
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {error_msg}")

    # Сохраняем анализ в сессии
    context = {
        "request": request,
        "user": current_user,
        "title": "Анализ продуктов",
        "analysis": analysis,
        "photo_path": photo_path
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    response = templates.TemplateResponse("meal_plans/create/step2.html", context)

    # Сохраняем анализ в куки
    response.set_cookie(
        key=f"meal_plan_analysis_{current_user.id}",
        value=json.dumps(analysis),
        max_age=3600
    )

    return response


@router.post("/create/step2")
async def process_meal_plan_clarifications(
    request: Request,
    current_user: User = Depends(get_current_user),
    clarifications: str = Form("")
):
    """Обработка уточнений для плана питания - переход к шагу 3"""
    response = RedirectResponse(url="/meal-plans/create/step3", status_code=302)

    # Сохраняем уточнения в сессии
    response.set_cookie(
        key=f"meal_plan_clarifications_{current_user.id}",
        value=clarifications,
        max_age=3600
    )

    return response


@router.get("/create/step3", response_class=HTMLResponse)
async def meal_plan_parameters_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Ввод параметров для плана питания - шаг 3"""
    context = {
        "request": request,
        "user": current_user,
        "title": "Параметры плана питания"
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("meal_plans/create/step3.html", context)


@router.post("/create/step3")
async def process_meal_plan_parameters(
    request: Request,
    current_user: User = Depends(get_current_user),
    meals_count: int = Form(...),
    target_daily_calories: float = Form(...),
    target_daily_protein: float = Form(...),
    target_daily_fat: float = Form(...),
    target_daily_carbs: float = Form(...),
    daily_greens_weight: float = Form(...)
):
    """Обработка параметров и генерация плана питания"""
    # Валидация диапазонов
    if not (1 <= meals_count <= 6):
        raise HTTPException(
            status_code=400,
            detail="Количество приемов пищи должно быть от 1 до 6"
        )
    
    if not (500 <= target_daily_calories <= 5000):
        raise HTTPException(
            status_code=400,
            detail="Калории за день должны быть от 500 до 5000"
        )
    
    if not (0 <= target_daily_protein <= 500):
        raise HTTPException(
            status_code=400,
            detail="Белки за день должны быть от 0 до 500 г"
        )
    
    if not (0 <= target_daily_fat <= 300):
        raise HTTPException(
            status_code=400,
            detail="Жиры за день должны быть от 0 до 300 г"
        )
    
    if not (0 <= target_daily_carbs <= 600):
        raise HTTPException(
            status_code=400,
            detail="Углеводы за день должны быть от 0 до 600 г"
        )
    
    if not (0 <= daily_greens_weight <= 2000):
        raise HTTPException(
            status_code=400,
            detail="Вес растительности за день должен быть от 0 до 2000 г"
        )
    # Получаем данные из сессии
    photo_path = request.cookies.get(f"meal_plan_photo_{current_user.id}")
    analysis_json = request.cookies.get(f"meal_plan_analysis_{current_user.id}")
    clarifications = request.cookies.get(f"meal_plan_clarifications_{current_user.id}")

    if not all([photo_path, analysis_json]):
        return RedirectResponse(url="/meal-plans/create", status_code=302)

    analysis = json.loads(analysis_json)

    # Формируем список ингредиентов
    ingredients = analysis.get("ingredients", [])
    if clarifications:
        ingredients.append(f"Уточнения: {clarifications}")

    try:
        # Генерируем план питания
        meal_plan_data = await openai_service.generate_meal_plan(
            ingredients=ingredients,
            meals_count=meals_count,
            target_daily_calories=target_daily_calories,
            target_daily_protein=target_daily_protein,
            target_daily_fat=target_daily_fat,
            target_daily_carbs=target_daily_carbs,
            daily_greens_weight=daily_greens_weight
        )

        # Сохраняем план в БД
        meal_plan = await MealPlan.create(
            user=current_user,
            photo_file_id=photo_path,
            ingredients_detected=json.dumps(ingredients, ensure_ascii=False),
            clarifications=clarifications,
            meals_count=meals_count,
            target_daily_calories=target_daily_calories,
            target_daily_protein=target_daily_protein,
            target_daily_fat=target_daily_fat,
            target_daily_carbs=target_daily_carbs,
            daily_greens_weight=daily_greens_weight,
            meal_plan_text=json.dumps(meal_plan_data, ensure_ascii=False),
            calculated_daily_calories=meal_plan_data['calculated_daily_nutrition']['calories'],
            calculated_daily_protein=meal_plan_data['calculated_daily_nutrition']['protein_g'],
            calculated_daily_fat=meal_plan_data['calculated_daily_nutrition']['fat_g'],
            calculated_daily_carbs=meal_plan_data['calculated_daily_nutrition']['carbs_g']
        )

        # Очищаем сессию и перенаправляем на результат
        response = RedirectResponse(url=f"/meal-plans/{meal_plan.id}", status_code=302)
        set_flash_message(response, "План питания успешно создан!", "success")

        # Очищаем куки
        response.delete_cookie(f"meal_plan_photo_{current_user.id}")
        response.delete_cookie(f"meal_plan_analysis_{current_user.id}")
        response.delete_cookie(f"meal_plan_clarifications_{current_user.id}")

        return response

    except Exception as e:
        response = RedirectResponse(url="/meal-plans/create", status_code=302)
        set_flash_message(response, f"Ошибка генерации плана: {str(e)}", "error")
        return response


@router.get("/{meal_plan_id}", response_class=HTMLResponse)
async def view_meal_plan(
    request: Request,
    meal_plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Просмотр готового плана питания"""
    try:
        meal_plan = await MealPlan.get(id=meal_plan_id, user=current_user)
        meal_plan_data = json.loads(meal_plan.meal_plan_text)

        return templates.TemplateResponse(
            "meal_plans/view.html",
            {
                "request": request,
                "user": current_user,
                "title": "План питания на день",
                "meal_plan": meal_plan,
                "meal_plan_data": meal_plan_data
            }
        )
    except MealPlan.DoesNotExist:
        raise HTTPException(status_code=404, detail="План питания не найден")



