"""
Роуты для работы с рецептами
"""

import json
import os
from pathlib import Path
from typing import Optional
import uuid

from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bot.core.models import Recipe, RecipeBase
from bot.services.openai_service import openai_service
from bot.services.recipe_search import (
    find_recipes_by_kbzhu,
    find_recipes_by_tags,
    find_recipes_by_title,
    get_random_recipes
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Директория для загрузки изображений
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/", response_class=HTMLResponse)
async def recipes_home(request: Request):
    """Главная страница рецептов"""
    # Получаем последние рецепты
    recipes = await Recipe.all().order_by("-created_at").limit(10)

    context = {
        "request": request,
        "title": "Рецепты",
        "recipes": recipes
    }

    return templates.TemplateResponse("recipes/index.html", context)


@router.get("/create", response_class=HTMLResponse)
async def create_recipe_page(request: Request):
    """Страница создания рецепта - шаг 1: загрузка фото"""
    context = {
        "request": request,
        "title": "Создать рецепт - Загрузка фото"
    }

    return templates.TemplateResponse("recipes/create/step1.html", context)


@router.post("/create/step1")
async def process_photo_upload(
    request: Request,
    photo: UploadFile = File(...)
):
    """Обработка загруженного фото - шаг 1"""
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

    # Генерируем уникальный ID сессии
    session_id = str(uuid.uuid4())

    # Сохраняем фото
    file_extension = os.path.splitext(photo.filename)[1]
    file_name = f"{session_id}_recipe{file_extension}"
    file_path = UPLOAD_DIR / file_name

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Сохраняем путь к фото в сессии (в куки для простоты)
    response = RedirectResponse(url="/recipes/create/step2", status_code=302)
    response.set_cookie(
        key="recipe_session_id",
        value=session_id,
        httponly=True,  # Защита от XSS атак
        secure=False,   # Для разработки без HTTPS
        max_age=3600    # 1 час
    )
    response.set_cookie(
        key="recipe_photo",
        value=str(file_path.relative_to("static")),
        httponly=True,  # Защита от XSS атак
        secure=False,   # Для разработки без HTTPS
        max_age=3600    # 1 час
    )

    return response


@router.get("/create/step2", response_class=HTMLResponse)
async def analyze_photo_page(request: Request):
    """Анализ фото и уточнение продуктов - шаг 2"""
    # Получаем фото из сессии
    photo_path = request.cookies.get("recipe_photo")
    if not photo_path:
        return RedirectResponse(url="/recipes/create", status_code=302)

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
    context = {
        "request": request,
        "title": "Анализ продуктов",
        "analysis": analysis,
        "photo_path": photo_path
    }

    response = templates.TemplateResponse("recipes/create/step2.html", context)

    # Сохраняем анализ в куки (сериализуем в JSON)
    response.set_cookie(
        key="recipe_analysis",
        value=json.dumps(analysis),
        httponly=True,  # Защита от XSS атак
        secure=False,   # Для разработки без HTTPS
        max_age=3600
    )

    return response


@router.post("/create/step2")
async def process_clarifications(
    request: Request,
    clarifications: str = Form("")
):
    """Обработка уточнений - переход к шагу 3"""
    response = RedirectResponse(url="/recipes/create/step3", status_code=302)

    # Сохраняем уточнения в сессии
    response.set_cookie(
        key="recipe_clarifications",
        value=clarifications,
        httponly=True,  # Защита от XSS атак
        secure=False,   # Для разработки без HTTPS
        max_age=3600
    )

    return response


@router.get("/create/step3", response_class=HTMLResponse)
async def nutrition_parameters_page(request: Request):
    """Ввод параметров КБЖУ - шаг 3"""
    context = {
        "request": request,
        "title": "Параметры питания"
    }

    return templates.TemplateResponse("recipes/create/step3.html", context)


@router.post("/create/step3")
async def process_nutrition_parameters(
    request: Request,
    target_calories: float = Form(...),
    target_protein: float = Form(...),
    target_fat: float = Form(...),
    target_carbs: float = Form(...),
    greens_weight: float = Form(...)
):
    """Обработка параметров КБЖУ и генерация рецепта"""
    # Валидация диапазонов
    if not (0 < target_calories <= 10000):
        raise HTTPException(
            status_code=400,
            detail="Калории должны быть от 0 до 10000"
        )

    if not (0 <= target_protein <= 1000):
        raise HTTPException(
            status_code=400,
            detail="Белки должны быть от 0 до 1000 г"
        )

    if not (0 <= target_fat <= 1000):
        raise HTTPException(
            status_code=400,
            detail="Жиры должны быть от 0 до 1000 г"
        )

    if not (0 <= target_carbs <= 1000):
        raise HTTPException(
            status_code=400,
            detail="Углеводы должны быть от 0 до 1000 г"
        )

    if not (0 <= greens_weight <= 2000):
        raise HTTPException(
            status_code=400,
            detail="Вес растительности должен быть от 0 до 2000 г"
        )

    # Получаем данные из сессии
    photo_path = request.cookies.get("recipe_photo")
    analysis_json = request.cookies.get("recipe_analysis")
    clarifications = request.cookies.get("recipe_clarifications")

    if not all([photo_path, analysis_json]):
        return RedirectResponse(url="/recipes/create", status_code=302)

    analysis = json.loads(analysis_json)

    # Формируем список ингредиентов
    ingredients = analysis.get("ingredients", [])
    if clarifications:
        ingredients.append(f"Уточнения: {clarifications}")

    try:
        # Генерируем рецепт
        recipe_data = await openai_service.generate_recipe(
            ingredients=ingredients,
            target_calories=target_calories,
            target_protein=target_protein,
            target_fat=target_fat,
            target_carbs=target_carbs,
            greens_weight=greens_weight
        )

        # Сохраняем рецепт в БД
        recipe = await Recipe.create(
            photo_file_id=photo_path,  # Сохраняем путь к фото
            ingredients_detected=json.dumps(ingredients, ensure_ascii=False),
            clarifications=clarifications,
            target_calories=target_calories,
            target_protein=target_protein,
            target_fat=target_fat,
            target_carbs=target_carbs,
            greens_weight=greens_weight,
            recipe_text=json.dumps(recipe_data, ensure_ascii=False),
            calculated_calories=recipe_data['calculated_nutrition']['calories'],
            calculated_protein=recipe_data['calculated_nutrition']['protein_g'],
            calculated_fat=recipe_data['calculated_nutrition']['fat_g'],
            calculated_carbs=recipe_data['calculated_nutrition']['carbs_g']
        )

        # Очищаем сессию и перенаправляем на результат
        response = RedirectResponse(url=f"/recipes/{recipe.id}", status_code=302)

        # Очищаем все куки связанные с рецептом
        response.delete_cookie("recipe_session_id")
        response.delete_cookie("recipe_photo")
        response.delete_cookie("recipe_analysis")
        response.delete_cookie("recipe_clarifications")

        return response

    except Exception as e:
        # В случае ошибки тоже очищаем сессию
        response = RedirectResponse(url="/recipes/create", status_code=302)
        response.delete_cookie("recipe_session_id")
        response.delete_cookie("recipe_photo")
        response.delete_cookie("recipe_analysis")
        response.delete_cookie("recipe_clarifications")
        return response


@router.get("/{recipe_id}", response_class=HTMLResponse)
async def view_recipe(request: Request, recipe_id: str):
    """Просмотр готового рецепта"""
    try:
        recipe = await Recipe.get(id=recipe_id)
        recipe_data = json.loads(recipe.recipe_text)

        context = {
            "request": request,
            "title": recipe_data.get('recipe_title', 'Рецепт'),
            "recipe": recipe,
            "recipe_data": recipe_data
        }

        return templates.TemplateResponse("recipes/view.html", context)
    except Recipe.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден")




