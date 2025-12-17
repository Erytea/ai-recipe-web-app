"""
Зависимости для веб-приложения
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import hashlib
import base64
import bcrypt

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from bot.core.config import settings
from bot.core.models import User

# Bearer токен для API
security = HTTPBearer(auto_error=False)


def _prehash_password(password: str) -> str:
    """
    Предварительно хеширует пароль через SHA-256 для обхода ограничения bcrypt в 72 байта.
    Использует base64 кодирование для компактности (32 байта SHA-256 = 44 символа base64).
    """
    # Кодируем пароль в UTF-8 байты
    password_bytes = password.encode('utf-8')

    # Хешируем пароль через SHA-256 (всегда 32 байта)
    sha256_digest = hashlib.sha256(password_bytes).digest()

    # Кодируем в base64 (32 байта = 44 символа base64, что меньше 72 байт в UTF-8)
    # Используем base64.urlsafe_b64encode для избежания проблем с символами
    prehashed = base64.urlsafe_b64encode(sha256_digest).decode('ascii')

    # Гарантируем, что результат не превышает 72 байта в UTF-8
    prehashed_bytes = prehashed.encode('utf-8')
    if len(prehashed_bytes) > 72:
        # Усекаем строку до 72 байт, но сохраняем валидность UTF-8
        truncated_bytes = prehashed_bytes[:72]
        # Находим последний полный UTF-8 символ
        while truncated_bytes:
            try:
                truncated_str = truncated_bytes.decode('utf-8')
                prehashed = truncated_str
                break
            except UnicodeDecodeError:
                # Убираем последний байт, который сломал UTF-8 символ
                truncated_bytes = truncated_bytes[:-1]

    return prehashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль"""
    try:
        # Предварительно хешируем пароль через SHA-256 перед проверкой через bcrypt
        prehashed = _prehash_password(plain_password)
        prehashed_bytes = prehashed.encode('utf-8')

        # Проверяем новый формат (base64)
        if bcrypt.checkpw(prehashed_bytes, hashed_password.encode('utf-8')):
            return True

        # Обратная совместимость: пробуем старый метод (hex) для существующих паролей
        password_bytes = plain_password.encode('utf-8')
        sha256_digest = hashlib.sha256(password_bytes).digest()
        prehashed_hex = sha256_digest.hex()
        return bcrypt.checkpw(prehashed_hex.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Хэширует пароль"""
    # Сначала убеждаемся, что пароль не пустой
    if not password:
        raise ValueError("Пароль не может быть пустым")

    # Предварительно хешируем пароль через SHA-256 перед bcrypt
    # Это позволяет использовать пароли любой длины и гарантирует <72 байт
    prehashed = _prehash_password(password)
    prehashed_bytes = prehashed.encode('utf-8')

    # Хешируем через bcrypt напрямую
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(prehashed_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создает JWT токен"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


async def get_user_by_email(email: str) -> Optional[User]:
    """Получает пользователя по email"""
    return await User.get_or_none(email=email, is_active=True)


async def authenticate_user(email: str, password: str) -> Optional[User]:
    """Аутентифицирует пользователя"""
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user_optional(
    access_token: Optional[str] = Cookie(None, alias="access_token")
) -> Optional[User]:
    """
    Получает текущего пользователя из cookie (опционально)
    Используется для шаблонов, где пользователь может быть не авторизован
    """
    if not access_token:
        return None

    try:
        payload = jwt.decode(
            access_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        user = await User.get_or_none(id=UUID(user_id), is_active=True)
        return user
    except (JWTError, ValueError):
        return None


async def get_current_user(
    access_token: Optional[str] = Cookie(None, alias="access_token")
) -> User:
    """
    Получает текущего пользователя из cookie (обязательно)
    Вызывает исключение если пользователь не авторизован
    """
    user = await get_current_user_optional(access_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Получает пользователя из Bearer токена (для API)
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не предоставлен токен авторизации"
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен"
        )

    user = await User.get_or_none(id=UUID(user_id), is_active=True)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )

    return user



