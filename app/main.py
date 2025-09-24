from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .database import (
    db, 
    get_user_by_username, 
    create_user, 
    get_camera,
    check_user_camera,
    get_camera_by_id,
    get_user_cameras,
    add_camera,
    update_camera_db,
    delete_camera_db)
from .security import (
    get_password_hash, 
    create_access_token, 
    authenticate_user, 
    get_current_user
)
from .models.user import User


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
    response = RedirectResponse(url="/panel", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

@app.get("/panel", response_class=HTMLResponse)
async def panel_form(request: Request,
                     user: User = Depends(get_current_user)):
    cameras = await get_user_cameras(user.id)
    if cameras:
        cameras_list = [dict(cam) for cam in cameras]
    else:
        cameras_list = []

    return templates.TemplateResponse("main.html", {"request": request, 
                                                    "cameras": cameras_list})

@app.get("/panel", response_class=HTMLResponse)
async def panel(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/cameras/add")
async def add_new_camera(name: str = Form(...),
                         url: str = Form(...),
                         user: User = Depends(get_current_user)):
    camera = await get_camera(user.id, name)
    if camera:
        return JSONResponse({"success": False, "error": "Камера уже существует"})
    
    camera_id = await add_camera(user.id, name, url)
    return JSONResponse({"success": True, "id": camera_id})

@app.post("/cameras/update")
async def update_camera(id: int = Form(...),
                        name: str = Form(...),
                        url: str = Form(...),
                        user: User = Depends(get_current_user)):
    if await check_user_camera(user.id, id):
        result = await update_camera_db(id, name, url)

        if result:
            return JSONResponse({"success": True, "id": id})
        else:
            return JSONResponse({"success": False, 
                                 "error": "Не удалось обновить бд"})

    return JSONResponse({"success": False, 
                         "error": "Неавторизованное обновление бд"})

@app.post("/cameras/delete")
async def delete_camera(id: int = Form(...),
                        user: User = Depends(get_current_user)):
    if await check_user_camera(user.id, id):
        result = await delete_camera_db(id)

        if result:
            return JSONResponse({"success": True, "id": id})
        else:
            return JSONResponse({"success": False, 
                                 "error": "Не удалось удалить из бд"})

    return JSONResponse({"success": False, 
                         "error": "Неавторизованное удаление из бд"})

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response
