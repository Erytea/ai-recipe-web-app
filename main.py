"""
AI Recipe Web App - FastAPI приложение
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from tortoise import Tortoise

from bot.core.config import settings
from bot.core.models import init_db, close_db
from bot.web.routes import auth, recipes, meal_plans, main, api, admin
from bot.web.dependencies import get_current_user_optional
from bot.core.models import User

# Настройка логирования
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

# Создаем директории для статических файлов
static_dir = Path("static")
templates_dir = Path("templates")
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# Управление жизненным циклом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Инициализация
    logger.info("Запуск веб-приложения...")
    try:
        await init_db(settings.database_url)
        logger.info("База данных инициализирована успешно")

        # Создаем администратора при первом запуске
        logger.info("Проверка администратора...")
        from bot.core.models import User
        admin_count = await User.filter(is_admin=True).count()
        if admin_count == 0:
            logger.info("Создание начального администратора...")
            from bot.web.dependencies import get_password_hash

            admin_email = os.getenv("ADMIN_EMAIL", "admin@railway.app")
            admin_password = os.getenv("ADMIN_PASSWORD", "secure_admin_password_123")
            admin_username = os.getenv("ADMIN_USERNAME", "admin")

            # Проверяем, существует ли пользователь
            existing = await User.get_or_none(email=admin_email)
            if not existing:
                hashed_password = get_password_hash(admin_password)
                admin_user = await User.create(
                    email=admin_email,
                    password_hash=hashed_password,
                    username=admin_username,
                    first_name="Администратор",
                    last_name="Railway",
                    is_admin=True,
                    is_active=True
                )
                logger.info(f"Создан администратор: {admin_email}")
            else:
                existing.is_admin = True
                await existing.save()
                logger.info(f"Назначен администратор: {admin_email}")
        else:
            logger.info("Администратор уже существует")

    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}", exc_info=True)
        raise

    yield

    # Завершение
    try:
        await close_db()
        logger.info("Веб-приложение остановлено")
    except Exception as e:
        logger.error(f"Ошибка при закрытии базы данных: {e}", exc_info=True)


# Инициализация FastAPI
app = FastAPI(
    title="AI Recipe Web App",
    description="Веб-приложение для создания рецептов с помощью ИИ",
    version="1.0.0",
    lifespan=lifespan,
)

# Настройка CORS
origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# Подключаем роутеры
app.include_router(main.router, tags=["main"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
app.include_router(meal_plans.router, prefix="/meal-plans", tags=["meal-plans"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(api.router, tags=["api"])


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional)
):
    """Главная страница"""
    from bot.web.flash_messages import get_flash_message
    from bot.web.csrf import get_csrf_token, generate_csrf_token, set_csrf_token
    
    context = {
        "request": request,
        "user": current_user,
        "title": "AI Recipe Bot"
    }
    
    # Получаем или генерируем CSRF токен
    csrf_token = get_csrf_token(request)
    if not csrf_token:
        csrf_token = generate_csrf_token()
    context["csrf_token"] = csrf_token
    
    # Получаем flash сообщение
    flash = get_flash_message(request)
    if flash:
        context["flash_message"] = flash[0]
        context["flash_type"] = flash[1]
    
    # Подсчитываем статистику для авторизованного пользователя
    if current_user:
        from bot.core.models import Recipe, MealPlan
        recipes_count = await Recipe.filter(user=current_user).count()
        meal_plans_count = await MealPlan.filter(user=current_user).count()
        context["recipes_count"] = recipes_count
        context["meal_plans_count"] = meal_plans_count
    
    response = templates.TemplateResponse("index.html", context)
    
    # Устанавливаем CSRF токен в cookie если его нет
    if not get_csrf_token(request):
        set_csrf_token(response, csrf_token)
    
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint для мониторинга"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0"
    }


@app.get("/status")
async def app_status():
    """Подробный статус приложения"""
    from bot.core.models import User, Recipe, MealPlan

    try:
        users_count = await User.all().count()
        recipes_count = await Recipe.all().count()
        meal_plans_count = await MealPlan.all().count()

        return {
            "status": "ok",
            "database": "connected",
            "users_count": users_count,
            "recipes_count": recipes_count,
            "meal_plans_count": meal_plans_count,
            "openai_api": "configured" if settings.openai_api_key else "not_configured"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений"""
    logger.warning(f"HTTP исключение: {exc.status_code} - {exc.detail}")
    
    # Для 404 ошибок показываем специальную страницу
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Страница не найдена",
                "title": "404 - Не найдено"
            },
            status_code=404
        )
    
    # Для других HTTP ошибок
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error": exc.detail or "Произошла ошибка",
            "title": f"Ошибка {exc.status_code}"
        },
        status_code=exc.status_code
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    logger.error(f"Необработанное исключение: {exc}", exc_info=True)
    
    # Определяем тип ошибки для более понятного сообщения
    error_message = str(exc)
    if "OpenAI" in str(type(exc)) or "openai" in error_message.lower():
        error_message = "Ошибка при обращении к OpenAI API. Проверь подключение к интернету и попробуй позже."
    elif "database" in error_message.lower() or "sql" in error_message.lower():
        error_message = "Ошибка базы данных. Попробуй позже."
    elif "timeout" in error_message.lower():
        error_message = "Превышено время ожидания. Попробуй еще раз."
    
    try:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": error_message,
                "title": "Ошибка"
            },
            status_code=500
        )
    except Exception:
        # Если даже шаблон ошибки не загрузился, возвращаем простой текст
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            f"Внутренняя ошибка сервера: {error_message}",
            status_code=500
        )




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )