"""
Хелперы для работы с паролями и JWT.

"""
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, Dict

from jose import JWTError, jwt
from fastapi import Request
from passlib.context import CryptContext

from .database import get_user_by_username

# --- Конфигурация / константы ---
SECRET_KEY: Optional[str] = os.getenv("SECRET_KEY")
ALGORITHM: Optional[str] = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля (passlib).
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Сверяет пароль и хэшированный пароль.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(id_: str) -> str:
    """
    Создаёт JWT токен с полями sub и exp.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_data = {"sub": id_, "exp": expire}
    encoded_jwt = jwt.encode(jwt_data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Аутентификация по username и password.
    Возвращает запись о пользователе из бд или False при неудаче.
    """
    user = await get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Получает текущего пользователя по токену из cookies.
    """
    token = request.cookies.get("access_token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    user = await get_user_by_username(username=username)
    return user