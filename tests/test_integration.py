#!/usr/bin/env python3
"""Комплексное тестирование веб-приложения"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, '.')


async def test_all():
    print("🧪 ТЕСТИРОВАНИЕ ВЕБ-ПРИЛОЖЕНИЯ")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # Тест 1: Импорты
    print("\n1️⃣ Тестирование импортов...")
    try:
        from bot.core.config import settings
        from bot.core.models import User, Recipe, RecipeBase, MealPlan
        from bot.web.routes import auth, recipes, meal_plans, main
        from bot.services.openai_service import openai_service
        from bot.services.recipe_search import find_recipes_by_kbzhu
        from bot.services.recipe_parser import parse_recipe_text
        print("   ✅ Все импорты работают")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Ошибка импортов: {e}")
        tests_failed += 1
        return False

    # Тест 2: Конфигурация
    print("\n2️⃣ Проверка конфигурации...")
    try:
        assert settings.openai_api_key, "OpenAI key не установлен"
        assert settings.database_url, "Database URL не установлен"
        assert settings.secret_key, "Secret key не установлен"
        print(f"   ✅ Конфигурация загружена")
        print(f"   📊 DEBUG: {settings.debug}")
        print(f"   📊 DATABASE: {settings.database_url}")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Ошибка конфигурации: {e}")
        tests_failed += 1

    # Тест 3: База данных
    print("\n3️⃣ Тестирование базы данных...")
    try:
        from tortoise import Tortoise

        await Tortoise.init(
            db_url=settings.database_url,
            modules={'models': ['bot.core.models']}
        )
        await Tortoise.generate_schemas()

        # Статистика
        users = await User.all().count()
        recipes = await Recipe.all().count()
        recipe_base = await RecipeBase.all().count()
        meal_plans = await MealPlan.all().count()

        print(f"   ✅ База данных работает")
        print(f"   📊 Пользователей: {users}")
        print(f"   📊 Рецептов: {recipes}")
        print(f"   📊 Рационов: {meal_plans}")
        print(f"   📊 База рецептов: {recipe_base}")
        tests_passed += 1

    except Exception as e:
        print(f"   ❌ Ошибка БД: {e}")
        tests_failed += 1

    # Тест 4: FastAPI приложение
    print("\n4️⃣ Тестирование FastAPI приложения...")
    try:
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        # Тест health check
        response = client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"

        # Тест главной страницы
        response = client.get("/")
        assert response.status_code == 200
        assert "AI Recipe" in response.text

        print(f"   ✅ FastAPI приложение работает")
        print(f"   📊 Health check: {health_data['status']}")
        tests_passed += 1

    except Exception as e:
        print(f"   ❌ Ошибка FastAPI: {e}")
        tests_failed += 1

    # Тест 5: Поиск рецептов
    print("\n5️⃣ Тестирование поиска рецептов...")
    try:
        from bot.services.recipe_search import (
            find_recipes_by_kbzhu,
            get_random_recipes
        )

        # Случайные рецепты
        random = await get_random_recipes(limit=2)
        print(f"   ✅ Случайные рецепты: {len(random)} шт")

        # Поиск по КБЖУ
        kbzhu = await find_recipes_by_kbzhu(
            target_calories=180,
            tolerance=0.3,
            limit=2
        )
        print(f"   ✅ Поиск по КБЖУ: {len(kbzhu)} шт")
        tests_passed += 1

    except Exception as e:
        print(f"   ❌ Ошибка поиска: {e}")
        tests_failed += 1

    # Тест 6: Парсер
    print("\n6️⃣ Тестирование парсера...")
    try:
        from bot.services.recipe_parser import (
            parse_recipe_text,
            validate_recipe_data
        )

        test_text = """
Тестовый рецепт

КБЖУ на 100 г:
180 ккал 18.0/6.0/15.0

Ингредиенты:
- Курица

Приготовление:
Готовить
"""

        parsed = parse_recipe_text(test_text)
        if parsed and validate_recipe_data(parsed):
            print(f"   ✅ Парсер работает: '{parsed['title']}'")
            tests_passed += 1
        else:
            print(f"   ⚠️ Парсер вернул неполные данные")
            tests_failed += 1

    except Exception as e:
        print(f"   ❌ Ошибка парсера: {e}")
        tests_failed += 1

    # Тест 7: OpenAI Service
    print("\n7️⃣ Тестирование OpenAI Service...")
    try:
        from bot.services.openai_service import openai_service

        # Просто проверяем, что объект создан
        assert openai_service is not None
        assert hasattr(openai_service, 'client')
        print(f"   ✅ OpenAI Service инициализирован")
        tests_passed += 1

    except Exception as e:
        print(f"   ❌ Ошибка OpenAI: {e}")
        tests_failed += 1

    # Тест 8: Статические файлы
    print("\n8️⃣ Проверка статических файлов...")
    try:
        static_dir = Path("static")
        templates_dir = Path("templates")

        assert static_dir.exists(), "Директория static не существует"
        assert templates_dir.exists(), "Директория templates не существует"

        # Создаем директории если нужно
        static_dir.mkdir(exist_ok=True)
        (static_dir / "uploads").mkdir(exist_ok=True)

        print(f"   ✅ Статические директории созданы")
        tests_passed += 1

    except Exception as e:
        print(f"   ❌ Ошибка статических файлов: {e}")
        tests_failed += 1

    # Закрываем соединения
    try:
        await Tortoise.close_connections()
    except:
        pass

    # Итоги
    print("\n" + "=" * 60)
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"   ✅ Пройдено: {tests_passed}")
    print(f"   ❌ Не пройдено: {tests_failed}")
    print(f"   📈 Всего: {tests_passed + tests_failed}")

    if tests_failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\n💡 Веб-приложение готово к работе!")
        return True
    else:
        print(f"\n⚠️ Есть проблемы ({tests_failed} тестов провалено)")
        return False


if __name__ == '__main__':
    success = asyncio.run(test_all())
    sys.exit(0 if success else 1)



