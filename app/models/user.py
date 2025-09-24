from pydantic import BaseModel

class User(BaseModel):
    id: int | None = None
    username: str