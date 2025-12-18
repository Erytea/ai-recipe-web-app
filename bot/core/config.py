from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Настройки приложения"""

    # OpenAI API
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite://db.sqlite3?charset=utf8")

    # Web App Settings
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-min-32-chars-12345678901234567890123456789012")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # JWT Settings
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-change-in-production-min-32-chars-12345678901234567890123456789012")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # CORS Settings - пустая строка означает localhost только
    cors_origins: str = os.getenv("CORS_ORIGINS", "")

    # File Upload Settings
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_image_types: str = "image/jpeg,image/png,image/webp"

    # Redis (для продакшена)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    model_config = SettingsConfigDict(
        env_file=None,  # Отключаем загрузку .env файла
        case_sensitive=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # В production режиме проверяем критические настройки
        if not self.debug:
            # Проверяем только если переменные установлены явно (не значения по умолчанию)
            if os.getenv("SECRET_KEY") and self.secret_key == "dev-secret-key-change-in-production-min-32-chars-12345678901234567890123456789012":
                print("⚠️  WARNING: SECRET_KEY все еще имеет значение по умолчанию!")
            if os.getenv("JWT_SECRET_KEY") and self.jwt_secret_key == "dev-jwt-secret-key-change-in-production-min-32-chars-12345678901234567890123456789012":
                print("⚠️  WARNING: JWT_SECRET_KEY все еще имеет значение по умолчанию!")
            if os.getenv("CORS_ORIGINS") and not self.cors_origins.strip():
                print("⚠️  WARNING: CORS_ORIGINS не настроен!")

            # Критическая проверка - если SECRET_KEY не установлен вообще
            if not os.getenv("SECRET_KEY"):
                print("⚠️  WARNING: SECRET_KEY не установлен! Используется значение по умолчанию.")
            if not os.getenv("JWT_SECRET_KEY"):
                print("⚠️  WARNING: JWT_SECRET_KEY не установлен! Используется значение по умолчанию.")

            print("✅ Production mode activated")


# Глобальный экземпляр настроек
settings = Settings()