"""
Точка входа FastAPI приложения.

Определяет маршруты API, middleware аутентификации и lifecycle-хуки.

"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import (
    add_camera,
    check_user_camera,
    create_user,
    db,
    delete_camera_db,
    get_camera,
    get_camera_settings_by_id,
    get_user_by_username,
    get_user_cameras,
    set_camera_settings_by_id,
    update_camera_db,
)
from .models.user import User, UserIn, UserRegister
from .models.camera import CameraCreate, CameraUpdate, CameraSettings
from .security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from .video import VideoManager, load_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Хук жизненного цикла приложения.

    - При старте: подключение к БД и загрузка YOLO-моделей.
    - При завершении: отключение от БД.
    """
    await db.connect()
    load_models()
    yield
    await db.disconnect()


# -------------------------
# Приложение и конфигурация
# -------------------------
video_manager = VideoManager()
app = FastAPI(lifespan=lifespan)

# Шаблоны и статика
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Пути, доступные без авторизации
PUBLIC_PATHS = ["/login", "/register", "/static", "/favicon.ico"]


# -------------------------
# Middleware
# -------------------------
@app.middleware("http")
async def check_auth(request: Request, call_next):
    """
    Middleware для проверки аутентификации.

    - Пропускает публичные пути.
    - Проверяет наличие cookie `access_token`.
    - Перенаправляет неаутентифицированных пользователей на /login.
    """
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


# -------------------------
# Эндпоинты аутентификации
# -------------------------
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    """Форма регистрации."""
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    user_reg: UserRegister = Depends(UserRegister.as_form),
):
    """Обработка регистрации: проверка пароля и создание пользователя."""
    if user_reg.password != user_reg.confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request, 
                "username": user_reg.username, 
                "error": "Пароли не совпадают"
            },
        )

    user = await get_user_by_username(user_reg.username)

    if user:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "username": user_reg.username,
                "error": "Имя пользователя занято",
            },
        )

    hashed_password = get_password_hash(user_reg.password)
    await create_user(user_reg.username, hashed_password)

    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """Форма входа."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    user_in: UserIn = Depends(UserIn.as_form),
):
    """Аутентификация и установка JWT-токена в cookie."""
    user = await authenticate_user(user_in.username, user_in.password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "username": user_in.username,
                "error": "Неправильные логин или пароль",
            },
        )
    token = create_access_token(user_in.username)
    response = RedirectResponse(url="/panel", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response


@app.get("/logout")
async def logout():
    """Выход: удаление cookies и редирект на login."""
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response


# -------------------------
# Панель и камеры
# -------------------------
@app.get("/panel", response_class=HTMLResponse)
async def panel_form(request: Request, user: User = Depends(get_current_user)):
    """Основная панель с камерами пользователя и списком YOLO-моделей."""
    cameras = await get_user_cameras(user.id)

    # Собираем список из доступных YOLO-моделей
    yolo_models = ["None"] + list(
        map(lambda x: x.split(".")[0], os.listdir("app/yolo"))
    )

    return templates.TemplateResponse(
        "main.html",
        {
            "request": request,
            "username": user.username,
            "cameras": cameras,
            "models": yolo_models,
        },
    )


@app.post("/cameras/add")
async def add_new_camera(
    camera_create: CameraCreate = Depends(CameraCreate.as_form), 
    user: User = Depends(get_current_user),
):
    """Добавить новую камеру текущему пользователю."""
    camera = await get_camera(user.id, camera_create.name)
    if camera:
        return JSONResponse({"success": False, "error": "Камера уже существует"})

    camera_id = await add_camera(user.id, camera_create.name, camera_create.url)
    if camera_id is None:
        return JSONResponse({
            "success": False, 
            "error": "Не удалось добавить камеру в бд"
        })
    
    return JSONResponse({"success": True, "id": camera_id})


@app.post("/cameras/update")
async def update_camera(
    camera_update: CameraUpdate = Depends(CameraUpdate.as_form),
    user: User = Depends(get_current_user),
):
    """Обновить данные камеры и синхронизировать URL с VideoManager."""
    if await check_user_camera(user.id, camera_update.id):
        result = await update_camera_db(
            camera_update.id, 
            camera_update.name, 
            camera_update.url
        )

        if result:
            video_manager.update_url(
                user.id, 
                camera_update.id, 
                camera_update.url
            )

            return JSONResponse({"success": True, "id": camera_update.id})
        else:
            return JSONResponse({"success": False, "error": "Не удалось обновить бд"})

    return JSONResponse({"success": False, "error": "Неавторизованное обновление бд"})


@app.post("/cameras/delete")
async def delete_camera(
    id: int = Form(...), 
    user: User = Depends(get_current_user),
):
    """Удалить камеру текущего пользователя."""
    if await check_user_camera(user.id, id):
        result = await delete_camera_db(id)

        if result:
            return JSONResponse({"success": True, "id": id})
        else:
            return JSONResponse({"success": False, "error": "Не удалось удалить из бд"})

    return JSONResponse({"success": False, "error": "Неавторизованное удаление из бд"})


@app.post("/cameras/settings/get")
async def get_camera_settings(
    id: int = Form(...), 
    user: User = Depends(get_current_user),
):
    """Получить настройки камеры текущего пользователя."""
    if await check_user_camera(user.id, id):
        result = await get_camera_settings_by_id(id)

        if result:
            return JSONResponse(
                {
                    "success": True,
                    "url": result.url,
                    "model_name": result.model_name,
                    "confidence_threshold": result.confidence_threshold,
                }
            )
        else:
            return JSONResponse(
                {"success": False, "error": "Не удалось получить данные из бд"}
            )

    return JSONResponse({"success": False, "error": "Неавторизованный доступ к бд"})


@app.post("/cameras/settings/set")
async def set_camera_settings(
    camera_settings: CameraSettings = Depends(CameraSettings.as_form),
    user: User = Depends(get_current_user),
):
    """Сохранить настройки камеры и обновить параметры в VideoManager."""
    if await check_user_camera(user.id, camera_settings.id):
        result = await set_camera_settings_by_id(
            camera_settings.id, 
            camera_settings.model, 
            camera_settings.threshold
        )

        if result:
            video_manager.update_params(
                user.id, 
                camera_settings.model, 
                camera_settings.threshold * 0.01
            )

            return JSONResponse({"success": True})
        else:
            return JSONResponse(
                {"success": False, "error": "Не удалось обновить данные в бд"}
            )

    return JSONResponse({"success": False, "error": "Неавторизованный доступ к бд"})


# -------------------------
# Стримы
# -------------------------
@app.get("/stream/{camera_id}")
async def video_feed(camera_id: int, user: User = Depends(get_current_user)):
    """Стрим MJPEG для камеры пользователя."""
    if await check_user_camera(user.id, camera_id):
        result = await get_camera_settings_by_id(camera_id)

        if result:
            video_manager.start_stream(
                user.id,
                camera_id,
                result.url,
                result.model_name,
                result.confidence_threshold * 0.01,
            )

            media_type = "multipart/x-mixed-replace; boundary=frame"
            return StreamingResponse(
                video_manager.get_frames(user.id), media_type=media_type
            )
        else:
            raise HTTPException(
                status_code=403, detail="Не удалось получить данные из бд"
            )

    else:
        raise HTTPException(status_code=403, detail="Неавторизованный доступ к камере")
