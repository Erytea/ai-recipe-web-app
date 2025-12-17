# План реализации недостающего функционала

## Анализ проекта

Проект представляет собой веб-приложение для создания рецептов с помощью ИИ на базе FastAPI. Есть базовая структура, но отсутствует значительная часть функционала.

### Архитектура баз рецептов

В проекте есть **две отдельные базы рецептов**:

1. **RecipeBase (общая база)** - доступна всем пользователям
   - Рецепты импортируются администраторами через скрипты
   - Используется для поиска готовых рецептов
   - Нет связи с конкретным пользователем
   - Доступна всем авторизованным пользователям

2. **Recipe (личная база)** - персональные рецепты каждого пользователя
   - Создаются через ИИ (загрузка фото продуктов)
   - Привязаны к конкретному пользователю через ForeignKey
   - Доступны только владельцу
   - Хранят исходные данные (фото, ингредиенты, параметры КБЖУ)

**Важно:** Нужно добавить функционал копирования рецептов из общей базы в личную коллекцию пользователя.

---

## 1. РОУТЫ И API

### 1.1. Роуты для работы с базой рецептов (RecipeBase)
**Статус:** ❌ Отсутствует полностью

**Зачем это нужно:**
Сейчас пользователи могут создавать свои рецепты через ИИ, но не могут искать готовые рецепты из общей базы данных `RecipeBase`. Это важная функция - пользователи должны иметь возможность:
- Найти готовый рецепт по калориям, тегам или названию
- Просмотреть рецепт из общей базы
- **Сохранить понравившийся рецепт в свою личную коллекцию** (копировать из RecipeBase в Recipe)

**Важно:** Общая база (RecipeBase) доступна всем авторизованным пользователям, но каждый пользователь видит только свои личные рецепты (Recipe).

**Что нужно:**
- `GET /recipes/base` - список всех рецептов из общей базы (доступна всем)
- `GET /recipes/base/search` - поиск рецептов по КБЖУ, тегам, названию
- `GET /recipes/base/{recipe_id}` - просмотр конкретного рецепта из общей базы
- `GET /recipes/base/random` - случайные рецепты из общей базы
- `POST /recipes/base/{recipe_id}/save` - **сохранить рецепт из общей базы в свою личную коллекцию**
- `GET /recipes` - список личных рецептов пользователя (только свои)
- `GET /recipes/{recipe_id}` - просмотр личного рецепта (только свой)

**Как реализовать:**

1. **Добавить роуты в `bot/web/routes/recipes.py`:**
```python
from bot.services.recipe_search import (
    find_recipes_by_kbzhu,
    find_recipes_by_tags,
    find_recipes_by_title,
    get_random_recipes
)
from bot.core.models import RecipeBase

@router.get("/base", response_class=HTMLResponse)
async def recipes_base_list(
    request: Request,
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
):
    """Список всех рецептов из базы"""
    # Получить рецепты с пагинацией
    offset = (page - 1) * limit
    recipes = await RecipeBase.all().offset(offset).limit(limit)
    total = await RecipeBase.all().count()
    
    return templates.TemplateResponse(
        "recipes/base/index.html",
        {
            "request": request,
            "user": current_user,
            "recipes": recipes,
            "page": page,
            "total_pages": (total + limit - 1) // limit
        }
    )

@router.get("/base/search", response_class=HTMLResponse)
async def recipes_base_search_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница поиска рецептов"""
    return templates.TemplateResponse(
        "recipes/base/search.html",
        {"request": request, "user": current_user}
    )

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
    
    if search_type == "kbzhu" and calories:
        recipes = await find_recipes_by_kbzhu(
            target_calories=calories,
            target_protein=protein,
            target_fat=fat,
            target_carbs=carbs
        )
    elif search_type == "tags" and tags:
        tag_list = [t.strip() for t in tags.split(",")]
        recipes = await find_recipes_by_tags(tag_list)
    elif search_type == "title" and query:
        recipes = await find_recipes_by_title(query)
    
    return templates.TemplateResponse(
        "recipes/base/index.html",
        {
            "request": request,
            "user": current_user,
            "recipes": recipes,
            "search_query": query
        }
    )

@router.get("/base/{recipe_id}", response_class=HTMLResponse)
async def recipes_base_view(
    request: Request,
    recipe_id: str,
    current_user: User = Depends(get_current_user)
):
    """Просмотр рецепта из базы"""
    try:
        recipe = await RecipeBase.get(id=recipe_id)
        return templates.TemplateResponse(
            "recipes/base/view.html",
            {
                "request": request,
                "user": current_user,
                "recipe": recipe
            }
        )
    except RecipeBase.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден")

@router.get("/base/random", response_class=HTMLResponse)
async def recipes_base_random(
    request: Request,
    current_user: User = Depends(get_current_user),
    limit: int = 5
):
    """Случайные рецепты"""
    recipes = await get_random_recipes(limit=limit)
    return templates.TemplateResponse(
        "recipes/base/index.html",
        {
            "request": request,
            "user": current_user,
            "recipes": recipes,
            "is_random": True
        }
    )

@router.post("/base/{recipe_id}/save")
async def save_recipe_to_personal(
    request: Request,
    recipe_id: str,
    current_user: User = Depends(get_current_user)
):
    """Сохранить рецепт из общей базы в личную коллекцию пользователя"""
    try:
        # Получаем рецепт из общей базы
        base_recipe = await RecipeBase.get(id=recipe_id)
        
        # Проверяем, не сохранен ли уже этот рецепт пользователем
        # (можно добавить поле source_recipe_base_id в Recipe для отслеживания)
        existing = await Recipe.filter(
            user=current_user,
            recipe_text__contains=base_recipe.title
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Этот рецепт уже сохранен в вашей коллекции"
            )
        
        # Создаем личный рецепт на основе рецепта из базы
        # Преобразуем данные RecipeBase в формат Recipe
        personal_recipe = await Recipe.create(
            user=current_user,
            photo_file_id="",  # У рецептов из базы может не быть фото
            ingredients_detected=base_recipe.ingredients,
            clarifications=f"Скопировано из общей базы: {base_recipe.title}",
            target_calories=int(base_recipe.calories_per_100g * 2),  # Примерно для порции 200г
            target_protein=base_recipe.protein_per_100g * 2,
            target_fat=base_recipe.fat_per_100g * 2,
            target_carbs=base_recipe.carbs_per_100g * 2,
            greens_weight=0,  # Не указано в базе
            recipe_text=json.dumps({
                "recipe_title": base_recipe.title,
                "ingredients_with_weights": [
                    {"name": ing.strip(), "weight_g": 100} 
                    for ing in base_recipe.ingredients.split("\n") if ing.strip()
                ],
                "cooking_steps": base_recipe.instructions.split("\n\n") if base_recipe.instructions else [],
                "calculated_nutrition": {
                    "calories": base_recipe.calories_per_100g * 2,
                    "protein_g": base_recipe.protein_per_100g * 2,
                    "fat_g": base_recipe.fat_per_100g * 2,
                    "carbs_g": base_recipe.carbs_per_100g * 2
                }
            }, ensure_ascii=False),
            calculated_calories=base_recipe.calories_per_100g * 2,
            calculated_protein=base_recipe.protein_per_100g * 2,
            calculated_fat=base_recipe.fat_per_100g * 2,
            calculated_carbs=base_recipe.carbs_per_100g * 2
        )
        
        return RedirectResponse(
            url=f"/recipes/{personal_recipe.id}",
            status_code=302
        )
        
    except RecipeBase.DoesNotExist:
        raise HTTPException(status_code=404, detail="Рецепт не найден в базе")
```

