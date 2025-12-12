"""
Скрипт для импорта рецептов в базу данных
"""

import asyncio
import sys
from tortoise import Tortoise

from bot.core.config import settings
from bot.core.models import RecipeBase
from bot.services.recipe_parser import parse_recipe_text, validate_recipe_data


async def init_db():
    """Инициализация базы данных"""
    await Tortoise.init(db_url=settings.database_url, modules={"models": ["models"]})
    await Tortoise.generate_schemas()
    print("✅ База данных инициализирована")


async def close_db():
    """Закрытие соединения с базой данных"""
    await Tortoise.close_connections()


async def import_recipe_from_text(recipe_text: str) -> bool:
    """
    Импортирует один рецепт из текста в базу данных

    Args:
        recipe_text: Текст рецепта

    Returns:
        True, если импорт успешен
    """
    # Парсим текст
    recipe_data = parse_recipe_text(recipe_text)

    if not recipe_data:
        print("❌ Не удалось распарсить рецепт")
        return False

    # Валидируем данные
    if not validate_recipe_data(recipe_data):
        print("❌ Данные рецепта неполные")
        print(f"   Название: {recipe_data.get('title', 'НЕ НАЙДЕНО')}")
        return False

    # Проверяем, нет ли уже такого рецепта
    existing = await RecipeBase.filter(title=recipe_data["title"]).first()

    if existing:
        print(f"⚠️  Рецепт '{recipe_data['title']}' уже существует")
        return False

    # Создаём запись в БД
    recipe = await RecipeBase.create(**recipe_data)

    print(f"✅ Добавлен рецепт: {recipe.title}")
    print(f"   КБЖУ: {recipe.kbzhu_formatted}")

    return True


async def import_recipes_interactive():
    """
    Интерактивный режим импорта рецептов
    """
    print("\n" + "=" * 60)
    print("📖 ИМПОРТ РЕЦЕПТОВ В БАЗУ ДАННЫХ")
    print("=" * 60)
    print()
    print("Вставьте текст рецепта и нажмите Enter.")
    print("Для завершения ввода введите строку: END")
    print("Для выхода введите: QUIT")
    print()
    print("-" * 60)

    await init_db()

    total_imported = 0

    try:
        while True:
            print("\n📝 Вставьте рецепт (завершите строкой END):")
            print()

            # Читаем многострочный ввод
            lines = []
            while True:
                try:
                    line = input()
                    if line.strip() == "END":
                        break
                    if line.strip() == "QUIT":
                        print("\n👋 Выход из программы...")
                        return total_imported
                    lines.append(line)
                except EOFError:
                    break

            if not lines:
                print("⚠️  Пустой ввод, попробуйте ещё раз")
                continue

            recipe_text = "\n".join(lines)

            # Импортируем рецепт
            success = await import_recipe_from_text(recipe_text)
            if success:
                total_imported += 1

            print(f"\n📊 Всего импортировано рецептов: {total_imported}")
            print("-" * 60)

    finally:
        await close_db()
        print(f"\n✅ Импорт завершён. Добавлено рецептов: {total_imported}")


async def import_from_file(filepath: str):
    """
    Импорт рецептов из файла

    Args:
        filepath: Путь к файлу с рецептами
    """
    await init_db()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Разделяем рецепты (предполагаем, что они разделены пустыми
        # строками или числами)
        recipes = []
        current_recipe = []

        for line in content.split("\n"):
            # Если строка - просто число (разделитель между рецептами)
            if line.strip().isdigit() and len(line.strip()) <= 2:
                if current_recipe:
                    recipes.append("\n".join(current_recipe))
                    current_recipe = []
            else:
                current_recipe.append(line)

        # Добавляем последний рецепт
        if current_recipe:
            recipes.append("\n".join(current_recipe))

        print(f"📚 Найдено рецептов в файле: {len(recipes)}")
        print()

        imported_count = 0
        for i, recipe_text in enumerate(recipes, 1):
            print(f"\n[{i}/{len(recipes)}] Импортирую рецепт...")
            success = await import_recipe_from_text(recipe_text)
            if success:
                imported_count += 1

        print("\n✅ Импорт завершён!")
        print(f"   Всего рецептов: {len(recipes)}")
        print(f"   Успешно импортировано: {imported_count}")

    except FileNotFoundError:
        print(f"❌ Файл не найден: {filepath}")
    except Exception as e:
        print(f"❌ Ошибка при импорте: {e}")
    finally:
        await close_db()


async def show_stats():
    """Показывает статистику по базе рецептов"""
    await init_db()

    try:
        total = await RecipeBase.all().count()
        print("\n📊 Статистика базы рецептов:")
        print(f"   Всего рецептов: {total}")

        if total > 0:
            # Последние добавленные
            recent = await RecipeBase.all().limit(5).order_by("-created_at")
            print("\n   Последние 5 рецептов:")
            for recipe in recent:
                print(f"   - {recipe.title}")
    finally:
        await close_db()


async def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "file" and len(sys.argv) > 2:
            # Импорт из файла
            filepath = sys.argv[2]
            await import_from_file(filepath)
        elif command == "stats":
            # Показать статистику
            await show_stats()
        else:
            print("Использование:")
            print("  python import_recipes.py          " "- интерактивный режим")
            print("  python import_recipes.py file <путь>  " "- импорт из файла")
            print("  python import_recipes.py stats    " "- показать статистику")
    else:
        # Интерактивный режим
        await import_recipes_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем")
