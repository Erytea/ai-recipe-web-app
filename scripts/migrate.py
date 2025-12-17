#!/usr/bin/env python3
"""
Скрипт для применения миграций базы данных
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.core.models import TORTOISE_ORM
from tortoise import Tortoise


async def apply_migrations():
    """Применяет все миграции"""
    print("🔄 Применение миграций...")

    # Подключаемся к базе данных и генерируем схемы
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

    print("✅ Схемы базы данных созданы")

    # Создаем запись о миграции в таблице aerich
    try:
        from aerich.models import Aerich
        from tortoise.transactions import in_transaction

        async with in_transaction():
            # Проверяем, есть ли уже запись
            existing = await Aerich.filter(version="0_20241217000000_init", app="models").first()
            if existing:
                print("✅ Миграция 0_20241217000000_init уже применена")
            else:
                # Создаем запись о миграции
                await Aerich.create(
                    version="0_20241217000000_init",
                    app="models",
                    content='{"upgrade": "initial migration"}'
                )
                print("✅ Миграция 0_20241217000000_init зарегистрирована")

    except Exception as e:
        print(f"⚠️ Не удалось зарегистрировать миграцию: {e}")

    await Tortoise.close_connections()


async def check_db_status():
    """Проверяет статус базы данных"""
    print("🔍 Проверка статуса базы данных...")

    await Tortoise.init(config=TORTOISE_ORM)

    try:
        from tortoise.transactions import in_transaction
        async with in_transaction() as conn:
            # Проверяем таблицы
            tables_result = await conn.execute_query("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)

            tables = [row[0] for row in tables_result[1]] if tables_result and tables_result[1] else []
            print(f"📊 Найдено таблиц: {len(tables)}")
            for table in tables:
                print(f"   - {table}")

            # Проверяем миграции
            migrations_result = await conn.execute_query("""
                SELECT version, app FROM aerich ORDER BY version
            """)

            migrations = migrations_result[1] if migrations_result and migrations_result[1] else []
            print(f"📋 Применено миграций: {len(migrations)}")
            for migration in migrations:
                print(f"   - {migration[0]} ({migration[1]})")

    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        asyncio.run(check_db_status())
    else:
        asyncio.run(apply_migrations())
