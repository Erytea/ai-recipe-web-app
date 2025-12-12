"""
Полный цикл импорта рецептов из PDF в базу данных
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict

from tortoise import Tortoise

from bot.core.config import settings
from bot.core.models import RecipeBase
from bot.services.pdf_processor import PDFRecipeProcessor


async def init_db():
    """Инициализация базы данных"""
    await Tortoise.init(
        db_url=settings.database_url,
        modules={'models': ['models']}
    )
    await Tortoise.generate_schemas()
    print("✅ База данных инициализирована\n")


async def close_db():
    """Закрытие соединения с базой данных"""
    await Tortoise.close_connections()


async def save_recipes_to_db(recipes: List[Dict]) -> int:
    """
    Сохраняет обработанные рецепты в базу данных
    
    Args:
        recipes: Список словарей с данными рецептов
        
    Returns:
        Количество успешно сохраненных рецептов
    """
    if not recipes:
        print("❌ Нет рецептов для сохранения")
        return 0
    
    print("\n" + "="*70)
    print("💾 СОХРАНЕНИЕ РЕЦЕПТОВ В БАЗУ ДАННЫХ")
    print("="*70 + "\n")
    
    saved_count = 0
    skipped_count = 0
    
    for i, recipe_data in enumerate(recipes, 1):
        try:
            # Проверяем, нет ли уже такого рецепта
            existing = await RecipeBase.filter(
                title=recipe_data['title']
            ).first()
            
            if existing:
                print(f"[{i}/{len(recipes)}] ⚠️  Рецепт уже существует: {recipe_data['title']}")
                skipped_count += 1
                continue
            
            # Создаём запись в БД
            recipe = await RecipeBase.create(**recipe_data)
            
            print(f"[{i}/{len(recipes)}] ✅ Сохранен: {recipe.title}")
            print(f"            КБЖУ: {recipe.kbzhu_formatted}")
            saved_count += 1
            
        except Exception as e:
            print(f"[{i}/{len(recipes)}] ❌ Ошибка при сохранении '{recipe_data.get('title', '???')}': {e}")
    
    print("\n" + "-"*70)
    print(f"\n📊 ИТОГИ:")
    print(f"   Всего рецептов: {len(recipes)}")
    print(f"   Успешно сохранено: {saved_count}")
    print(f"   Пропущено (дубликаты): {skipped_count}")
    print(f"   Ошибок: {len(recipes) - saved_count - skipped_count}")
    print()
    
    return saved_count


async def show_db_stats():
    """Показывает статистику базы данных"""
    total = await RecipeBase.all().count()
    print(f"\n📈 Статистика базы данных:")
    print(f"   Всего рецептов в базе: {total}\n")


async def import_pdf_to_db(pdf_path: str, save_json: bool = True):
    """
    Полный цикл: извлечение из PDF → обработка → сохранение в БД
    
    Args:
        pdf_path: Путь к PDF файлу
        save_json: Сохранять ли промежуточный JSON файл
    """
    # Проверяем файл
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ Файл не найден: {pdf_path}")
        return
    
    if not pdf_file.suffix.lower() == '.pdf':
        print(f"❌ Файл должен быть PDF: {pdf_path}")
        return
    
    print("\n" + "🌟"*35)
    print(" "*15 + "PDF → База данных")
    print("🌟"*35 + "\n")
    
    # Инициализируем БД
    await init_db()
    
    try:
        # Показываем статистику до импорта
        await show_db_stats()
        
        # Обрабатываем PDF
        processor = PDFRecipeProcessor()
        recipes = await processor.process_pdf(pdf_path)
        
        if not recipes:
            print("\n❌ Не удалось извлечь рецепты из PDF")
            return
        
        # Опционально сохраняем JSON
        if save_json:
            import json
            json_path = pdf_file.stem + "_processed.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)
            print(f"💾 Промежуточный результат сохранен в {json_path}\n")
        
        # Сохраняем в БД
        saved = await save_recipes_to_db(recipes)
        
        # Показываем статистику после импорта
        if saved > 0:
            await show_db_stats()
        
        print("🎉 Импорт завершен!\n")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await close_db()


async def import_from_json(json_path: str):
    """
    Импортирует рецепты из ранее сохраненного JSON файла
    
    Args:
        json_path: Путь к JSON файлу
    """
    import json
    
    json_file = Path(json_path)
    if not json_file.exists():
        print(f"❌ Файл не найден: {json_path}")
        return
    
    await init_db()
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            recipes = json.load(f)
        
        print(f"📖 Загружено {len(recipes)} рецептов из {json_path}")
        
        await save_recipes_to_db(recipes)
        await show_db_stats()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await close_db()


def print_usage():
    """Выводит справку по использованию"""
    print("""
📚 ИМПОРТ РЕЦЕПТОВ ИЗ PDF

Использование:
    python import_from_pdf.py <путь_к_pdf>              - импортировать из PDF
    python import_from_pdf.py json <путь_к_json>       - импортировать из JSON
    python import_from_pdf.py --help                    - эта справка

Примеры:
    python import_from_pdf.py recipes.pdf
    python import_from_pdf.py json recipes_processed.json

Процесс работы:
    1. Извлекает текст из PDF
    2. Разделяет на отдельные рецепты через OpenAI
    3. Для каждого рецепта:
       - Очищает текст от мусора
       - Рассчитывает КБЖУ на 100г
       - Структурирует данные
    4. Сохраняет в базу данных

Требования:
    - Файл .env с OPENAI_API_KEY
    - Установленные зависимости (pip install -r requirements.txt)
    """)


async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command in ['--help', '-h', 'help']:
        print_usage()
        return
    
    if command == 'json':
        if len(sys.argv) < 3:
            print("❌ Укажите путь к JSON файлу")
            print("   Пример: python import_from_pdf.py json recipes.json")
            sys.exit(1)
        
        json_path = sys.argv[2]
        await import_from_json(json_path)
    
    else:
        # Считаем что первый аргумент - путь к PDF
        pdf_path = command
        await import_pdf_to_db(pdf_path)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем")


