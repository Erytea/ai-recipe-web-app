"""
API endpoints для генерации рецептов
"""

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
import json
import os
from pathlib import Path

from bot.core.models import Recipe, RecipeBase
from bot.services.openai_service import openai_service
from bot.services.recipe_search import (
    find_recipes_by_kbzhu,
    find_recipes_by_tags,
    find_recipes_by_title,
    get_random_recipes
)

router = APIRouter(prefix="/api/v1", tags=["api"])

# Директория для загрузки изображений
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# --- Pydantic модели для валидации ---

class RecipeResponse(BaseModel):
    """Модель ответа для рецепта"""
    id: str
    title: Optional[str] = None
    ingredients_detected: str
    clarifications: Optional[str] = None
    target_calories: int
    target_protein: float
    target_fat: float
    target_carbs: float
    greens_weight: float
    recipe_text: dict
    calculated_calories: float
    calculated_protein: float
    calculated_fat: float
    calculated_carbs: float
    created_at: str

    class Config:
        from_attributes = True


class MealPlanResponse(BaseModel):
    """Модель ответа для плана питания"""
    id: str
    meals_count: int
    target_daily_calories: int
    target_daily_protein: float
    target_daily_fat: float
    target_daily_carbs: float
    daily_greens_weight: float
    meal_plan_text: dict
    calculated_daily_calories: float
    calculated_daily_protein: float
    calculated_daily_fat: float
    calculated_daily_carbs: float
    created_at: str

    class Config:
        from_attributes = True


class RecipeBaseResponse(BaseModel):
    """Модель ответа для рецепта из общей базы"""
    id: str
    title: str
    tags: Optional[str] = None
    cooking_time: Optional[str] = None
    difficulty: Optional[str] = None
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    ingredients: str
    instructions: str
    notes: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True




# --- Общая база рецептов ---

@router.get("/recipes-base", response_model=List[RecipeBaseResponse])
async def get_base_recipes(limit: int = 20, offset: int = 0):
    """Получить список рецептов из общей базы"""
    recipes = await RecipeBase.all().offset(offset).limit(limit).order_by("-created_at")

    result = []
    for recipe in recipes:
        result.append(RecipeBaseResponse(
            id=str(recipe.id),
            title=recipe.title,
            tags=recipe.tags,
            cooking_time=recipe.cooking_time,
            difficulty=recipe.difficulty,
            calories_per_100g=recipe.calories_per_100g,
            protein_per_100g=recipe.protein_per_100g,
            fat_per_100g=recipe.fat_per_100g,
            carbs_per_100g=recipe.carbs_per_100g,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            notes=recipe.notes,
            created_at=recipe.created_at.isoformat() if recipe.created_at else ""
        ))

    return result


@router.get("/recipes-base/{recipe_id}", response_model=RecipeBaseResponse)
async def get_base_recipe(recipe_id: str):
    """Получить конкретный рецепт из общей базы"""
    try:
        recipe = await RecipeBase.get(id=recipe_id)

        return RecipeBaseResponse(
            id=str(recipe.id),
            title=recipe.title,
            tags=recipe.tags,
            cooking_time=recipe.cooking_time,
            difficulty=recipe.difficulty,
            calories_per_100g=recipe.calories_per_100g,
            protein_per_100g=recipe.protein_per_100g,
            fat_per_100g=recipe.fat_per_100g,
            carbs_per_100g=recipe.carbs_per_100g,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            notes=recipe.notes,
            created_at=recipe.created_at.isoformat() if recipe.created_at else ""
        )
    except RecipeBase.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден в базе")


@router.post("/recipes-base/search")
async def search_base_recipes(
    search_type: str = Form(...),
    query: Optional[str] = Form(None),
    calories: Optional[float] = Form(None),
    protein: Optional[float] = Form(None),
    fat: Optional[float] = Form(None),
    carbs: Optional[float] = Form(None),
    tags: Optional[str] = Form(None)
):
    """Поиск рецептов в общей базе"""
    recipes = []

    if search_type == "kbzhu" and calories:
        recipes = await find_recipes_by_kbzhu(
            target_calories=calories,
            target_protein=protein,
            target_fat=fat,
            target_carbs=carbs
        )
    elif search_type == "tags" and tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        recipes = await find_recipes_by_tags(tag_list)
    elif search_type == "title" and query:
        recipes = await find_recipes_by_title(query)

    result = []
    for recipe in recipes:
        result.append(RecipeBaseResponse(
            id=str(recipe.id),
            title=recipe.title,
            tags=recipe.tags,
            cooking_time=recipe.cooking_time,
            difficulty=recipe.difficulty,
            calories_per_100g=recipe.calories_per_100g,
            protein_per_100g=recipe.protein_per_100g,
            fat_per_100g=recipe.fat_per_100g,
            carbs_per_100g=recipe.carbs_per_100g,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            notes=recipe.notes,
            created_at=recipe.created_at.isoformat() if recipe.created_at else ""
        ))

    return result


