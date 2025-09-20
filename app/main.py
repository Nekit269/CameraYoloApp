from fastapi import FastAPI, HTTPException, status, Depends
from contextlib import asynccontextmanager

from .database import db
from .security import (
    get_password_hash, 
    create_access_token, 
    authenticate_user, 
    get_current_user
)
from models.user import User, UserIn


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()
    
app = FastAPI(lifespan=lifespan)

@app.post("/register")
async def register(user: UserIn):
    hashed_password = get_password_hash(user.password)
    query = "INSERT INTO users (username, password) VALUES (:username, :password)"
    values = {"username": user.username, "password": hashed_password}
    await db.execute(query=query, values=values)
    access_token = create_access_token(user.username)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token")
async def login(user: UserIn):
    user = await authenticate_user(user.username, user.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user.username)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
