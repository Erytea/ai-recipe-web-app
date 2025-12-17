#!/usr/bin/env python3
"""
Скрипт для настройки администратора на Railway
Запускается вручную после развертывания
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.core.models import User, init_db, close_db
from bot.web.dependencies import get_password_hash
from bot.core.config import settings


async def setup_railway_admin():
    """Настраивает администратора для Railway"""

    print("🚀 Настройка администратора для Railway")
    print("=" * 50)

    # Подключение к БД
    await init_db(settings.database_url)
    print("✅ Подключение к базе данных установлено")

    try:
        # Проверяем существующих админов
        admin_count = await User.filter(is_admin=True).count()
        print(f"📊 Найдено админов: {admin_count}")

        if admin_count > 0:
            print("ℹ️  Администратор уже существует")
            admins = await User.filter(is_admin=True).limit(5)
            for admin in admins:
                print(f"   👑 {admin.email} ({admin.username or 'без логина'})")
            return

        # Получаем данные для админа
        admin_email = os.getenv("ADMIN_EMAIL") or input("📧 Email администратора: ").strip()
        admin_password = os.getenv("ADMIN_PASSWORD") or input("🔒 Пароль администратора: ").strip()
        admin_username = os.getenv("ADMIN_USERNAME") or input("👤 Логин администратора: ").strip()

        if not admin_email or not admin_password:
            print("❌ Email и пароль обязательны!")
            return

        # Проверяем, существует ли пользователь
        existing = await User.get_or_none(email=admin_email)
        if existing:
            print(f"ℹ️  Пользователь {admin_email} уже существует")
            existing.is_admin = True
            existing.username = admin_username
            await existing.save()
            print("✅ Пользователь назначен администратором")
        else:
            # Создаем нового пользователя
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
            print("✅ Администратор создан")

        print("\n" + "="*50)
        print("🎉 Админка настроена!")
        print("🔑 Данные для входа:")
        print(f"   📧 Email: {admin_email}")
        print(f"   🔒 Пароль: {admin_password}")
        print(f"   👤 Логин: {admin_username}")
        print("="*50)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        await close_db()


if __name__ == "__main__":
    # Если переданы аргументы командной строки
    if len(sys.argv) > 1:
        os.environ["ADMIN_EMAIL"] = sys.argv[1] if len(sys.argv) > 1 else ""
        os.environ["ADMIN_PASSWORD"] = sys.argv[2] if len(sys.argv) > 2 else ""
        os.environ["ADMIN_USERNAME"] = sys.argv[3] if len(sys.argv) > 3 else ""

    asyncio.run(setup_railway_admin())
