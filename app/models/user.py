from fastapi import Form
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    id: int | None = None
    username: str = Field(..., min_length=5, max_length=20, example="Username")


class User(UserBase):
    """Схема для проверки текущего пользователя."""
    pass


class UserIn(UserBase):
    """Схема для входа пользователя."""
    password: str = Field(..., min_length=5, max_length=30, example="Password")

    @classmethod
    def as_form(
        cls,
        username: str = Form(..., min_length=5, max_length=20),
        password: str = Form(..., min_length=5, max_length=30),
    ):
        return cls(username=username, password=password)


class UserRegister(UserIn):
    """Схема для регистрации пользователя."""
    confirm_password: str = Field(..., min_length=5, max_length=30, example="Password")

    @classmethod
    def as_form(
        cls,
        username: str = Form(..., min_length=5, max_length=20),
        password: str = Form(..., min_length=5, max_length=30),
        confirm_password: str = Form(..., min_length=5, max_length=30),
    ):
        return cls(username=username, password=password, confirm_password=confirm_password)