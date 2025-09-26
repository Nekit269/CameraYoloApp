import os
import databases

from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv("DATABASE_URL")
db = databases.Database(database_url)

async def get_user_by_username(username: str):
    query = """
        SELECT id, username, password, created_at FROM users 
        WHERE username = :username
    """
    result = await db.fetch_one(query, values={"username": username})
    if result:
        return result

async def create_user(username: str, hashed_password: str):
    query = """
        INSERT INTO users (username, password) 
        VALUES (:username, :password)
    """
    values = {"username": username, "password": hashed_password}
    await db.execute(query=query, values=values)

async def check_user_camera(user_id: int, camera_id: int):
    query = """
        SELECT id FROM cameras 
        WHERE id = :camera_id AND user_id = :user_id
    """
    values = {"camera_id": camera_id, "user_id": user_id}
    result = await db.fetch_one(query, values)
    if result:
        return True
    else:
        return False

async def get_camera(user_id: int, camera_name: str):
    query = """
        SELECT * FROM cameras 
        WHERE user_id = :user_id AND name = :name
    """
    values = {"user_id": user_id, "name": camera_name}
    result = await db.fetch_one(query, values)
    if result:
        return result
    
async def get_user_cameras(user_id: int):
    query = """
        SELECT id, name, url FROM cameras 
        WHERE user_id = :user_id
        ORDER BY created_at
    """
    values = {"user_id": user_id}
    result = await db.fetch_all(query, values)
    if result:
        return result
    
async def add_camera(user_id: int, name: str, url: str):
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
    return camera_id

async def update_camera_db(id: int, name: str, url: str):
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
    
async def delete_camera_db(id: int):
    query = """
        DELETE FROM cameras 
        WHERE id = :id 
        RETURNING id
    """
    values = {"id": id}
    result = await db.execute(query, values)
    if result:
        return result
    
async def get_camera_settings_by_id(id: int):
    query = """
        SELECT url, model_name, confidence_threshold FROM cameras 
        JOIN cameras_settings ON cameras.id = camera_id
        WHERE cameras.id = :id
    """
    values = {"id": id}
    result = await db.fetch_one(query, values)
    if result:
        return result
    
async def set_camera_settings_by_id(id: int, model: str, threshold: int):
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