2. **Создать шаблоны:**
   - `templates/recipes/base/index.html` - список рецептов из общей базы
     - Показать карточки рецептов
     - Кнопка "Сохранить в мою коллекцию" на каждом рецепте
     - Указать, что это общая база (доступна всем)
   - `templates/recipes/base/search.html` - форма поиска с полями для КБЖУ, тегов, названия
   - `templates/recipes/base/view.html` - просмотр рецепта из общей базы
     - Показать полную информацию о рецепте
     - Кнопка "Сохранить в мою коллекцию"
     - Указать источник (общая база)

3. **Обновить существующие шаблоны:**
   - `templates/recipes/index.html` - список ЛИЧНЫХ рецептов пользователя
     - Заголовок: "Мои рецепты" (личная коллекция)
     - Показать только рецепты текущего пользователя
     - Кнопка "Создать новый рецепт через ИИ"
     - Ссылка "Поиск в общей базе рецептов"
   - `templates/recipes/view.html` - просмотр ЛИЧНОГО рецепта
     - Показать, что это личный рецепт
     - Если рецепт скопирован из базы - показать источник

**Файлы для создания/изменения:**
- `bot/web/routes/recipes.py` - добавить новые роуты для общей базы и сохранения в коллекцию
- `templates/recipes/base/index.html` - список рецептов из общей базы
- `templates/recipes/base/search.html` - форма поиска
- `templates/recipes/base/view.html` - просмотр рецепта из общей базы
- `templates/recipes/index.html` - обновить (показать, что это личные рецепты)
- `templates/recipes/view.html` - обновить (показать источник, если скопирован)

**Зависимости:**
- Использовать функции из `bot/services/recipe_search.py` (уже реализованы)
- Модели `RecipeBase` и `Recipe` уже разделены правильно

**Важные моменты:**
- Общая база (RecipeBase) - доступна всем авторизованным пользователям
- Личная база (Recipe) - каждый пользователь видит только свои рецепты
- При сохранении рецепта из базы создается новый Recipe, связанный с пользователем
- Можно добавить поле `source_recipe_base_id` в модель Recipe для отслеживания источника

---

### 1.2. Роуты для управления профилем
**Статус:** ❌ Частично отсутствует

**Зачем это нужно:**
Пользователи должны иметь возможность изменять свои данные (имя, email) и пароль. Сейчас есть только просмотр профиля, но нет возможности его редактировать.

**Что есть:**
- `GET /profile` - просмотр профиля (роут есть в `bot/web/routes/main.py`, но шаблон отсутствует)

