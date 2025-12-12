"""
Поиск рецептов по КБЖУ
"""

from typing import List, Optional
from bot.core.models import RecipeBase


async def find_recipes_by_kbzhu(
    target_calories: float,
    target_protein: Optional[float] = None,
    target_fat: Optional[float] = None,
    target_carbs: Optional[float] = None,
    tolerance: float = 0.2,
    limit: int = 5,
) -> List[RecipeBase]:
    """
    Находит рецепты, близкие к заданным КБЖУ

    Args:
        target_calories: Целевые калории на 100г
        target_protein: Целевой белок на 100г (опционально)
        target_fat: Целевые жиры на 100г (опционально)
        target_carbs: Целевые углеводы на 100г (опционально)
        tolerance: Допустимое отклонение (20% по умолчанию)
        limit: Максимальное количество результатов

    Returns:
        Список рецептов, отсортированных по близости к целевым значениям
    """
    # Получаем все рецепты
    all_recipes = await RecipeBase.all()

    if not all_recipes:
        return []

    # Вычисляем "расстояние" до каждого рецепта
    recipes_with_distance = []

    cal_min = target_calories * (1 - tolerance)
    cal_max = target_calories * (1 + tolerance)

    for recipe in all_recipes:
        # Проверяем, входит ли рецепт в диапазон калорий
        if not (cal_min <= recipe.calories_per_100g <= cal_max):
            continue

        # Вычисляем "расстояние" (чем меньше, тем ближе к целевым значениям)
        distance = 0.0

        # Калории (вес 1.0)
        cal_diff = abs(recipe.calories_per_100g - target_calories) / target_calories
        distance += cal_diff * 1.0

        # Белки (вес 0.8)
        if target_protein is not None and target_protein > 0:
            protein_diff = (
                abs(recipe.protein_per_100g - target_protein) / target_protein
            )
            distance += protein_diff * 0.8

        # Жиры (вес 0.6)
        if target_fat is not None and target_fat > 0:
            fat_diff = abs(recipe.fat_per_100g - target_fat) / target_fat
            distance += fat_diff * 0.6

        # Углеводы (вес 0.7)
        if target_carbs is not None and target_carbs > 0:
            carbs_diff = abs(recipe.carbs_per_100g - target_carbs) / target_carbs
            distance += carbs_diff * 0.7

        recipes_with_distance.append((recipe, distance))

    # Сортируем по расстоянию (меньше = лучше)
    recipes_with_distance.sort(key=lambda x: x[1])

    # Возвращаем топ N рецептов
    return [recipe for recipe, _ in recipes_with_distance[:limit]]


async def find_recipes_by_tags(tags: List[str], limit: int = 10) -> List[RecipeBase]:
    """
    Находит рецепты по тегам

    Args:
        tags: Список тегов для поиска
        limit: Максимальное количество результатов

    Returns:
        Список рецептов
    """
    recipes = []

    for tag in tags:
        # Ищем рецепты, содержащие тег (регистронезависимо)
        found = await RecipeBase.filter(tags__icontains=tag).limit(limit)
        recipes.extend(found)

    # Убираем дубликаты
    unique_recipes = []
    seen_ids = set()

    for recipe in recipes:
        if recipe.id not in seen_ids:
            unique_recipes.append(recipe)
            seen_ids.add(recipe.id)

    return unique_recipes[:limit]


async def find_recipes_by_title(query: str, limit: int = 10) -> List[RecipeBase]:
    """
    Находит рецепты по названию

    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов

    Returns:
        Список рецептов
    """
    return await RecipeBase.filter(title__icontains=query).limit(limit)


async def get_random_recipes(limit: int = 5) -> List[RecipeBase]:
    """
    Возвращает случайные рецепты

    Args:
        limit: Количество рецептов

    Returns:
        Список случайных рецептов
    """
    # Tortoise ORM не поддерживает RANDOM() напрямую
    # Получаем все рецепты и выбираем случайные
    import random

    all_recipes = await RecipeBase.all()

    if len(all_recipes) <= limit:
        return all_recipes

    return random.sample(all_recipes, limit)


def format_recipe_for_display(recipe: RecipeBase) -> str:
    """
    Форматирует рецепт для отображения пользователю

    Args:
        recipe: Объект рецепта

    Returns:
        Отформатированная строка
    """
    text = f"🍽 <b>{recipe.title}</b>\n\n"

    if recipe.tags:
        text += f"🏷 Теги: {recipe.tags}\n"

    if recipe.cooking_time:
        text += f"⏱ Время: {recipe.cooking_time}\n"

    if recipe.difficulty:
        text += f"📊 Сложность: {recipe.difficulty}\n"

    text += f"\n{recipe.kbzhu_formatted}\n\n"

    text += f"<b>Ингредиенты:</b>\n{recipe.ingredients}\n\n"

    text += f"<b>Приготовление:</b>\n{recipe.instructions}\n"

    if recipe.notes:
        text += f"\n<i>{recipe.notes}</i>"

    return text
