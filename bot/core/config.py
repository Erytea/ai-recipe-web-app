from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Настройки приложения"""

    # OpenAI API
    openai_api_key: str = ""  # Необязателен для development

    # Database
    database_url: str = "sqlite://db.sqlite3?charset=utf8"

    # Web App Settings
    secret_key: str = "production-secret-key-change-in-production-min-32-chars-for-development-only-this-is-a-long-enough-key"  # Для debug режима
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", 8000))

    # JWT Settings
    jwt_secret_key: str = "production-jwt-secret-key-change-in-production-this-is-a-long-enough-key-for-testing"  # Для debug режима
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # CORS Settings
    cors_origins: str = "*"

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
        # В production проверяем, что используются не debug ключи
        if not self.debug:
            if self.secret_key.startswith("debug-"):
                raise ValueError("SECRET_KEY должен быть изменен для production!")
            if self.jwt_secret_key.startswith("debug-"):
                raise ValueError("JWT_SECRET_KEY должен быть изменен для production!")


# Глобальный экземпляр настроек
settings = Settings()