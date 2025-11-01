"""
Auth API - Авторизация клиентов
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Client
from services.auth_service import create_access_token, hash_password, verify_password, get_current_client


router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str  # person_id клиента
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    client_id: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Авторизация клиента
    
    В MVP: простая авторизация по person_id (username = password для упрощения)
    """
    
    # Найти клиента
    result = await db.execute(
        select(Client).where(Client.person_id == request.username)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(401, "Invalid credentials")
    
    # В MVP: password = username+1 или универсальный password+1 (для упрощения тестирования)
    # В production: проверять хешированный пароль
    expected_password_username = request.username + "+1"
    universal_password = "password+1"
    if request.password != expected_password_username and request.password != universal_password:
        raise HTTPException(401, "Invalid credentials")
    
    # Создать JWT токен
    access_token = create_access_token(
        data={
            "sub": client.person_id,
            "type": "client",
            "bank": "self"
        }
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        client_id=client.person_id
    )


@router.get("/me")
async def get_current_user(
    current_client: dict = Depends(get_current_client)
):
    """Получение информации о текущем клиенте"""
    
    if not current_client:
        raise HTTPException(401, "Not authenticated")
    
    return current_client


@router.post("/bank-token")
async def create_bank_token(bank_code: str, shared_secret: str = "hackapi-2025-bank-secret"):
    """
    Создание токена для межбанковских запросов
    
    Использует JWT RS256 с приватным ключом банка
    """
    from config import config
    
    # В sandbox: простая проверка секрета
    if shared_secret != "hackapi-2025-bank-secret":
        raise HTTPException(401, "Invalid secret")
    
    # Создать bank token с RS256
    bank_token = create_access_token(
        data={
            "sub": bank_code,
            "type": "bank",
            "iss": config.BANK_CODE,
            "aud": "interbank"
        },
        use_rs256=True  # Используем RS256 для межбанковских токенов
    )
    
    return {
        "access_token": bank_token,
        "token_type": "bearer",
        "bank_code": bank_code,
        "algorithm": "RS256"
    }


@router.post("/banker-login")
async def banker_login(
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Авторизация банкира
    
    В sandbox: упрощенная авторизация
    """
    # Banker credentials: username 'admin', password 'admin+1'
    if username != "admin" or password != "admin+1":
        raise HTTPException(401, "Invalid credentials")
    
    from config import config
    
    # Создать токен банкира
    banker_token = create_access_token(
        data={
            "sub": "banker",
            "type": "banker",
            "bank": config.BANK_CODE
        }
    )
    
    return {
        "access_token": banker_token,
        "token_type": "bearer",
        "role": "banker"
    }

