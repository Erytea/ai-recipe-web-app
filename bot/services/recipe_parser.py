"""
Парсер для импорта рецептов из текстового формата
"""

import re
from typing import Dict, Optional


def parse_recipe_text(text: str) -> Optional[Dict]:
    """
    Парсит рецепт из текстового формата

    Args:
        text: Текст рецепта

    Returns:
        Словарь с данными рецепта или None, если не удалось распарсить
    """
    lines = text.strip().split("\n")

    if not lines:
        return None

    recipe_data = {
        "title": "",
        "tags": None,
        "cooking_time": None,
        "difficulty": None,
        "calories_per_100g": 0.0,
        "protein_per_100g": 0.0,
        "fat_per_100g": 0.0,
        "carbs_per_100g": 0.0,
        "ingredients": "",
        "instructions": "",
        "notes": None,
    }

    # Извлекаем название (первая непустая строка)
    title_idx = 0
    while title_idx < len(lines) and not lines[title_idx].strip():
        title_idx += 1

    if title_idx < len(lines):
        recipe_data["title"] = lines[title_idx].strip()
    else:
        return None

    # Ищем теги
    for i, line in enumerate(lines):
        if line.startswith("Теги:") or line.startswith("теги:"):
            tags = line.split(":", 1)[1].strip()
            recipe_data["tags"] = tags
            break

    # Ищем время приготовления
    for line in lines:
        if "Время приготовления" in line or "время" in line.lower():
            match = re.search(r"~?\s*(\d+)\s*мин", line, re.IGNORECASE)
            if match:
                recipe_data["cooking_time"] = f"~{match.group(1)} мин"
            else:
                time_match = re.search(r":\s*(.+?)(?:\n|$)", line)
                if time_match:
                    recipe_data["cooking_time"] = time_match.group(1).strip()

    # Ищем сложность
    for line in lines:
        if "Сложность" in line or "сложность" in line.lower():
            difficulty_match = re.search(r":\s*(.+?)(?:\n|$)", line, re.IGNORECASE)
            if difficulty_match:
                recipe_data["difficulty"] = difficulty_match.group(1).strip()

    # Ищем КБЖУ
    kbzhu_found = False
    for i, line in enumerate(lines):
        if "КБЖУ на 100" in line or "кбжу на 100" in line.lower():
            # Ищем в следующих строках (пропуская пустые)
            # числа в формате: 178 ккал 17.5/5.5/14.5
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j].strip()
                if not next_line:
                    continue

                # Паттерн: число ккал число/число/число
                match = re.search(
                    r"(\d+(?:\.\d+)?)\s*ккал\s*"
                    r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)",
                    next_line,
                )
                if match:
                    recipe_data["calories_per_100g"] = float(match.group(1))
                    recipe_data["protein_per_100g"] = float(match.group(2))
                    recipe_data["fat_per_100g"] = float(match.group(3))
                    recipe_data["carbs_per_100g"] = float(match.group(4))
                    kbzhu_found = True
                    break
            break

    if not kbzhu_found:
        # Если КБЖУ не найдено, возвращаем None
        return None

    # Извлекаем ингредиенты
    ingredients_start = -1
    ingredients_end = -1

    for i, line in enumerate(lines):
        if line.strip().startswith("Ингредиенты:"):
            ingredients_start = i + 1
        elif (
            ingredients_start != -1
            and ingredients_end == -1
            and (
                line.strip().startswith("Приготовление:")
                or line.strip().startswith("приготовление:")
            )
        ):
            ingredients_end = i
            break

    if ingredients_start != -1:
        if ingredients_end == -1:
            ingredients_end = len(lines)

        ingredients_lines = []
        for i in range(ingredients_start, ingredients_end):
            line = lines[i].strip()
            if line and not line.startswith("Приготовление"):
                ingredients_lines.append(line)

        recipe_data["ingredients"] = "\n".join(ingredients_lines)

    # Извлекаем инструкции приготовления
    instructions_start = -1

    for i, line in enumerate(lines):
        if line.strip().startswith("Приготовление:") or line.strip().startswith(
            "приготовление:"
        ):
            instructions_start = i + 1
            break

    if instructions_start != -1:
        instructions_lines = []
        for i in range(instructions_start, len(lines)):
            line = lines[i].strip()
            # Пропускаем служебные строки
            if (
                line
                and not line.startswith("Приятного")
                and not line.startswith("*")
                and not line.isdigit()
                and line != "0"
            ):
                instructions_lines.append(line)

        recipe_data["instructions"] = "\n\n".join(instructions_lines)

    # Извлекаем заметки (строки начинающиеся с *)
    notes_lines = []
    for line in lines:
        if line.strip().startswith("*"):
            notes_lines.append(line.strip())

    if notes_lines:
        recipe_data["notes"] = "\n".join(notes_lines)

    return recipe_data


def validate_recipe_data(data: Dict) -> bool:
    """
    Проверяет, что все необходимые поля заполнены

    Args:
        data: Словарь с данными рецепта

    Returns:
        True, если данные валидны
    """
    required_fields = [
        "title",
        "calories_per_100g",
        "protein_per_100g",
        "fat_per_100g",
        "carbs_per_100g",
        "ingredients",
        "instructions",
    ]

    for field in required_fields:
        if not data.get(field):
            return False

    return True
