"""
Зависимости для веб-приложения
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import hashlib

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from bot.core.config import settings
from bot.core.models import User

# Настройки для паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer токен для API
security = HTTPBearer(auto_error=False)


def _prehash_password(password: str) -> str:
    """
    Предварительно хеширует пароль через SHA-256 для обхода ограничения bcrypt в 72 байта.
    Это позволяет использовать пароли любой длины без ограничений.
    """
    # Хешируем пароль через SHA-256 (всегда 32 байта, что меньше 72 байт)
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return sha256_hash


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль"""
    # Предварительно хешируем пароль через SHA-256 перед проверкой через bcrypt
    prehashed = _prehash_password(plain_password)
    return pwd_context.verify(prehashed, hashed_password)


def get_password_hash(password: str) -> str:
    """Хэширует пароль"""
    # Предварительно хешируем пароль через SHA-256 перед bcrypt
    # Это позволяет использовать пароли любой длины
    prehashed = _prehash_password(password)
    return pwd_context.hash(prehashed)


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



