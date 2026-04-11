from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, str]:
    role = "admin" if payload.username.startswith("admin") else "user"
    return {"access_token": "dev-token", "token_type": "bearer", "role": role}
