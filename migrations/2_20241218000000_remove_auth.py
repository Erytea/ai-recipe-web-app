"""
Remove authentication tables and user_id from recipes
"""
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Удаляем внешний ключ из recipes перед удалением users
        ALTER TABLE "recipes" DROP COLUMN "user_id";

        -- Удаляем внешний ключ из meal_plans перед удалением users
        ALTER TABLE "meal_plans" DROP COLUMN "user_id";

        -- Удаляем таблицы
        DROP TABLE IF EXISTS "meal_plans";
        DROP TABLE IF EXISTS "users";
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Восстанавливаем таблицы (обратная миграция не поддерживается)
        -- Это удаление без возможности восстановления
    """
