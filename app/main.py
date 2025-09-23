from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .database import db, get_user_by_username, create_user
from .security import (
    get_password_hash, 
    create_access_token, 
    authenticate_user, 
    get_current_user
)
from models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()
    
app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
PUBLIC_PATHS = ["/login", "/register", "/static", "/favicon.ico"]

@app.middleware("http")
async def check_auth(request: Request, call_next):
    path = request.url.path

    if any(path.startswith(pub) for pub in PUBLIC_PATHS):
        return await call_next(request)

    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login")

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/login")

    response = await call_next(request)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request, 
    username: str = Form(..., min_length=5, max_length=20),
    password: str = Form(..., min_length=5, max_length=30),
    confirm_password: str = Form(..., min_length=5, max_length=30)
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html", {
                "request": request, 
                "username": username,
                "error": "Пароли не совпадают"
            }
        )

    user = await get_user_by_username(username)

    if user:
        return templates.TemplateResponse(
            "register.html", {
                "request": request, 
                "username": username,
                "error": "Имя пользователя занято"
            }
        )

    hashed_password = get_password_hash(password)
    await create_user(username, hashed_password)

    return RedirectResponse(url="/login", status_code=302)
    
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(..., min_length=5, max_length=20),
    password: str = Form(..., min_length=5, max_length=30)
):
    user = await authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", {
                "request": request, 
                "username": username, 
                "error": "Неправильные логин или пароль"
            }
        )
    token = create_access_token(username)
    response = RedirectResponse(url="/users/me", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response
