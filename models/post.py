from pydantic import BaseModel

class UserPostIn(BaseModel):
    name: str
    body: str

class UserPost(UserPostIn):
    id: int