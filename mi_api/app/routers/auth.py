from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from ..auth import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from ..database import create_user, get_user, init_users_table

# ruff: noqa: B008

router = APIRouter(tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserCreate(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(user: UserCreate):
    await init_users_table()
    existing = await get_user(user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    hashed = get_password_hash(user.password)
    await create_user(user.username, hashed)
    return {"message": "Usuario creado exitosamente"}


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    username = payload.get("sub")
    user = await get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"]}