**Что нужно добавить:**
- `GET /profile/edit` - форма редактирования профиля
- `POST /profile/edit` - обновление данных профиля
- `GET /profile/change-password` - форма смены пароля
- `POST /profile/change-password` - смена пароля

**Как реализовать:**

1. **Добавить роуты в `bot/web/routes/main.py`:**
```python
from bot.web.dependencies import get_password_hash, verify_password

@router.get("/profile/edit", response_class=HTMLResponse)
async def profile_edit_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница редактирования профиля"""
    return templates.TemplateResponse(
        "profile/edit.html",
        {
            "request": request,
            "user": current_user,
            "title": "Редактировать профиль"
        }
    )

@router.post("/profile/edit")
async def profile_edit(
    request: Request,
    current_user: User = Depends(get_current_user),
    username: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None),
    email: str = Form(None)
):
    """Обновление данных профиля"""
    # Проверка, что email не занят другим пользователем
    if email and email != current_user.email:
        existing = await User.get_or_none(email=email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email уже используется"
            )
        current_user.email = email
    
    if username:
        current_user.username = username
    if first_name:
        current_user.first_name = first_name
    if last_name:
        current_user.last_name = last_name
    
    await current_user.save()
    
    return RedirectResponse(url="/profile", status_code=302)

@router.get("/profile/change-password", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Страница смены пароля"""
    return templates.TemplateResponse(
        "profile/change_password.html",
        {
            "request": request,
            "user": current_user,
            "title": "Сменить пароль"
        }
    )

@router.post("/profile/change-password")
async def change_password(
    request: Request,
    current_user: User = Depends(get_current_user),
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Смена пароля"""
    # Проверка старого пароля
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="Неверный текущий пароль"
        )
    
    # Проверка совпадения новых паролей
    if new_password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Новые пароли не совпадают"
        )
    
    # Проверка минимальной длины пароля
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Пароль должен быть не менее 8 символов"
        )
    
    # Обновление пароля
    current_user.password_hash = get_password_hash(new_password)
    await current_user.save()
    
    return RedirectResponse(url="/profile", status_code=302)
```

2. **Создать шаблоны:**
   - `templates/profile.html` - отобразить данные пользователя, статистику (количество рецептов, планов), ссылки на редактирование
   - `templates/profile/edit.html` - форма с полями: username, first_name, last_name, email
   - `templates/profile/change_password.html` - форма с полями: старый пароль, новый пароль, подтверждение

**Файлы для создания:**
- `templates/profile.html` - просмотр профиля
- `templates/profile/edit.html` - редактирование профиля
- `templates/profile/change_password.html` - смена пароля
- `bot/web/routes/main.py` - добавить новые роуты (уже есть базовый роут `/profile`)

---

### 1.3. API endpoints для мобильных приложений
**Статус:** ⚠️ Частично реализовано

**Что есть:**
- `/auth/api/login` - вход
- `/auth/api/register` - регистрация

**Что нужно добавить:**
- `GET /api/recipes` - список рецептов пользователя (JSON)
- `GET /api/recipes/{recipe_id}` - детали рецепта (JSON)
- `POST /api/recipes` - создание рецепта через API
- `GET /api/meal-plans` - список планов питания (JSON)
- `GET /api/recipes/base` - поиск в базе рецептов (JSON)

**Файлы для изменения:**
- `bot/web/routes/recipes.py` - добавить API endpoints
- `bot/web/routes/meal_plans.py` - добавить API endpoints

---

## 2. ШАБЛОНЫ (TEMPLATES)

### 2.1. Шаблоны для планов питания (Meal Plans)
**Статус:** ❌ Полностью отсутствуют

**Зачем это нужно:**
Роуты для планов питания уже реализованы, но без шаблонов пользователи не могут использовать эту функцию. Нужно создать HTML страницы для отображения и создания планов питания.

**Файлы для создания:**

1. **`templates/meal_plans/index.html`** - список планов питания
   - Показать все планы питания пользователя
   - Карточки с краткой информацией (дата создания, калории за день)
   - Ссылки на просмотр каждого плана
   - Кнопка "Создать новый план"
   - Использовать дизайн как в `templates/recipes/index.html`

2. **`templates/meal_plans/view.html`** - просмотр плана питания
   - Отобразить все приемы пищи из плана
   - Для каждого приема: название, продукты с весом, КБЖУ
   - Итоговое КБЖУ за день
   - Фото продуктов (если есть)
   - Использовать дизайн как в `templates/recipes/view.html`

3. **`templates/meal_plans/create/step1.html`** - загрузка фото
   - Форма загрузки изображения
   - Инструкции для пользователя
   - Кнопка "Загрузить фото"
   - Использовать дизайн как в `templates/recipes/create/step1.html`

4. **`templates/meal_plans/create/step2.html`** - анализ продуктов
   - Показать обнаруженные ингредиенты
   - Показать неопределенные продукты (uncertainties)
   - Поле для уточнений (clarifications)
   - Кнопка "Продолжить"
   - Использовать дизайн как в `templates/recipes/create/step2.html`

