from fastapi import Form
from pydantic import BaseModel, Field


class CameraBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, example="Камера_1")
    url: str = Field(..., example="rtsp://")


class CameraCreate(CameraBase):
    """Схема для добавления новой камеры."""

    @classmethod
    def as_form(
        cls,
        name: str = Form(..., min_length=3, max_length=50),
        url: str = Form(...),
    ):
        return cls(name=name, url=url)


class CameraUpdate(CameraBase):
    """Схема для обновления камеры."""
    id: int = Field(..., example=1)

    @classmethod
    def as_form(
        cls,
        id: int = Form(...),
        name: str = Form(..., min_length=3, max_length=50),
        url: str = Form(...),
    ):
        return cls(id=id, name=name, url=url)


class CameraSettings(BaseModel):
    """Схема для обновления настроек камеры."""
    id: int = Field(..., example=1)
    model: str = Field(..., example="yolov8n")
    threshold: int = Field(..., ge=0, le=100, example=50)

    @classmethod
    def as_form(
        cls,
        id: int = Form(...),
        model: str = Form(...),
        threshold: int = Form(...),
    ):
        return cls(id=id, model=model, threshold=threshold)