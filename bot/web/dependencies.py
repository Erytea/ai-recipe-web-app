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


def _prehash_password(password: str) -> bytes:
    """
    Предварительно хеширует пароль через SHA-256 для обхода ограничения bcrypt в 72 байта.
    Возвращает байты (не строку), чтобы гарантировать правильную обработку.
    """
    # Кодируем пароль в UTF-8 байты
    password_bytes = password.encode('utf-8')
    
    # Хешируем пароль через SHA-256 (всегда 32 байта, что меньше 72 байт)
    sha256_digest = hashlib.sha256(password_bytes).digest()
    
    # Возвращаем байты напрямую (32 байта)
    return sha256_digest


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль"""
    try:
        # Предварительно хешируем пароль через SHA-256 перед проверкой через bcrypt
        # Преобразуем байты в hex строку для совместимости с bcrypt
        prehashed_bytes = _prehash_password(plain_password)
        prehashed = prehashed_bytes.hex()  # hexdigest всегда 64 символа = 64 байта в UTF-8
        return pwd_context.verify(prehashed, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Хэширует пароль"""
    # Сначала убеждаемся, что пароль не пустой
    if not password:
        raise ValueError("Пароль не может быть пустым")
    
    # Предварительно хешируем пароль через SHA-256 перед bcrypt
    # Это позволяет использовать пароли любой длины
    prehashed_bytes = _prehash_password(password)
    # Преобразуем байты в hex строку (64 символа = 64 байта в UTF-8, что меньше 72)
    prehashed = prehashed_bytes.hex()
    
    # Дополнительная проверка: убеждаемся, что длина в байтах не превышает 72
    prehashed_bytes_utf8 = prehashed.encode('utf-8')
    if len(prehashed_bytes_utf8) > 72:
        # Это не должно произойти, но на всякий случай усекаем
        prehashed = prehashed_bytes_utf8[:72].decode('utf-8', errors='ignore')
    
    # Финальная проверка перед передачей в bcrypt
    final_bytes = prehashed.encode('utf-8')
    if len(final_bytes) > 72:
        # Если все равно превышает, усекаем до 72 байт
        final_bytes = final_bytes[:72]
        prehashed = final_bytes.decode('utf-8', errors='ignore')
    
    try:
        return pwd_context.hash(prehashed)
    except ValueError as e:
        # Если все равно возникает ошибка о длине, используем более короткий хеш
        if "72" in str(e) or "bytes" in str(e).lower():
            # Используем только первые 32 байта хеша (16 hex символов)
            short_hash = prehashed[:16]
            return pwd_context.hash(short_hash)
        raise


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



