"""
API endpoints для мобильных приложений
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel, EmailStr
import json

from bot.core.models import User, Recipe, MealPlan, RecipeBase
from bot.web.dependencies import get_current_user
from bot.services.openai_service import openai_service
from bot.services.recipe_search import (
    find_recipes_by_kbzhu,
    find_recipes_by_tags,
    find_recipes_by_title,
    get_random_recipes
)

router = APIRouter(prefix="/api/v1", tags=["api"])


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


# --- Аутентификация ---

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о текущем пользователе"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }


# --- Рецепты пользователя ---

@router.get("/recipes", response_model=List[RecipeResponse])
async def get_user_recipes(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """Получить список рецептов пользователя"""
    recipes = await Recipe.filter(user=current_user).offset(offset).limit(limit).order_by("-created_at")
    
    result = []
    for recipe in recipes:
        recipe_data = json.loads(recipe.recipe_text) if recipe.recipe_text else {}
        result.append(RecipeResponse(
            id=str(recipe.id),
            title=recipe_data.get("recipe_title"),
            ingredients_detected=recipe.ingredients_detected,
            clarifications=recipe.clarifications,
            target_calories=recipe.target_calories,
            target_protein=recipe.target_protein,
            target_fat=recipe.target_fat,
            target_carbs=recipe.target_carbs,
            greens_weight=recipe.greens_weight,
            recipe_text=recipe_data,
            calculated_calories=recipe.calculated_calories,
            calculated_protein=recipe.calculated_protein,
            calculated_fat=recipe.calculated_fat,
            calculated_carbs=recipe.calculated_carbs,
            created_at=recipe.created_at.isoformat() if recipe.created_at else ""
        ))
    
    return result


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_user_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить конкретный рецепт пользователя"""
    try:
        recipe = await Recipe.get(id=recipe_id, user=current_user)
        recipe_data = json.loads(recipe.recipe_text) if recipe.recipe_text else {}
        
        return RecipeResponse(
            id=str(recipe.id),
            title=recipe_data.get("recipe_title"),
            ingredients_detected=recipe.ingredients_detected,
            clarifications=recipe.clarifications,
            target_calories=recipe.target_calories,
            target_protein=recipe.target_protein,
            target_fat=recipe.target_fat,
            target_carbs=recipe.target_carbs,
            greens_weight=recipe.greens_weight,
            recipe_text=recipe_data,
            calculated_calories=recipe.calculated_calories,
            calculated_protein=recipe.calculated_protein,
            calculated_fat=recipe.calculated_fat,
            calculated_carbs=recipe.calculated_carbs,
            created_at=recipe.created_at.isoformat() if recipe.created_at else ""
        )
    except Recipe.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден")


# --- Планы питания ---

@router.get("/meal-plans", response_model=List[MealPlanResponse])
async def get_user_meal_plans(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """Получить список планов питания пользователя"""
    meal_plans = await MealPlan.filter(user=current_user).offset(offset).limit(limit).order_by("-created_at")
    
    result = []
    for meal_plan in meal_plans:
        meal_plan_data = json.loads(meal_plan.meal_plan_text) if meal_plan.meal_plan_text else {}
        result.append(MealPlanResponse(
            id=str(meal_plan.id),
            meals_count=meal_plan.meals_count,
            target_daily_calories=meal_plan.target_daily_calories,
            target_daily_protein=meal_plan.target_daily_protein,
            target_daily_fat=meal_plan.target_daily_fat,
            target_daily_carbs=meal_plan.target_daily_carbs,
            daily_greens_weight=meal_plan.daily_greens_weight,
            meal_plan_text=meal_plan_data,
            calculated_daily_calories=meal_plan.calculated_daily_calories,
            calculated_daily_protein=meal_plan.calculated_daily_protein,
            calculated_daily_fat=meal_plan.calculated_daily_fat,
            calculated_daily_carbs=meal_plan.calculated_daily_carbs,
            created_at=meal_plan.created_at.isoformat() if meal_plan.created_at else ""
        ))
    
    return result


@router.get("/meal-plans/{meal_plan_id}", response_model=MealPlanResponse)
async def get_user_meal_plan(
    meal_plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить конкретный план питания пользователя"""
    try:
        meal_plan = await MealPlan.get(id=meal_plan_id, user=current_user)
        meal_plan_data = json.loads(meal_plan.meal_plan_text) if meal_plan.meal_plan_text else {}
        
        return MealPlanResponse(
            id=str(meal_plan.id),
            meals_count=meal_plan.meals_count,
            target_daily_calories=meal_plan.target_daily_calories,
            target_daily_protein=meal_plan.target_daily_protein,
            target_daily_fat=meal_plan.target_daily_fat,
            target_daily_carbs=meal_plan.target_daily_carbs,
            daily_greens_weight=meal_plan.daily_greens_weight,
            meal_plan_text=meal_plan_data,
            calculated_daily_calories=meal_plan.calculated_daily_calories,
            calculated_daily_protein=meal_plan.calculated_daily_protein,
            calculated_daily_fat=meal_plan.calculated_daily_fat,
            calculated_daily_carbs=meal_plan.calculated_daily_carbs,
            created_at=meal_plan.created_at.isoformat() if meal_plan.created_at else ""
        )
    except MealPlan.DoesNotExist:
        raise HTTPException(status_code=404, detail="План питания не найден")


# --- Общая база рецептов ---

@router.get("/recipes-base", response_model=List[RecipeBaseResponse])
async def get_base_recipes(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
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
async def get_base_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user)
):
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
    current_user: User = Depends(get_current_user),
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
async def get_random_base_recipes(
    current_user: User = Depends(get_current_user),
    limit: int = 5
):
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

