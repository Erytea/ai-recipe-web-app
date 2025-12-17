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
from bot.web.routes import recipes, main, api

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
app.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
app.include_router(api.router, tags=["api"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница"""

    context = {
        "request": request,
        "title": "AI Recipe Bot"
    }

    response = templates.TemplateResponse("index.html", context)

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
    from bot.core.models import Recipe

    try:
        recipes_count = await Recipe.all().count()

        return {
            "status": "ok",
            "database": "connected",
            "recipes_count": recipes_count,
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