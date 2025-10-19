"""
Асинхронная обёртка над запросами к БД (databases).

"""
from typing import Any, Dict, List, Optional

import os

import databases

# --- Конфигурация / константы ---
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
db = databases.Database(DATABASE_URL)


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Получить пользователя по имени пользователя.

    Возвращает запись или None.
    """
    query = """
        SELECT id, username, password, created_at FROM users 
        WHERE username = :username
    """
    result = await db.fetch_one(query, values={"username": username})
    if result:
        return result
    return None


async def create_user(username: str, hashed_password: str) -> None:
    """
    Создать нового пользователя.
    """
    query = """
        INSERT INTO users (username, password) 
        VALUES (:username, :password)
    """
    values = {"username": username, "password": hashed_password}
    await db.execute(query=query, values=values)


async def check_user_camera(user_id: int, camera_id: int) -> bool:
    """
    Проверяет, принадлежит ли камера пользователю.
    """
    query = """
        SELECT id FROM cameras 
        WHERE id = :camera_id AND user_id = :user_id
    """
    values = {"camera_id": camera_id, "user_id": user_id}
    result = await db.fetch_one(query, values)
    return bool(result)


async def get_camera(user_id: int, camera_name: str) -> Optional[Dict[str, Any]]:
    """
    Получает камеру по имени для пользователя.
    """
    query = """
        SELECT * FROM cameras 
        WHERE user_id = :user_id AND name = :name
    """
    values = {"user_id": user_id, "name": camera_name}
    result = await db.fetch_one(query, values)
    if result:
        return result
    return None
    

async def get_user_cameras(user_id: int) -> List[Dict[str, Any]]:
    """
    Возвращает список камер пользователя (id, name, url).
    """
    query = """
        SELECT id, name, url FROM cameras 
        WHERE user_id = :user_id
        ORDER BY created_at
    """
    values = {"user_id": user_id}
    result = await db.fetch_all(query, values)
    return list(result) if result else []

    
async def add_camera(user_id: int, name: str, url: str) -> Optional[int]:
    """
    Добавляет камеру и соответствующую строку в cameras_settings в транзакции.
    Возвращает id добавленной камеры.
    """
    async with db.transaction():
        query = """
            INSERT INTO cameras (user_id, name, url) 
            VALUES (:user_id, :name, :url)
            RETURNING id
        """
        values = {"user_id": user_id, "name": name, "url": url}
        camera_id = await db.execute(query, values)

        query = """
            INSERT INTO cameras_settings (camera_id) 
            VALUES (:camera_id)
        """
        values = {"camera_id": camera_id}
        await db.execute(query, values)
    if camera_id:
        return camera_id
    return None


async def update_camera_db(id: int, name: str, url: str) -> Optional[int]:
    """
    Обновление данных камеры. Возвращает id камеры.
    """
    query = """
        UPDATE cameras
        SET name = :name, url = :url
        WHERE id = :id
        RETURNING id
    """
    values = {"id": id, "name": name, "url": url}
    result = await db.execute(query, values)
    if result:
        return result
    return None


async def delete_camera_db(id: int) -> Optional[int]:
    """
    Удаляет камеру по id. Возвращает id удаленной камеры.
    """
    query = """
        DELETE FROM cameras 
        WHERE id = :id 
        RETURNING id
    """
    values = {"id": id}
    result = await db.execute(query, values)
    if result:
        return result
    return None


async def get_camera_settings_by_id(id: int) -> Optional[Dict[str, Any]]:
    """
    Получает url, model_name и confidence_threshold для камеры.
    """
    query = """
        SELECT url, model_name, confidence_threshold FROM cameras 
        JOIN cameras_settings ON cameras.id = camera_id
        WHERE cameras.id = :id
    """
    values = {"id": id}
    result = await db.fetch_one(query, values)
    if result:
        return result
    return None
    

async def set_camera_settings_by_id(
        id: int, 
        model: str, 
        threshold: int
    ) -> Optional[int]:
    """
    Обновляет настройки камеры и возвращает id камеры.
    """
    query = """
        UPDATE cameras_settings
        SET model_name = :model, confidence_threshold = :threshold
        WHERE camera_id = :id
        RETURNING camera_id
    """
    values = {"id": id, "model": model, "threshold": threshold}
    result = await db.execute(query, values)
    if result:
        return result
    return None