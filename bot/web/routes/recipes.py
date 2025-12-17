"""
Роуты для работы с рецептами
"""

import base64
import json
import logging
import os
import traceback
from pathlib import Path
from typing import Optional
from urllib.parse import quote
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
logger = logging.getLogger(__name__)

# Директория для загрузки изображений
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def encode_cookie_value(value: str) -> str:
    """Кодирует строковое значение cookie в base64 для поддержки Unicode"""
    if not value:
        return ""
    # Кодируем строку в base64 напрямую (без JSON, так как это уже строка)
    return base64.b64encode(value.encode('utf-8')).decode('ascii')


def decode_cookie_value(encoded_value: str) -> str:
    """Декодирует строковое значение cookie из base64"""
    if not encoded_value:
        return ""
    try:
        # Декодируем из base64
        return base64.b64decode(encoded_value.encode('ascii')).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка декодирования cookie: {e}")
        return ""


def encode_cookie_json(obj: dict) -> str:
    """Кодирует JSON объект в base64 для cookie"""
    if not obj:
        return ""
    json_str = json.dumps(obj, ensure_ascii=False)
    return base64.b64encode(json_str.encode('utf-8')).decode('ascii')


def decode_cookie_json(encoded_value: str) -> dict:
    """Декодирует JSON объект из base64 cookie"""
    if not encoded_value:
        return {}
    try:
        json_str = base64.b64decode(encoded_value.encode('ascii')).decode('utf-8')
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Ошибка декодирования JSON cookie: {e}")
        return {}


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
    error_message = request.query_params.get("error")
    
    context = {
        "request": request,
        "title": "Создать рецепт - Загрузка фото",
        "error_message": error_message
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

    # Сохраняем анализ в куки (кодируем в base64 для поддержки Unicode)
    response.set_cookie(
        key="recipe_analysis",
        value=encode_cookie_json(analysis),
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

    # Сохраняем уточнения в сессии (кодируем в base64 для поддержки Unicode)
    response.set_cookie(
        key="recipe_clarifications",
        value=encode_cookie_value(clarifications),
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
    target_protein: float = Form(0),
    target_fat: float = Form(0),
    target_carbs: float = Form(0),
    greens_weight: float = Form(0),
    cooking_tags: str = Form("")
):
    """Обработка параметров КБЖУ и генерация рецепта"""
    # Валидация диапазонов
    if not (0 < target_calories <= 10000):
        raise HTTPException(
            status_code=400,
            detail="Калории должны быть от 0 до 10000"
        )

    # Опциональные параметры - проверяем только если указаны
    if target_protein > 0 and not (0 < target_protein <= 1000):
        raise HTTPException(
            status_code=400,
            detail="Белки должны быть от 0 до 1000 г"
        )

    if target_fat > 0 and not (0 < target_fat <= 1000):
        raise HTTPException(
            status_code=400,
            detail="Жиры должны быть от 0 до 1000 г"
        )

    if target_carbs > 0 and not (0 < target_carbs <= 1000):
        raise HTTPException(
            status_code=400,
            detail="Углеводы должны быть от 0 до 1000 г"
        )

    if greens_weight > 0 and not (0 < greens_weight <= 2000):
        raise HTTPException(
            status_code=400,
            detail="Вес растительности должен быть от 0 до 2000 г"
        )

    # Получаем данные из сессии
    photo_path = request.cookies.get("recipe_photo")
    analysis_encoded = request.cookies.get("recipe_analysis")
    clarifications_encoded = request.cookies.get("recipe_clarifications")

    if not all([photo_path, analysis_encoded]):
        return RedirectResponse(url="/recipes/create", status_code=302)

    # Декодируем cookie значения из base64
    analysis = decode_cookie_json(analysis_encoded) if analysis_encoded else {}
    clarifications = decode_cookie_value(clarifications_encoded) if clarifications_encoded else ""

    # Формируем список ингредиентов
    ingredients = analysis.get("ingredients", [])

    # Добавляем уточнения пользователя
    if clarifications:
        ingredients.append(f"Уточнения: {clarifications}")

    # Теги способов приготовления передаются отдельно в generate_recipe

    # Формируем параметры для AI (только указанные пользователем)
    ai_params = {
        "ingredients": ingredients,
        "target_calories": int(target_calories)
    }

    # Добавляем опциональные параметры только если они указаны
    if target_protein > 0:
        ai_params["target_protein"] = target_protein
    if target_fat > 0:
        ai_params["target_fat"] = target_fat
    if target_carbs > 0:
        ai_params["target_carbs"] = target_carbs
    if greens_weight > 0:
        ai_params["greens_weight"] = greens_weight
    
    # Добавляем теги способов приготовления, если указаны
    if cooking_tags:
        ai_params["cooking_tags"] = cooking_tags

    try:
        # Генерируем рецепт
        recipe_data = await openai_service.generate_recipe(**ai_params)

        # Валидация структуры данных рецепта
        if not recipe_data:
            raise ValueError("Не получены данные рецепта от OpenAI")
        
        if 'calculated_nutrition' not in recipe_data:
            logger.error(f"Отсутствует ключ 'calculated_nutrition' в recipe_data. Доступные ключи: {recipe_data.keys()}")
            raise ValueError("Неверная структура данных рецепта: отсутствует 'calculated_nutrition'")
        
        nutrition = recipe_data['calculated_nutrition']
        required_nutrition_fields = ['calories', 'protein_g', 'fat_g', 'carbs_g']
        for field in required_nutrition_fields:
            if field not in nutrition:
                logger.error(f"Отсутствует поле '{field}' в calculated_nutrition. Доступные поля: {nutrition.keys()}")
                raise ValueError(f"Неверная структура данных рецепта: отсутствует '{field}' в calculated_nutrition")

        # Сохраняем рецепт в БД
        # Формируем строку уточнений с правильной кодировкой
        clarifications_combined = f"{clarifications or ''}; Cooking: {cooking_tags or ''}".strip('; ')
        if clarifications_combined:
            clarifications_combined = clarifications_combined.strip()
        else:
            clarifications_combined = None

        recipe = await Recipe.create(
            photo_file_id=photo_path,  # Сохраняем путь к фото
            ingredients_detected=json.dumps(ingredients, ensure_ascii=False),
            clarifications=clarifications_combined,
            target_calories=target_calories,
            target_protein=target_protein if target_protein > 0 else 0,
            target_fat=target_fat if target_fat > 0 else 0,
            target_carbs=target_carbs if target_carbs > 0 else 0,
            greens_weight=greens_weight if greens_weight > 0 else 0,
            recipe_text=json.dumps(recipe_data, ensure_ascii=False),
            calculated_calories=float(nutrition['calories']),
            calculated_protein=float(nutrition['protein_g']),
            calculated_fat=float(nutrition['fat_g']),
            calculated_carbs=float(nutrition['carbs_g'])
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
        # Логируем ошибку
        error_msg = str(e)
        logger.error(f"Ошибка при создании рецепта: {error_msg}")
        logger.error(traceback.format_exc())

        # В случае ошибки очищаем сессию и показываем сообщение об ошибке
        # Кодируем сообщение об ошибке для URL (для поддержки Unicode)
        try:
            error_url = f"/recipes/create?error={quote(error_msg, safe='')}"
        except UnicodeEncodeError:
            # Если quote не справляется, используем простое сообщение
            error_url = f"/recipes/create?error={quote('Произошла ошибка при создании рецепта', safe='')}"

        response = RedirectResponse(url=error_url, status_code=302)
        
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




