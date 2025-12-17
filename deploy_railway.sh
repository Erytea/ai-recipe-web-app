#!/bin/bash

# Скрипт быстрого развертывания на Railway
# Использование: ./deploy_railway.sh

echo "🚀 Развертывание AI Recipe Web App на Railway"
echo "=============================================="

# Проверка наличия переменных окружения
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY не настроена"
    echo "Установите переменную окружения: export OPENAI_API_KEY=your_key"
    exit 1
fi

# Генерация секретных ключей
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

echo "🔑 Сгенерированы секретные ключи"

# Переменные для админа (можно изменить)
ADMIN_EMAIL=${ADMIN_EMAIL:-"admin@railway.app"}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-"secure_admin_password_123"}
ADMIN_USERNAME=${ADMIN_USERNAME:-"admin"}

# Создание .env файла для Railway
cat > railway.env << EOF
OPENAI_API_KEY=$OPENAI_API_KEY
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
DEBUG=False
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD=$ADMIN_PASSWORD
ADMIN_USERNAME=$ADMIN_USERNAME
EOF

echo "📝 Создан файл railway.env"

# Инструкции для пользователя
echo ""
echo "📋 Следующие шаги:"
echo "1. Перейдите на https://railway.app"
echo "2. Создайте новый проект"
echo "3. Подключите этот GitHub репозиторий"
echo "4. Добавьте переменные окружения из файла railway.env:"
echo "   - OPENAI_API_KEY"
echo "   - SECRET_KEY"
echo "   - JWT_SECRET_KEY"
echo "   - DEBUG=False"
echo "   - ADMIN_EMAIL (опционально)"
echo "   - ADMIN_PASSWORD (опционально)"
echo "   - ADMIN_USERNAME (опционально)"
echo ""
echo "5. Railway автоматически развернет приложение!"
echo ""
echo "🌐 После развертывания приложение будет доступно по URL от Railway"
echo ""
echo "👑 Данные для входа в админку:"
echo "   📧 Email: $ADMIN_EMAIL"
echo "   🔒 Пароль: $ADMIN_PASSWORD"
echo "   👤 Логин: $ADMIN_USERNAME"
echo ""
echo "⚠️  Не забудьте:"
echo "   - Настроить домен (опционально)"
echo "   - После первого входа измените пароль админа"
echo "   - Настроить бэкапы базы данных"

echo ""
echo "✅ Подготовка к развертыванию завершена!"




