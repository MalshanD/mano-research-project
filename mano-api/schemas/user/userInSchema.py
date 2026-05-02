from pydantic import BaseModel


class UserIn(BaseModel):
    guest_name: str
    password: str
