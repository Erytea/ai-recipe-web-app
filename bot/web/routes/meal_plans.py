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

    return templates.TemplateResponse(
        "meal_plans/index.html",
        {
            "request": request,
            "user": current_user,
            "title": "Мои планы питания",
            "meal_plans": meal_plans
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_meal_plan_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница создания плана питания - шаг 1: загрузка фото"""
    return templates.TemplateResponse(
        "meal_plans/create/step1.html",
        {
            "request": request,
            "user": current_user,
            "title": "Создать план питания - Загрузка фото"
        }
    )


@router.post("/create/step1")
async def process_meal_plan_photo_upload(
    request: Request,
    current_user: User = Depends(get_current_user),
    photo: UploadFile = File(...)
):
    """Обработка загруженного фото продуктов"""
    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")

    # Сохраняем фото
    file_extension = os.path.splitext(photo.filename)[1]
    file_name = f"{current_user.id}_meal_plan_{request.url_for('create_meal_plan_page').path.replace('/', '_')}{file_extension}"
    file_path = UPLOAD_DIR / file_name

    with open(file_path, "wb") as buffer:
        content = await photo.read()
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
        return RedirectResponse(url="/meal-plans/create", status_code=302)

    # Анализируем фото
    full_path = Path("static") / photo_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Фото не найдено")

    try:
        with open(full_path, "rb") as f:
            analysis = await openai_service.analyze_food_image(f.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

    # Сохраняем анализ в сессии
    response = templates.TemplateResponse(
        "meal_plans/create/step2.html",
        {
            "request": request,
            "user": current_user,
            "title": "Анализ продуктов",
            "analysis": analysis,
            "photo_path": photo_path
        }
    )

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
    return templates.TemplateResponse(
        "meal_plans/create/step3.html",
        {
            "request": request,
            "user": current_user,
            "title": "Параметры плана питания"
        }
    )


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

        # Очищаем куки
        response.delete_cookie(f"meal_plan_photo_{current_user.id}")
        response.delete_cookie(f"meal_plan_analysis_{current_user.id}")
        response.delete_cookie(f"meal_plan_clarifications_{current_user.id}")

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации плана: {str(e)}")


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