5. **`templates/meal_plans/create/step3.html`** - параметры питания
   - Форма с полями:
     - Количество приемов пищи (1-6)
     - Целевые калории за день
     - Целевой белок за день (г)
     - Целевые жиры за день (г)
     - Целевые углеводы за день (г)
     - Количество растительности за день (г)
   - Кнопка "Создать план питания"
   - Использовать дизайн как в `templates/recipes/create/step3.html`

**Как создать шаблоны:**
- Скопировать структуру из `templates/recipes/` и адаптировать под планы питания
- Использовать те же стили и компоненты Bootstrap
- Следовать дизайну из `layout.html` (красная тема)

**Примечание:** Роуты уже реализованы в `bot/web/routes/meal_plans.py`, но шаблоны отсутствуют. Без них приложение будет выдавать ошибки при попытке открыть страницы планов питания.

---

### 2.2. Шаблоны для профиля
**Статус:** ❌ Полностью отсутствуют

**Файлы для создания:**
- `templates/profile.html` - просмотр профиля
- `templates/profile/edit.html` - редактирование профиля
- `templates/profile/change_password.html` - смена пароля

---

### 2.3. Шаблоны для базы рецептов
**Статус:** ❌ Полностью отсутствуют

**Файлы для создания:**
- `templates/recipes/base/index.html` - список рецептов из базы
- `templates/recipes/base/search.html` - форма поиска
- `templates/recipes/base/view.html` - просмотр рецепта из базы

---

### 2.4. Общие шаблоны
**Статус:** ❌ Отсутствуют

**Файлы для создания:**
- `templates/about.html` - страница "О приложении"
- `templates/error.html` - страница ошибки (используется в `main.py`)

---

## 3. БАЗА ДАННЫХ И МИГРАЦИИ

### 3.1. Настройка миграций Aerich
**Статус:** ❌ Не настроено

**Зачем это нужно:**
Миграции позволяют безопасно изменять структуру базы данных при обновлении моделей. Без миграций при изменении моделей нужно будет вручную изменять БД или удалять её и создавать заново, что приведет к потере данных.

**Что нужно:**
1. Инициализировать Aerich
2. Создать первую миграцию
3. Настроить автоматические миграции при запуске

**Как реализовать:**

1. **Создать файл `pyproject.toml` с конфигурацией Aerich** (если его нет или нужно добавить):
```toml
[tool.aerich]
tortoise_orm = "bot.core.models.Tortoise"
location = "./migrations"
src_folder = "./"
```

2. **Инициализировать Aerich:**
```bash
# В корне проекта
aerich init -t bot.core.models.Tortoise
```
Это создаст папку `migrations/` и файл `aerich.ini`

3. **Создать первую миграцию:**
```bash
aerich init-db
```
Это создаст файлы миграций на основе текущих моделей в `bot/core/models.py`

4. **Применить миграции:**
```bash
aerich upgrade
```

5. **В будущем, при изменении моделей:**
```bash
# Создать новую миграцию
aerich migrate --name "описание изменений"

# Применить миграцию
aerich upgrade
```

6. **Настроить автоматические миграции при запуске** (опционально):
В `main.py` в функции `lifespan` можно добавить:
```python
import subprocess
# При запуске приложения
subprocess.run(["aerich", "upgrade"], check=False)
```

**Файлы для создания/изменения:**
- `pyproject.toml` - добавить конфигурацию Aerich (если нужно)
- `.env` - проверить DATABASE_URL (должен быть указан)
- `aerich.ini` - создастся автоматически при инициализации
- `migrations/` - папка с миграциями (создастся автоматически)

**Важно:**
- Не коммитить файл БД `db.sqlite3` в git (добавить в `.gitignore`)
- Коммитить папку `migrations/` в git
- Перед применением миграций в продакшене делать бэкап БД

---

### 3.2. Проверка моделей
**Статус:** ✅ Модели реализованы

**Что проверить:**
- Все связи между моделями корректны
- Индексы для полей поиска (если нужны)
- Валидация данных на уровне моделей

---

## 4. ВАЛИДАЦИЯ И ОБРАБОТКА ОШИБОК

### 4.1. Валидация форм
**Статус:** ⚠️ Частично реализовано

**Зачем это нужно:**
Валидация защищает от некорректных данных, которые могут привести к ошибкам или проблемам безопасности. Например, загрузка слишком большого файла может перегрузить сервер, а слабый пароль - скомпрометировать аккаунт.

**Что нужно добавить:**

1. **Валидация загружаемых изображений (размер, формат)**
   - Проверка размера файла (максимум из `settings.max_upload_size`)
   - Проверка типа файла (только изображения: jpeg, png, webp)
   - Проверка расширения файла

2. **Валидация параметров КБЖУ (диапазоны значений)**
   - Калории: от 0 до 10000 (разумный максимум)
   - Белки/жиры/углеводы: от 0 до 1000 г
   - Проверка, что сумма не превышает разумных значений

3. **Валидация email при регистрации** (уже есть в Pydantic через EmailStr)

4. **Валидация пароля (минимальная длина, сложность)**
   - Минимум 8 символов
   - Опционально: требовать буквы и цифры

**Как реализовать:**

