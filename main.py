import os
import databases

from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from models.post import UserPost, UserPostIn

load_dotenv()
database_url = os.getenv("DATABASE_URL")
db = databases.Database(database_url)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()
    
app = FastAPI(lifespan=lifespan)

@app.post("/post", response_model=UserPost)
async def create_post(post: UserPostIn):
    pass

@app.get("/posts", response_model=list[UserPost])
async def get_all_posts():
    pass