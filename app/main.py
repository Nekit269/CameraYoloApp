import os

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import (
    HTMLResponse, 
    RedirectResponse, 
    JSONResponse,
    StreamingResponse
)
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from contextlib import asynccontextmanager

from .database import (
    db, 
    get_user_by_username, 
    create_user, 
    get_camera,
    check_user_camera,
    get_user_cameras,
    add_camera,
    update_camera_db,
    delete_camera_db,
    get_camera_settings_by_id,
    set_camera_settings_by_id)
from .security import (
    get_password_hash, 
    create_access_token, 
    authenticate_user, 
    get_current_user
)
from. video import VideoManager, load_models
from .models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    load_models()
    yield
    await db.disconnect()

video_manager = VideoManager()
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

    yolo_models = ["None"] + list(map(lambda x: x.split('.')[0], 
                                      os.listdir("app/yolo")))

    return templates.TemplateResponse("main.html", {"request": request, 
                                                    "cameras": cameras_list,
                                                    "models": yolo_models})

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
            video_manager.update_url(user.id, id, url)

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

@app.post("/cameras/settings/get")
async def get_camera_settings(id: int = Form(...),
                              user: User = Depends(get_current_user)):
    if await check_user_camera(user.id, id):
        result = await get_camera_settings_by_id(id)

        if result:
            return JSONResponse({"success": True, 
                                 "url": result.url,
                                 "model_name": result.model_name,
                                 "confidence_threshold": result.confidence_threshold})
        else:
            return JSONResponse({"success": False, 
                                 "error": "Не удалось получить данные из бд"})

    return JSONResponse({"success": False, 
                         "error": "Неавторизованный доступ к бд"})

@app.post("/cameras/settings/set")
async def set_camera_settings(id: int = Form(...),
                              model: str = Form(...),
                              threshold: int = Form(...),
                              user: User = Depends(get_current_user)):
    if await check_user_camera(user.id, id):
        result = await set_camera_settings_by_id(id, model, threshold)

        if result:
            video_manager.update_params(user.id, model, threshold * 0.01)

            return JSONResponse({"success": True})
        else:
            return JSONResponse({"success": False, 
                                 "error": "Не удалось обновить данные в бд"})

    return JSONResponse({"success": False, 
                         "error": "Неавторизованный доступ к бд"})

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response

@app.get("/stream/{camera_id}")
async def video_feed(camera_id: int,
                     user: User = Depends(get_current_user)):
    if await check_user_camera(user.id, camera_id):
        result = await get_camera_settings_by_id(camera_id)

        if result:
            video_manager.start_stream(user.id, 
                                       camera_id,
                                       result.url, 
                                       result.model_name,
                                       result.confidence_threshold * 0.01)

            media_type = "multipart/x-mixed-replace; boundary=frame"
            return StreamingResponse(video_manager.get_frames(user.id), 
                                     media_type=media_type)
        else:
            return HTTPException(status_code=403,
                                 detail="Не удалось получить данные из бд")

    else:
        raise HTTPException(status_code=403, 
                            detail="Неавторизованный доступ к камере")
