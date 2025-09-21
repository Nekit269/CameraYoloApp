import os
import databases

from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv("DATABASE_URL")
db = databases.Database(database_url)

async def get_user_by_username(username: str):
    query = """
        SELECT id, username, password FROM users 
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