1. **В `bot/web/routes/recipes.py` и `meal_plans.py` - валидация файлов:**
```python
from bot.core.config import settings
import os

@router.post("/create/step1")
async def process_photo_upload(
    request: Request,
    current_user: User = Depends(get_current_user),
    photo: UploadFile = File(...)
):
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
    
    # Читаем файл для проверки размера
    content = await photo.read()
    file_size = len(content)
    
    # Проверка размера
    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {settings.max_upload_size / 1024 / 1024:.1f} МБ"
        )
    
    # Сбрасываем позицию файла для дальнейшего использования
    await photo.seek(0)
    
    # ... остальной код сохранения файла
```

2. **В `bot/web/routes/recipes.py` и `meal_plans.py` - валидация КБЖУ:**
```python
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
    
    # ... остальной код
```

3. **В `bot/web/routes/auth.py` - валидация пароля:**
```python
import re

def validate_password(password: str) -> tuple[bool, str]:
    """Проверяет пароль и возвращает (валиден, сообщение об ошибке)"""
    if len(password) < 8:
        return False, "Пароль должен быть не менее 8 символов"
    
    if len(password) > 128:
        return False, "Пароль слишком длинный (максимум 128 символов)"
    
    # Опционально: требовать буквы и цифры
    if not re.search(r'[A-Za-z]', password):
        return False, "Пароль должен содержать хотя бы одну букву"
    
    if not re.search(r'[0-9]', password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    
    return True, ""

@router.post("/register")
async def register(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    # ...
):
    # Валидация пароля
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    # ... остальной код
```

**Файлы для изменения:**
- `bot/web/routes/recipes.py` - добавить валидацию файлов и КБЖУ
- `bot/web/routes/meal_plans.py` - добавить валидацию файлов и КБЖУ
- `bot/web/routes/auth.py` - улучшить валидацию пароля

---

### 4.2. Обработка ошибок
**Статус:** ⚠️ Частично реализовано

**Что есть:**
- Глобальный обработчик исключений в `main.py`
- Базовые HTTPException

**Что нужно улучшить:**
- Специфичные обработчики для разных типов ошибок
- Логирование ошибок
- Пользовательские сообщения об ошибках
- Обработка ошибок OpenAI API (rate limits, timeout)

**Файлы для изменения:**
- `main.py` - улучшить обработчик ошибок
- `bot/services/openai_service.py` - добавить обработку ошибок API

---

## 5. БЕЗОПАСНОСТЬ

### 5.1. Защита от CSRF
**Статус:** ❌ Не реализовано

**Зачем это нужно:**
CSRF (Cross-Site Request Forgery) атаки позволяют злоумышленникам выполнять действия от имени пользователя без его ведома. Например, если пользователь залогинен и откроет вредоносный сайт, тот может отправить запрос на изменение пароля. CSRF токены защищают от таких атак.

**Что нужно:**
- Добавить CSRF токены для форм
- Проверка CSRF токенов в POST запросах

**Как реализовать:**

**Вариант 1: Использовать библиотеку `fastapi-csrf-protect`**

1. **Установить библиотеку:**
```bash
pip install fastapi-csrf-protect
```

2. **Добавить в `main.py`:**
```python
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

# Настройка CSRF
@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings(secret_key=settings.secret_key)

# Обработчик ошибок CSRF
@app.exception_handler(CsrfProtectError)
async def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error": "Ошибка CSRF защиты. Пожалуйста, обновите страницу.",
            "title": "Ошибка безопасности"
        },
        status_code=403
    )
```

3. **В шаблонах добавить токен:**
```html
<!-- В начале формы -->
{% set csrf_token = csrf_protect.generate_csrf_token() %}
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
```

4. **В роутах проверять токен:**
```python
from fastapi_csrf_protect import CsrfProtect

@router.post("/create/step1")
async def process_photo_upload(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    current_user: User = Depends(get_current_user),
    photo: UploadFile = File(...)
):
    await csrf_protect.validate_csrf(request)
    # ... остальной код
```

**Вариант 2: Собственная реализация (проще, но менее надежно)**

1. **Создать утилиту в `bot/web/dependencies.py`:**
```python
import secrets
from fastapi import Request, HTTPException

def generate_csrf_token() -> str:
    """Генерирует CSRF токен"""
    return secrets.token_urlsafe(32)

async def get_csrf_token(request: Request) -> str:
    """Получает CSRF токен из сессии или создает новый"""
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = generate_csrf_token()
    return request.session["csrf_token"]

async def validate_csrf_token(request: Request, token: str):
    """Проверяет CSRF токен"""
    session_token = await get_csrf_token(request)
    if not secrets.compare_digest(session_token, token):
        raise HTTPException(
            status_code=403,
            detail="Неверный CSRF токен"
        )
```

2. **В шаблонах:**
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
```

3. **В роутах:**
```python
@router.post("/create/step1")
async def process_photo_upload(
    request: Request,
    current_user: User = Depends(get_current_user),
    photo: UploadFile = File(...),
    csrf_token: str = Form(...)
):
    await validate_csrf_token(request, csrf_token)
    # ... остальной код