@router.get("/recipes-base/random", response_model=List[RecipeBaseResponse])
async def get_random_base_recipes(limit: int = 5):
    """Получить случайные рецепты из общей базы"""
    recipes = await get_random_recipes(limit=limit)

    result = []
    for recipe in recipes:
        result.append(RecipeBaseResponse(
            id=str(recipe.id),
            title=recipe.title,
            tags=recipe.tags,
            cooking_time=recipe.cooking_time,
            difficulty=recipe.difficulty,
            calories_per_100g=recipe.calories_per_100g,
            protein_per_100g=recipe.protein_per_100g,
            fat_per_100g=recipe.fat_per_100g,
            carbs_per_100g=recipe.carbs_per_100g,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            notes=recipe.notes,
            created_at=recipe.created_at.isoformat() if recipe.created_at else ""
        ))

    return result


# --- Генерация рецептов ---

@router.post("/generate-recipe")
async def generate_recipe(
    photo: UploadFile = File(...),
    clarifications: str = Form(""),
    target_calories: float = Form(...),
    target_protein: float = Form(0),
    target_fat: float = Form(0),
    target_carbs: float = Form(0),
    greens_weight: float = Form(0),
    cooking_tags: str = Form("")
):
    """Генерировать рецепт на основе фото"""
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

    # Читаем файл
    content = await photo.read()
    file_size = len(content)

    # Проверка размера
    if file_size > settings.max_upload_size:
        max_size_mb = settings.max_upload_size / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {max_size_mb:.1f} МБ"
        )

    # Валидация параметров
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

    try:
        # Формируем параметры для AI
        ai_params = {
            "image_data": content,  # Передаем изображение напрямую
            "target_calories": int(target_calories)
        }

        # Добавляем уточнения пользователя, если есть
        if clarifications:
            ai_params["ingredients"] = [f"Уточнения: {clarifications}"]

        # Добавляем опциональные параметры только если они указаны
        if target_protein > 0:
            ai_params["target_protein"] = target_protein
        if target_fat > 0:
            ai_params["target_fat"] = target_fat
        if target_carbs > 0:
            ai_params["target_carbs"] = target_carbs
        if greens_weight > 0:
            # Используем plant_level для нового промпта, но сохраняем greens_weight для БД
            ai_params["plant_level"] = greens_weight
        
        # Добавляем теги способов приготовления, если указаны
        if cooking_tags:
            ai_params["cooking_tags"] = cooking_tags

        # Генерируем рецепт напрямую из изображения
        recipe_data = await openai_service.generate_recipe(**ai_params)

        # Извлекаем список ингредиентов для сохранения в БД
        ingredients_list = []
        if "ingredients" in recipe_data:
            ingredients_list = [ing.get("name", "") for ing in recipe_data["ingredients"]]
        elif "ingredients_with_weights" in recipe_data:
            ingredients_list = [ing.get("name", "") for ing in recipe_data["ingredients_with_weights"]]

        # Сохраняем рецепт в БД
        recipe = await Recipe.create(
            photo_file_id="",  # Не сохраняем фото в файловой системе
            ingredients_detected=json.dumps(ingredients_list, ensure_ascii=False),
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

        return {
            "recipe_id": str(recipe.id),
            "recipe": recipe_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации рецепта: {str(e)}")


@router.get("/recipe/{recipe_id}")
async def get_recipe(recipe_id: str):
    """Получить рецепт по ID"""
    try:
        recipe = await Recipe.get(id=recipe_id)
        recipe_data = json.loads(recipe.recipe_text) if recipe.recipe_text else {}

        return {
            "id": str(recipe.id),
            "recipe": recipe_data,
            "ingredients_detected": recipe.ingredients_detected,
            "clarifications": recipe.clarifications,
            "target_calories": recipe.target_calories,
            "target_protein": recipe.target_protein,
            "target_fat": recipe.target_fat,
            "target_carbs": recipe.target_carbs,
            "greens_weight": recipe.greens_weight,
            "calculated_calories": recipe.calculated_calories,
            "calculated_protein": recipe.calculated_protein,
            "calculated_fat": recipe.calculated_fat,
            "calculated_carbs": recipe.calculated_carbs,
            "created_at": recipe.created_at.isoformat() if recipe.created_at else ""
        }
    except Recipe.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден")

