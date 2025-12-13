from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Настройки приложения"""

    # OpenAI API
    openai_api_key: str

    # Database
    database_url: str = "sqlite://db.sqlite3"

    # Web App Settings
    secret_key: str  # Обязательная переменная окружения
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", 8000))

    # JWT Settings
    jwt_secret_key: str  # Обязательная переменная окружения
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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Проверяем, что секретные ключи не являются значениями по умолчанию
        if self.secret_key == "your-secret-key-change-in-production":
            raise ValueError("SECRET_KEY должен быть установлен в переменных окружения!")
        if self.jwt_secret_key == "jwt-secret-key":
            raise ValueError("JWT_SECRET_KEY должен быть установлен в переменных окружения!")


# Глобальный экземпляр настроек
settings = Settings()