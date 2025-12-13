"""
Роуты для работы с рецептами
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bot.core.models import User, Recipe
from bot.services.openai_service import openai_service
from bot.web.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Директория для загрузки изображений
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def cleanup_recipe_session(response: Response, user_id: str):
    """Очищает все куки связанные с созданием рецепта для пользователя"""
    cookies_to_delete = [
        f"recipe_photo_{user_id}",
        f"recipe_analysis_{user_id}",
        f"recipe_clarifications_{user_id}"
    ]

    for cookie_key in cookies_to_delete:
        response.delete_cookie(key=cookie_key)


@router.get("/", response_class=HTMLResponse)
async def recipes_home(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Главная страница рецептов"""
    # Получаем рецепты пользователя
    recipes = await Recipe.filter(user=current_user).order_by("-created_at").limit(10)

    return templates.TemplateResponse(
        "recipes/index.html",
        {
            "request": request,
            "user": current_user,
            "title": "Мои рецепты",
            "recipes": recipes
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_recipe_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница создания рецепта - шаг 1: загрузка фото"""
    return templates.TemplateResponse(
        "recipes/create/step1.html",
        {
            "request": request,
            "user": current_user,
            "title": "Создать рецепт - Загрузка фото"
        }
    )


@router.post("/create/step1")
async def process_photo_upload(
    request: Request,
    current_user: User = Depends(get_current_user),
    photo: UploadFile = File(...)
):
    """Обработка загруженного фото - шаг 1"""
    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")

    # Сохраняем фото
    file_extension = os.path.splitext(photo.filename)[1]
    file_name = f"{current_user.id}_recipe_{request.url_for('create_recipe_page').path.replace('/', '_')}{file_extension}"
    file_path = UPLOAD_DIR / file_name

    with open(file_path, "wb") as buffer:
        content = await photo.read()
        buffer.write(content)

    # Сохраняем путь к фото в сессии (в куки для простоты)
    response = RedirectResponse(url="/recipes/create/step2", status_code=302)
    response.set_cookie(
        key=f"recipe_photo_{current_user.id}",
        value=str(file_path.relative_to("static")),
        httponly=True,  # Защита от XSS атак
        secure=False,   # Для разработки без HTTPS
        max_age=3600    # 1 час
    )

    return response


@router.get("/create/step2", response_class=HTMLResponse)
async def analyze_photo_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Анализ фото и уточнение продуктов - шаг 2"""
    # Получаем фото из сессии
    photo_path = request.cookies.get(f"recipe_photo_{current_user.id}")
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
    response = templates.TemplateResponse(
        "recipes/create/step2.html",
        {
            "request": request,
            "user": current_user,
            "title": "Анализ продуктов",
            "analysis": analysis,
            "photo_path": photo_path
        }
    )

    # Сохраняем анализ в куки (сериализуем в JSON)
    response.set_cookie(
        key=f"recipe_analysis_{current_user.id}",
        value=json.dumps(analysis),
        httponly=True,  # Защита от XSS атак
        secure=False,   # Для разработки без HTTPS
        max_age=3600
    )

    return response


@router.post("/create/step2")
async def process_clarifications(
    request: Request,
    current_user: User = Depends(get_current_user),
    clarifications: str = Form("")
):
    """Обработка уточнений - переход к шагу 3"""
    response = RedirectResponse(url="/recipes/create/step3", status_code=302)

    # Сохраняем уточнения в сессии
    response.set_cookie(
        key=f"recipe_clarifications_{current_user.id}",
        value=clarifications,
        httponly=True,  # Защита от XSS атак
        secure=False,   # Для разработки без HTTPS
        max_age=3600
    )

    return response


@router.get("/create/step3", response_class=HTMLResponse)
async def nutrition_parameters_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Ввод параметров КБЖУ - шаг 3"""
    return templates.TemplateResponse(
        "recipes/create/step3.html",
        {
            "request": request,
            "user": current_user,
            "title": "Параметры питания"
        }
    )


@router.post("/create/step3")
async def process_nutrition_parameters(
    request: Request,
    current_user: User = Depends(get_current_user),
    target_calories: float = Form(...),
    target_protein: float = Form(...),
    target_fat: float = Form(...),
    target_carbs: float = Form(...),
    greens_weight: float = Form(...)
):
    """Обработка параметров КБЖУ и генерация рецепта"""
    # Получаем данные из сессии
    photo_path = request.cookies.get(f"recipe_photo_{current_user.id}")
    analysis_json = request.cookies.get(f"recipe_analysis_{current_user.id}")
    clarifications = request.cookies.get(f"recipe_clarifications_{current_user.id}")

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
            user=current_user,
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
        cleanup_recipe_session(response, str(current_user.id))

        return response

    except Exception as e:
        # В случае ошибки тоже очищаем сессию
        response = Response(
            content=json.dumps({"error": f"Ошибка генерации рецепта: {str(e)}"}),
            media_type="application/json",
            status_code=500
        )
        cleanup_recipe_session(response, str(current_user.id))
        return response


@router.get("/{recipe_id}", response_class=HTMLResponse)
async def view_recipe(
    request: Request,
    recipe_id: str,
    current_user: User = Depends(get_current_user)
):
    """Просмотр готового рецепта"""
    try:
        recipe = await Recipe.get(id=recipe_id, user=current_user)
        recipe_data = json.loads(recipe.recipe_text)

        return templates.TemplateResponse(
            "recipes/view.html",
            {
                "request": request,
                "user": current_user,
                "title": recipe_data.get('recipe_title', 'Рецепт'),
                "recipe": recipe,
                "recipe_data": recipe_data
            }
        )
    except Recipe.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден")


