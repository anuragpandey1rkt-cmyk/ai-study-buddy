from pydantic import BaseModel
from datetime import date

class UserCreate(BaseModel):
    username: str

class ProgressCreate(BaseModel):
    user_id: int
    date: date
    xp: int
    streak: int
    minutes: int
