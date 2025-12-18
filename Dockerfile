# Используем официальный Python образ
FROM python:3.12-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app

# Устанавливаем рабочую директорию
WORKDIR /home/app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем директории для статических файлов и загрузок
RUN mkdir -p static/uploads static/images

# Меняем владельца файлов
RUN chown -R app:app /home/app

# Переключаемся на пользователя app
USER app

# Открываем порт (Railway будет использовать переменную PORT)
EXPOSE 8000

# Команда запуска через uvicorn для production
# Railway автоматически передает PORT через переменную окружения
# Используем shell-формат для подстановки переменной окружения
# Добавляем логирование для отладки
CMD ["sh", "-c", "echo 'Starting application on port ${PORT:-8000}' && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]




