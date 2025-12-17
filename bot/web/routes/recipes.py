"""
Роуты для работы с рецептами
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Response, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bot.core.models import User, Recipe, RecipeBase
from bot.services.openai_service import openai_service
from bot.services.recipe_search import (
    find_recipes_by_kbzhu,
    find_recipes_by_tags,
    find_recipes_by_title,
    get_random_recipes
)
from bot.web.dependencies import get_current_user
from bot.web.flash_messages import get_flash_message, set_flash_message

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

    context = {
        "request": request,
        "user": current_user,
        "title": "Мои рецепты",
        "recipes": recipes
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]

    return templates.TemplateResponse("recipes/index.html", context)


@router.get("/create", response_class=HTMLResponse)
async def create_recipe_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница создания рецепта - шаг 1: загрузка фото"""
    context = {
        "request": request,
        "user": current_user,
        "title": "Создать рецепт - Загрузка фото"
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("recipes/create/step1.html", context)


@router.post("/create/step1")
async def process_photo_upload(
    request: Request,
    current_user: User = Depends(get_current_user),
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

    # Сохраняем фото
    file_extension = os.path.splitext(photo.filename)[1]
    file_name = f"{current_user.id}_recipe_{request.url_for('create_recipe_page').path.replace('/', '_')}{file_extension}"
    file_path = UPLOAD_DIR / file_name

    with open(file_path, "wb") as buffer:
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
    
    response = templates.TemplateResponse("recipes/create/step2.html", context)

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
    context = {
        "request": request,
        "user": current_user,
        "title": "Параметры питания"
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("recipes/create/step3.html", context)


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
        set_flash_message(response, "Рецепт успешно создан!", "success")

        # Очищаем все куки связанные с рецептом
        cleanup_recipe_session(response, str(current_user.id))

        return response

    except Exception as e:
        # В случае ошибки тоже очищаем сессию
        response = RedirectResponse(url="/recipes/create", status_code=302)
        set_flash_message(response, f"Ошибка генерации рецепта: {str(e)}", "error")
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

        context = {
            "request": request,
            "user": current_user,
            "title": recipe_data.get('recipe_title', 'Рецепт'),
            "recipe": recipe,
            "recipe_data": recipe_data
        }
        
        # Получаем flash сообщение
        flash = get_flash_message(request)
        if flash:
            context["flash_message"] = flash[0]
            context["flash_type"] = flash[1]

        return templates.TemplateResponse("recipes/view.html", context)
    except Recipe.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден")


# ===== РОУТЫ ДЛЯ ОБЩЕЙ БАЗЫ РЕЦЕПТОВ (RecipeBase) =====

@router.get("/base", response_class=HTMLResponse)
async def recipes_base_list(
    request: Request,
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
):
    """Список всех рецептов из общей базы"""
    offset = (page - 1) * limit
    recipes = await RecipeBase.all().offset(offset).limit(limit)
    total = await RecipeBase.all().count()
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    context = {
        "request": request,
        "user": current_user,
        "title": "Общая база рецептов",
        "recipes": recipes,
        "page": page,
        "total_pages": total_pages,
        "total": total
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("recipes/base/index.html", context)


@router.get("/base/search", response_class=HTMLResponse)
async def recipes_base_search_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница поиска рецептов"""
    context = {
        "request": request,
        "user": current_user,
        "title": "Поиск рецептов"
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("recipes/base/search.html", context)


@router.post("/base/search")
async def recipes_base_search(
    request: Request,
    current_user: User = Depends(get_current_user),
    search_type: str = Form(...),
    query: str = Form(None),
    calories: float = Form(None),
    protein: float = Form(None),
    fat: float = Form(None),
    carbs: float = Form(None),
    tags: str = Form(None)
):
    """Обработка поиска рецептов"""
    recipes = []
    search_query = query
    
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
    
    context = {
        "request": request,
        "user": current_user,
        "title": "Результаты поиска",
        "recipes": recipes,
        "search_query": search_query,
        "is_search": True
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("recipes/base/index.html", context)


@router.get("/base/random", response_class=HTMLResponse)
async def recipes_base_random(
    request: Request,
    current_user: User = Depends(get_current_user),
    limit: int = 5
):
    """Случайные рецепты из общей базы"""
    recipes = await get_random_recipes(limit=limit)
    
    context = {
        "request": request,
        "user": current_user,
        "title": "Случайные рецепты",
        "recipes": recipes,
        "is_random": True
    }
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    return templates.TemplateResponse("recipes/base/index.html", context)


@router.get("/base/{recipe_id}", response_class=HTMLResponse)
async def recipes_base_view(
    request: Request,
    recipe_id: str,
    current_user: User = Depends(get_current_user)
):
    """Просмотр рецепта из общей базы"""
    try:
        recipe = await RecipeBase.get(id=recipe_id)
        
        # Проверяем, сохранен ли уже этот рецепт в личной коллекции
        saved_in_collection = False
        try:
            saved_recipe = await Recipe.filter(
                user=current_user,
                recipe_text__contains=recipe.title
            ).first()
            if saved_recipe:
                saved_in_collection = True
        except:
            pass
        
        context = {
            "request": request,
            "user": current_user,
            "title": recipe.title,
            "recipe": recipe,
            "saved_in_collection": saved_in_collection
        }
        
        # Получаем flash сообщение
        flash = get_flash_message(request)
        if flash:
            context["flash_message"] = flash[0]
            context["flash_type"] = flash[1]
        
        return templates.TemplateResponse("recipes/base/view.html", context)
    except RecipeBase.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден в базе")


@router.post("/base/{recipe_id}/save")
async def save_recipe_to_personal(
    request: Request,
    response: Response,
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    csrf_token: str = Form(None)
):
    """Сохранить рецепт из общей базы в личную коллекцию пользователя"""
    from bot.web.csrf import require_csrf_token
    
    # Проверка CSRF токена
    require_csrf_token(request, csrf_token)
    
    try:
        # Получаем рецепт из общей базы
        base_recipe = await RecipeBase.get(id=recipe_id)
        
        # Проверяем, не сохранен ли уже этот рецепт пользователем
        existing = await Recipe.filter(
            user=current_user,
            recipe_text__contains=base_recipe.title
        ).first()
        
        if existing:
            response = RedirectResponse(
                url=f"/recipes/{existing.id}",
                status_code=302
            )
            set_flash_message(response, "Этот рецепт уже в твоей коллекции", "info")
            return response
        
        # Преобразуем ингредиенты в список
        ingredients_list = []
        if base_recipe.ingredients:
            for line in base_recipe.ingredients.split("\n"):
                line = line.strip()
                if line and not line.startswith("-") and not line.startswith("*"):
                    # Убираем маркеры списка
                    line = line.lstrip("- *•").strip()
                    if line:
                        ingredients_list.append(line)
        
        # Создаем личный рецепт на основе рецепта из базы
        # Примерный расчет для порции 200г
        portion_weight = 200.0
        multiplier = portion_weight / 100.0
        
        personal_recipe = await Recipe.create(
            user=current_user,
            photo_file_id="",  # У рецептов из базы может не быть фото
            ingredients_detected=json.dumps(ingredients_list, ensure_ascii=False),
            clarifications=f"Скопировано из общей базы: {base_recipe.title}",
            target_calories=int(base_recipe.calories_per_100g * multiplier),
            target_protein=base_recipe.protein_per_100g * multiplier,
            target_fat=base_recipe.fat_per_100g * multiplier,
            target_carbs=base_recipe.carbs_per_100g * multiplier,
            greens_weight=0,  # Не указано в базе
            recipe_text=json.dumps({
                "recipe_title": base_recipe.title,
                "ingredients_with_weights": [
                    {"name": ing, "weight_g": 100} 
                    for ing in ingredients_list[:10]  # Ограничиваем количество
                ],
                "cooking_steps": base_recipe.instructions.split("\n\n") if base_recipe.instructions else [],
                "calculated_nutrition": {
                    "calories": base_recipe.calories_per_100g * multiplier,
                    "protein_g": base_recipe.protein_per_100g * multiplier,
                    "fat_g": base_recipe.fat_per_100g * multiplier,
                    "carbs_g": base_recipe.carbs_per_100g * multiplier
                }
            }, ensure_ascii=False),
            calculated_calories=base_recipe.calories_per_100g * multiplier,
            calculated_protein=base_recipe.protein_per_100g * multiplier,
            calculated_fat=base_recipe.fat_per_100g * multiplier,
            calculated_carbs=base_recipe.carbs_per_100g * multiplier
        )
        
        response = RedirectResponse(
            url=f"/recipes/{personal_recipe.id}",
            status_code=302
        )
        set_flash_message(response, "Рецепт сохранен в твою коллекцию!", "success")
        return response
        
    except RecipeBase.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден в базе")
    except Exception as e:
        response = RedirectResponse(url=f"/recipes/base/{recipe_id}", status_code=302)
        set_flash_message(response, f"Ошибка при сохранении: {str(e)}", "error")
        return response


