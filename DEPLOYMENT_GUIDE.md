# 🚀 Руководство по развертыванию AI Recipe Web App

## 📋 Варианты развертывания

### 1. 🌐 **Heroku (Самый простой)**

#### Настройка:
```bash
# 1. Создайте аккаунт на heroku.com
# 2. Установите Heroku CLI

# 3. Логин в Heroku
heroku login

# 4. Создайте приложение
heroku create your-recipe-app-name

# 5. Настройте переменные окружения
heroku config:set OPENAI_API_KEY=your_key_here
heroku config:set SECRET_KEY=your_super_secret_key_32_chars_min
heroku config:set JWT_SECRET_KEY=your_jwt_secret_key
heroku config:set DEBUG=False

# 6. Деплой
git push heroku main
```

#### Особенности Heroku:
- ✅ Бесплатный тариф (ограничения)
- ✅ Автоматический SSL
- ✅ PostgreSQL addon
- ✅ Простое масштабирование
- ❌ Дорогой при росте

---

### 2. 🚂 **Railway (Рекомендую для начала)**

#### Настройка:
```bash
# 1. Создайте аккаунт на railway.app
# 2. Подключите GitHub репозиторий
# 3. Railway автоматически обнаружит Python проект

# 4. Добавьте переменные окружения в Railway dashboard:
OPENAI_API_KEY=your_key_here
SECRET_KEY=your_super_secret_key_32_chars_min
JWT_SECRET_KEY=your_jwt_secret_key
DEBUG=False
DATABASE_URL=postgresql://... # Railway предоставит автоматически
```

#### Преимущества Railway:
- ✅ Бесплатный тариф щедрее Heroku
- ✅ PostgreSQL включен
- ✅ Автоматические деплой с GitHub
- ✅ Современный интерфейс

---

### 3. 🔧 **Render (Хороший баланс)**

#### Настройка:
```bash
# 1. Создайте аккаунт на render.com
# 2. Создайте новый Web Service
# 3. Подключите GitHub репозиторий

# 4. Настройки:
# Build Command: pip install -r requirements.txt
# Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

# 5. Переменные окружения:
OPENAI_API_KEY=your_key_here
SECRET_KEY=your_super_secret_key_32_chars_min
DATABASE_URL=postgresql://... # Render предоставит
DEBUG=False
```

---

### 4. 🖥️ **VPS с Docker (Для контроля)**

#### Подготовка сервера:
```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установите Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Клонируйте проект
git clone https://github.com/yourusername/recipe-app.git
cd recipe-app
```

#### Развертывание:
```bash
# 1. Создайте .env файл
cp env.example .env
# Отредактируйте .env с реальными значениями

# 2. Запустите приложение
docker-compose up -d

# 3. Проверьте статус
docker-compose ps
docker-compose logs web
```

#### Настройка Nginx (опционально):
```bash
# Установите Nginx
sudo apt install nginx

# Скопируйте конфигурацию
sudo cp nginx.conf /etc/nginx/sites-available/recipe-app
sudo ln -s /etc/nginx/sites-available/recipe-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Получите SSL сертификат (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## 🔒 Безопасность для продакшена

### Обязательные настройки:

```bash
# Генерируйте сильные ключи
openssl rand -hex 32  # Для SECRET_KEY
openssl rand -hex 32  # Для JWT_SECRET_KEY

# Настройте CORS для конкретных доменов
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Отключите DEBUG
DEBUG=False
```

### Переменные окружения:
```env
OPENAI_API_KEY=sk-your-openai-key
SECRET_KEY=your-32-char-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://localhost:6379
DEBUG=False
CORS_ORIGINS=https://yourdomain.com
```

---

## 🗄️ База данных

### PostgreSQL на Railway/Render:
- Автоматически предоставляется платформой
- Переменная `DATABASE_URL` уже настроена

### PostgreSQL на VPS:
```bash
# Установите PostgreSQL
sudo apt install postgresql postgresql-contrib

# Создайте базу данных
sudo -u postgres psql
CREATE DATABASE recipe_app;
CREATE USER recipe_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE recipe_app TO recipe_user;
\q

# Обновите DATABASE_URL в .env
DATABASE_URL=postgresql://recipe_user:secure_password@localhost:5432/recipe_app
```

---

## 📊 Мониторинг

### Добавьте в приложение:
```python
# В main.py добавьте эндпоинты для мониторинга
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/metrics")
async def metrics():
    # Добавьте метрики Prometheus если нужно
    pass
```

### Инструменты мониторинга:
- **UptimeRobot**: Бесплатный мониторинг доступности
- **Sentry**: Отслеживание ошибок
- **LogRocket**: Аналитика пользовательского поведения

---

## 🔄 CI/CD Pipeline

### GitHub Actions (бесплатно):
Создайте `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Deploy to Railway/Render/Heroku
      run: echo "Deploy command here"
```

---

## 💰 Ориентировочная стоимость

| Платформа | Бесплатно | Платно ($/мес) |
|-----------|-----------|----------------|
| Heroku | 500MB RAM | $7+ (1GB RAM) |
| Railway | 512MB RAM | $10+ (1GB RAM) |
| Render | 750 часов | $7+ (1GB RAM) |
| DigitalOcean | - | $6+ (1GB VPS) |
| Vultr | - | $5+ (1GB VPS) |

---

## 🚀 Рекомендации

### Для начала:
1. **Railway** - самый простой старт
2. **Render** - хороший баланс цена/качество
3. **VPS** - полный контроль, но требует навыков

### Масштабирование:
- Начинайте с бесплатного тарифа
- Мониторьте использование ресурсов
- Добавляйте Redis для кэширования при росте

### Безопасность:
- Всегда используйте HTTPS
- Регулярно обновляйте зависимости
- Настройте бэкапы базы данных

---

## 🔧 Troubleshooting

### Проблемы с развертыванием:

**Ошибка "Module not found"**:
```bash
pip install -r requirements.txt
```

**База данных не подключается**:
- Проверьте DATABASE_URL
- Убедитесь, что PostgreSQL запущен

**Статические файлы не загружаются**:
- Проверьте настройки static files
- Очистите кэш браузера

**Приложение падает**:
```bash
# Проверьте логи
heroku logs --tail  # Heroku
docker-compose logs web  # Docker
```

---

**Удачного развертывания! 🎉**

Если возникнут проблемы - проверьте логи и документацию платформы.


