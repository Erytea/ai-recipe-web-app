#!/usr/bin/env python3
"""
Скрипт для создания администратора на Railway
Запускается при развертывании для инициализации админа
"""

import asyncio
import os
from bot.core.models import User, init_db, close_db
from bot.web.dependencies import get_password_hash
from bot.core.config import settings


async def create_initial_admin():
    """Создает начального администратора если его нет"""

    await init_db(settings.database_url)

    try:
        # Проверяем, есть ли уже админы
        existing_admins = await User.filter(is_admin=True).count()
        if existing_admins > 0:
            print("✅ Администратор уже существует")
            return

        # Создаем администратора
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_username = os.getenv("ADMIN_USERNAME", "admin")

        # Проверяем, существует ли пользователь с таким email
        existing = await User.get_or_none(email=admin_email)
        if existing:
            # Делаем существующего пользователя админом
            existing.is_admin = True
            await existing.save()
            print(f"✅ Существующий пользователь {admin_email} назначен администратором")
        else:
            # Создаем нового администратора
            hashed_password = get_password_hash(admin_password)
            admin_user = await User.create(
                email=admin_email,
                password_hash=hashed_password,
                username=admin_username,
                first_name="Администратор",
                last_name="Системы",
                is_admin=True,
                is_active=True
            )
            print(f"✅ Создан новый администратор: {admin_email}")

        print("\n" + "="*50)
        print("🔑 Данные для входа в админку:")
        print(f"   📧 Email: {admin_email}")
        print(f"   🔒 Пароль: {admin_password}")
        print(f"   👤 Логин: {admin_username}")
        print("="*50)
        print("🚀 После входа в админку вы сможете:")
        print("   • Управлять пользователями")
        print("   • Просматривать рецепты")
        print("   • Видеть статистику")
        print("   • Назначать других админов")

    except Exception as e:
        print(f"❌ Ошибка создания администратора: {e}")
        raise
    finally:
        await close_db()


if __name__ == "__main__":
    print("🚀 Инициализация администратора для Railway...")
    asyncio.run(create_initial_admin())
    print("✅ Готово!")
