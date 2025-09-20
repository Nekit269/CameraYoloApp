from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import db
from models.post import UserPost, UserPostIn

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()
    
app = FastAPI(lifespan=lifespan)

@app.post("/post", response_model=UserPost)
async def create_post(post: UserPostIn):
    query = "INSERT INTO posts (name,body) VALUES (:name, :body) RETURNING id"
    last_record_id = await db.execute(query=query, values=post.model_dump())
    return {**post.model_dump(), "id": last_record_id}

@app.get("/posts", response_model=list[UserPost])
async def get_all_posts():
    query = "SELECT * FROM posts"
    return await db.fetch_all(query)