```

**Рекомендация:** Использовать вариант 1 с библиотекой, так как она более надежна и протестирована.

**Библиотека:** `fastapi-csrf-protect` или собственная реализация

---

### 5.2. Защита загружаемых файлов
**Статус:** ⚠️ Частично реализовано

**Что есть:**
- Проверка content-type

**Что нужно добавить:**
- Проверка размера файла (есть в config, но не используется)
- Проверка расширения файла
- Сканирование на вирусы (опционально)
- Ограничение типов файлов (только изображения)

**Файлы для изменения:**
- `bot/web/routes/recipes.py` - улучшить валидацию файлов
- `bot/web/routes/meal_plans.py` - улучшить валидацию файлов

---

### 5.3. Rate Limiting
**Статус:** ❌ Не реализовано

**Что нужно:**
- Ограничение количества запросов на пользователя
- Ограничение количества запросов к OpenAI API
- Защита от DDoS атак

**Библиотека:** `slowapi` или `fastapi-limiter`

---

## 6. УЛУЧШЕНИЯ UX/UI

### 6.1. Навигация
**Статус:** ⚠️ Частично реализовано

**Что нужно добавить:**
- Хлебные крошки (breadcrumbs)
- Кнопка "Назад" в формах
- Индикатор прогресса в многошаговых формах

---

### 6.2. Обратная связь пользователю
**Статус:** ⚠️ Частично реализовано

**Зачем это нужно:**
Пользователи должны знать, успешно ли выполнилось их действие (создание рецепта, изменение профиля и т.д.). Без обратной связи пользователь не понимает, что произошло - успешно ли действие или произошла ошибка.

**Что нужно добавить:**
- Flash сообщения (успех, ошибка) - временные сообщения, которые показываются один раз
- Индикаторы загрузки при обработке запросов - показывать, что запрос обрабатывается
- Подтверждение действий (удаление, изменение) - предотвращает случайные действия

**Как реализовать:**

1. **Flash сообщения через cookies:**

**Создать утилиту в `bot/web/dependencies.py`:**
```python
from fastapi import Response
from typing import Optional

def set_flash_message(response: Response, message: str, message_type: str = "success"):
    """Устанавливает flash сообщение в cookie"""
    response.set_cookie(
        key="flash_message",
        value=message,
        max_age=5,  # 5 секунд
        httponly=False  # Нужно читать в JavaScript
    )
    response.set_cookie(
        key="flash_type",
        value=message_type,  # success, error, warning, info
        max_age=5,
        httponly=False
    )

def get_flash_message(request: Request) -> Optional[tuple[str, str]]:
    """Получает flash сообщение из cookie"""
    message = request.cookies.get("flash_message")
    message_type = request.cookies.get("flash_type", "success")
    if message:
        return (message, message_type)
    return None
```

**В роутах использовать:**
```python
@router.post("/profile/edit")
async def profile_edit(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    # ...
):
    try:
        # ... обновление профиля
        set_flash_message(response, "Профиль успешно обновлен", "success")
        return RedirectResponse(url="/profile", status_code=302)
    except Exception as e:
        set_flash_message(response, f"Ошибка: {str(e)}", "error")
        return RedirectResponse(url="/profile/edit", status_code=302)
```

**В шаблоне `layout.html` добавить отображение:**
```html
{% if flash_message %}
<div class="alert alert-{{ flash_type }} alert-dismissible fade show" role="alert">
    {{ flash_message }}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
<script>
    // Удалить cookie после показа
    document.cookie = "flash_message=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    document.cookie = "flash_type=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
</script>
{% endif %}
```

2. **Индикаторы загрузки:**

**В шаблонах форм добавить:**
```html
<form id="recipe-form" onsubmit="showLoading()">
    <!-- поля формы -->
    <button type="submit" id="submit-btn">
        <span id="btn-text">Создать рецепт</span>
        <span id="btn-spinner" class="spinner-border spinner-border-sm d-none" role="status">
            <span class="visually-hidden">Загрузка...</span>
        </span>
    </button>
</form>

<script>
function showLoading() {
    document.getElementById('btn-text').classList.add('d-none');
    document.getElementById('btn-spinner').classList.remove('d-none');
    document.getElementById('submit-btn').disabled = true;
}
</script>
```

3. **Подтверждение действий:**

**В шаблонах добавить:**
```html
<button onclick="confirmDelete()" class="btn btn-danger">Удалить</button>

