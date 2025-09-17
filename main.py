import psycopg2

from fastapi import FastAPI
from contextlib import asynccontextmanager

from connect_to_db import connect_to_db
from models.post import UserPost, UserPostIn

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect_to_db()
    yield
    conn.close()
    
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Hello, world!"}

@app.post("/post", response_model=UserPost)
async def create_post(post: UserPost):
    pass

@app.get("/posts", response_model=list[UserPost])
async def get_all_posts():
    pass