<script>
function confirmDelete() {
    if (confirm('Вы уверены, что хотите удалить этот рецепт?')) {
        // Выполнить удаление
        fetch('/recipes/123/delete', {method: 'DELETE'})
            .then(() => window.location.href = '/recipes');
    }
}
</script>
```

**Библиотека:** Использовать cookies или session для flash сообщений. Для более продвинутых функций можно использовать `starlette-sessions` или `fastapi-sessions`.

---

### 6.3. Адаптивность
**Статус:** ✅ Используется Bootstrap

**Что проверить:**
- Все формы адаптивны
- Изображения корректно отображаются на мобильных
- Навигация работает на мобильных устройствах

---

## 7. ТЕСТИРОВАНИЕ

### 7.1. Unit тесты
**Статус:** ❌ Отсутствуют

**Что нужно:**
- Тесты для сервисов (openai_service, recipe_search, nutrition_database)
- Тесты для моделей
- Тесты для валидации

**Файлы для создания:**
- `tests/test_services.py`
- `tests/test_models.py`
- `tests/test_validation.py`

---

### 7.2. Integration тесты
**Статус:** ⚠️ Есть базовый файл

**Что нужно:**
- Тесты для роутов (auth, recipes, meal_plans)
- Тесты для API endpoints
- Тесты для работы с БД

**Файлы для изменения:**
- `tests/test_integration.py` - расширить существующие тесты

---

## 8. ДОКУМЕНТАЦИЯ

### 8.1. API документация
**Статус:** ✅ FastAPI автоматически генерирует

**Что проверить:**
- Все endpoints имеют описания
- Примеры запросов/ответов
- Схемы данных (Pydantic models)

---

### 8.2. Документация для разработчиков
**Статус:** ⚠️ Частично есть

**Что нужно добавить:**
- Описание архитектуры (есть в docs/ARCHITECTURE.md)
- Инструкции по развертыванию (есть в DEPLOYMENT_GUIDE.md)
- Руководство по добавлению новых функций
- Описание переменных окружения

---

## 9. ПРОИЗВОДИТЕЛЬНОСТЬ

### 9.1. Кэширование
**Статус:** ❌ Не реализовано

**Что нужно:**
- Кэширование результатов поиска рецептов
- Кэширование данных из базы продуктов
- Кэширование статических страниц

**Библиотека:** `aiocache` или `redis`

---

### 9.2. Оптимизация запросов к БД
**Статус:** ⚠️ Нужна проверка

**Что проверить:**
- Использование select_related/prefetch_related в Tortoise ORM
- Индексы на часто используемых полях
- Оптимизация запросов поиска

---

## 10. ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ

### 10.1. Экспорт рецептов
**Статус:** ❌ Не реализовано

**Что нужно:**
- Экспорт рецепта в PDF
- Экспорт рецепта в текстовый формат
- Экспорт списка рецептов

---

### 10.2. Избранные рецепты
**Статус:** ❌ Не реализовано

**Что нужно:**
- Модель FavoriteRecipe
- Роуты для добавления/удаления из избранного
- Страница с избранными рецептами

---

### 10.3. Комментарии и оценки
**Статус:** ❌ Не реализовано

**Что нужно:**
- Модель Comment/Rating
- Роуты для комментариев
- Отображение комментариев на странице рецепта

---

## ПРИОРИТЕТЫ РЕАЛИЗАЦИИ

### Критично (для базовой функциональности):
1. ✅ Создать недостающие шаблоны для meal_plans
2. ✅ Создать шаблоны для профиля
3. ✅ Создать роуты для работы с общей базой рецептов (RecipeBase)
   - ✅ Роут для сохранения рецепта из базы в личную коллекцию
   - ✅ Разделить отображение общей и личной баз
4. ✅ Настроить миграции Aerich
5. ✅ Создать шаблоны about.html и error.html

### Важно (для полноценной работы):
6. ✅ Улучшить валидацию форм
7. ✅ Добавить обработку ошибок
8. ✅ Добавить CSRF защиту
9. ✅ Добавить flash сообщения
10. ✅ Создать API endpoints для мобильных приложений

### Желательно (для улучшения):
11. ⚠️ Добавить rate limiting
12. ⚠️ Добавить кэширование
13. ⚠️ Написать тесты
14. ⚠️ Добавить экспорт рецептов
15. ⚠️ Добавить избранные рецепты

---

## ОЦЕНКА ВРЕМЕНИ

- **Критичные задачи:** 8-12 часов
- **Важные задачи:** 6-10 часов
- **Желательные задачи:** 10-15 часов

**Итого:** 24-37 часов работы

---

## ЗАМЕТКИ

- Все шаблоны должны следовать дизайну из `layout.html` (красная тема RINGO)
- Использовать Bootstrap 5 для UI компонентов
- Следовать принципам REST API для новых endpoints
- Документировать все новые функции

---

## РАЗДЕЛЕНИЕ БАЗ РЕЦЕПТОВ: ОБЩАЯ БАЗА И ЛИЧНАЯ КОЛЛЕКЦИЯ

### Архитектура: Общая база vs Личная коллекция

**Текущая структура:**
- `RecipeBase` - общая база рецептов (без связи с пользователем)
- `Recipe` - личные рецепты пользователей (с ForeignKey на User)

**Как это работает:**

1. **Общая база (RecipeBase):**
   - Импортируется администраторами через скрипты (`scripts/import_recipes.py`)
   - Доступна всем авторизованным пользователям
   - Используется для поиска готовых рецептов
   - Роуты: `/recipes/base/*`
   - **Нет связи с конкретным пользователем** - все видят одни и те же рецепты

2. **Личная коллекция (Recipe):**
   - Создается пользователем через ИИ (загрузка фото продуктов)
   - Или копируется из общей базы (новый функционал)
   - Доступна только владельцу (фильтр по `user`)
   - Роуты: `/recipes/*` (без `/base`)
   - **Привязана к пользователю** - каждый видит только свои рецепты

**Функционал "Сохранить в коллекцию":**

Когда пользователь находит рецепт в общей базе и хочет сохранить его в свою коллекцию:

1. Пользователь открывает рецепт из общей базы (`/recipes/base/{recipe_id}`)
2. Нажимает кнопку "Сохранить в мою коллекцию"
3. Создается новый `Recipe` на основе `RecipeBase`:
   - Рецепт привязывается к пользователю через `user` ForeignKey
   - Данные преобразуются из формата RecipeBase в формат Recipe
   - Сохраняется информация об источнике (опционально)
4. Пользователь видит рецепт в своей личной коллекции (`/recipes`)

**Пример кода для сохранения:**

```python
@router.post("/base/{recipe_id}/save")
async def save_recipe_to_personal(
    request: Request,
    recipe_id: str,
    current_user: User = Depends(get_current_user)
):
    """Сохранить рецепт из общей базы в личную коллекцию"""
    # Получаем рецепт из общей базы
    base_recipe = await RecipeBase.get(id=recipe_id)
    
    # Проверяем, не сохранен ли уже
    existing = await Recipe.filter(
        user=current_user,
        recipe_text__contains=base_recipe.title
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Этот рецепт уже в вашей коллекции"
        )
    
    # Создаем личный рецепт
    personal_recipe = await Recipe.create(
        user=current_user,
        photo_file_id="",  # У рецептов из базы может не быть фото
        ingredients_detected=base_recipe.ingredients,
        clarifications=f"Скопировано из общей базы: {base_recipe.title}",
        # ... остальные поля
    )
    
    return RedirectResponse(url=f"/recipes/{personal_recipe.id}", status_code=302)
```

**Улучшение (опционально):**

Можно добавить в модель `Recipe` поле для отслеживания источника:

```python
# В bot/core/models.py в класс Recipe добавить:
source_recipe_base = fields.ForeignKeyField(
    "models.RecipeBase",
    related_name="saved_recipes",
    null=True,
    on_delete=fields.SET_NULL,
    description="Рецепт из общей базы, из которого был создан этот личный рецепт"
)
```

Это позволит:
- Показывать пользователю, откуда взят рецепт
- Предотвращать дубликаты при сохранении (проверять по `source_recipe_base`)
- Отслеживать популярность рецептов из базы (сколько раз сохранен)
- Показывать в общей базе: "Сохранено X пользователями"

**Навигация в интерфейсе:**

1. **Главная страница `/recipes`:**
   - Заголовок: "Мои рецепты" (личная коллекция)
   - Показать только рецепты текущего пользователя
   - Кнопка "Создать новый рецепт через ИИ"
   - Ссылка "Поиск в общей базе рецептов" → `/recipes/base`

2. **Страница общей базы `/recipes/base`:**
   - Заголовок: "Общая база рецептов" (доступна всем)
   - Показать все рецепты из RecipeBase
   - Кнопка "Сохранить в мою коллекцию" на каждом рецепте
   - Ссылка "Мои рецепты" → `/recipes`

3. **Просмотр рецепта из базы `/recipes/base/{id}`:**
   - Показать полную информацию
   - Кнопка "Сохранить в мою коллекцию"
   - Указать источник: "Из общей базы рецептов"

4. **Просмотр личного рецепта `/recipes/{id}`:**
   - Показать полную информацию
   - Если скопирован из базы - показать: "Источник: общая база"
   - Кнопка "Удалить из коллекции" (опционально)

**Важно:**
- Общая база доступна всем авторизованным пользователям
- Личная коллекция доступна только владельцу
- При сохранении рецепта из базы создается копия в личной коллекции
- Исходный рецепт в базе остается неизменным

---

## ДОПОЛНИТЕЛЬНЫЕ ОБЪЯСНЕНИЯ

### Почему важно делать в таком порядке?

1. **Сначала шаблоны, потом роуты** - потому что роуты уже частично есть, но без шаблонов они не работают
2. **Миграции БД** - нужно настроить сразу, чтобы не потерять данные при изменениях
3. **Валидация и безопасность** - критично для продакшена, но можно делать параллельно с основным функционалом
4. **Тесты и оптимизация** - можно делать в последнюю очередь, когда основной функционал готов

### Как тестировать каждую задачу?

1. **Шаблоны:** Открыть страницу в браузере, проверить отображение
2. **Роуты:** Отправить HTTP запрос (через браузер или curl), проверить ответ
3. **Валидация:** Попробовать отправить некорректные данные, проверить ошибки
4. **Безопасность:** Попробовать обойти защиту (например, отправить запрос без CSRF токена)

### Что делать, если что-то не работает?

1. Проверить логи приложения (в консоли или файле)
2. Проверить, что все зависимости установлены (`pip install -r requirements.txt`)
3. Проверить переменные окружения в `.env`
4. Проверить, что база данных создана и доступна
5. Проверить, что все файлы на месте (особенно шаблоны)

### Полезные команды для разработки

```bash
# Запуск приложения
python main.py

# Или через uvicorn
uvicorn main:app --reload

# Проверка синтаксиса Python
python -m py_compile bot/web/routes/*.py

# Проверка шаблонов (если есть валидатор)
# Обычно проверяется визуально в браузере

# Просмотр логов
tail -f logs/app.log  # если логи пишутся в файл
```

