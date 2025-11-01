"""
Сервис авторизации клиентов и банков
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
import httpx

from config import config

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, use_rs256: bool = False):
    """Создание JWT токена (HS256 или RS256)"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Для bank tokens используем RS256
    if use_rs256:
        try:
            # Загрузить приватный ключ
            # Из /app/services/auth_service.py -> /app/services -> /app -> /app/shared/keys/
            keys_path = Path(__file__).parent.parent / "shared" / "keys"
            private_key_path = keys_path / f"{config.BANK_CODE}_private.pem"
            
            if not private_key_path.exists():
                # Fallback to HS256 if key not found
                encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
                return encoded_jwt
            
            with open(private_key_path, 'r') as f:
                private_key = f.read()
            
            # Добавить kid (key ID) в header
            headers = {"kid": f"{config.BANK_CODE}-2025"}
            encoded_jwt = jwt.encode(to_encode, private_key, algorithm="RS256", headers=headers)
            return encoded_jwt
        except Exception as e:
            print(f"Warning: Failed to load RSA key, falling back to HS256: {e}")
            # Fallback to HS256
            encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
            return encoded_jwt
    else:
        # Для client tokens используем HS256
        encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
        return encoded_jwt


def verify_token(token: str, issuer_bank_code: Optional[str] = None) -> dict:
    """
    Проверка JWT токена (HS256 или RS256)
    
    Args:
        token: JWT токен для проверки
        issuer_bank_code: Код банка-эмитента (issuer), который подписал токен.
                         Используется для получения публичного ключа этого банка.
    """
    try:
        # Сначала пробуем HS256 (для клиентских токенов)
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            return payload
        except JWTError:
            pass
        
        # Если не получилось, пробуем RS256 (для межбанковских токенов)
        # Сначала декодируем без проверки, чтобы получить issuer
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            issuer = unverified_payload.get("iss")
            
            if issuer:
                # Проверяем токен ключом эмитента (синхронная проверка с локальным ключом)
                payload = verify_rs256_token_sync(token, issuer)
                return payload
            elif issuer_bank_code:
                # Fallback: используем переданный bank_code
                payload = verify_rs256_token_sync(token, issuer_bank_code)
                return payload
        except Exception as e:
            print(f"RS256 verification failed: {e}")
            pass
        
        raise JWTError("Token validation failed")
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def verify_rs256_token_sync(token: str, issuer_bank_code: str) -> dict:
    """
    Синхронная проверка RS256 токена через локальный публичный ключ
    
    Args:
        token: JWT токен для проверки
        issuer_bank_code: Код банка-эмитента (issuer), который подписал токен
    
    Returns:
        dict: Payload токена
    """
    try:
        # Попробовать загрузить публичный ключ из локального файла
        keys_path = Path(__file__).parent.parent / "shared" / "keys"
        public_key_path = keys_path / f"{issuer_bank_code}_public.pem"
        
        if public_key_path.exists():
            with open(public_key_path, 'r') as f:
                public_key = f.read()
            
            payload = jwt.decode(token, public_key, algorithms=["RS256"])
            print(f"✅ Token verified using local public key: {issuer_bank_code}_public.pem")
            return payload
        
        # Если локального ключа нет - ошибка
        # Для асинхронной проверки через JWKS используйте verify_rs256_token_async
        raise JWTError(f"No local public key found for issuer '{issuer_bank_code}'")
        
    except JWTError:
        raise
    except Exception as e:
        print(f"❌ RS256 sync verification failed for issuer '{issuer_bank_code}': {e}")
        raise JWTError(f"RS256 verification failed: {str(e)}")


async def verify_rs256_token_async(token: str, issuer_bank_code: str) -> dict:
    """
    Асинхронная проверка RS256 токена через публичный ключ или JWKS
    
    Эта функция пробует два способа:
    1. Локальный публичный ключ (если есть)
    2. Загрузка JWKS через HTTP от банка-эмитента (межбанковый сценарий)
    
    Args:
        token: JWT токен для проверки
        issuer_bank_code: Код банка-эмитента (issuer), который подписал токен
    
    Returns:
        dict: Payload токена
    """
    try:
        # Стратегия 1: Попробовать загрузить публичный ключ из локального файла
        # Это работает, если у нас есть ключ банка-эмитента локально
        keys_path = Path(__file__).parent.parent / "shared" / "keys"
        public_key_path = keys_path / f"{issuer_bank_code}_public.pem"
        
        if public_key_path.exists():
            with open(public_key_path, 'r') as f:
                public_key = f.read()
            
            payload = jwt.decode(token, public_key, algorithms=["RS256"])
            print(f"✅ Token verified using local public key: {issuer_bank_code}_public.pem")
            return payload
        
        # Стратегия 2: Загрузить JWKS банка-эмитента через HTTP
        # Это межбанковый сценарий - получаем публичный ключ из JWKS endpoint
        async with httpx.AsyncClient() as client:
            # Определить base URL банка-эмитента
            bank_ports = {
                "vbank": 8001, 
                "abank": 8002, 
                "sbank": 8003,
                "onebank": 8000
            }
            port = bank_ports.get(issuer_bank_code, 8001)
            
            jwks_url = f"http://localhost:{port}/.well-known/jwks.json"
            print(f"🔍 Fetching JWKS from: {jwks_url}")
            
            response = await client.get(jwks_url, timeout=5.0)
            
            if response.status_code == 200:
                jwks = response.json()
                # Используем первый ключ из JWKS
                if jwks.get("keys"):
                    # В production нужно искать по kid из header токена
                    key = jwks["keys"][0]
                    
                    # Преобразуем JWK в PEM формат для python-jose
                    from jose.backends.rsa_backend import RSAKey
                    rsa_key = RSAKey(key, algorithm="RS256")
                    
                    payload = jwt.decode(token, rsa_key.to_pem().decode(), algorithms=["RS256"])
                    print(f"✅ Token verified using JWKS from: {jwks_url}")
                    return payload
        
        raise JWTError(f"Failed to verify RS256 token: no public key found for issuer '{issuer_bank_code}'")
        
    except JWTError:
        raise
    except Exception as e:
        print(f"❌ RS256 verification failed for issuer '{issuer_bank_code}': {e}")
        raise JWTError(f"RS256 verification failed: {str(e)}")


async def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[dict]:
    """
    Dependency для получения текущего клиента из JWT токена
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload.get("type") != "client":
        return None
    
    return {
        "client_id": payload.get("sub"),
        "type": "client"
    }


async def get_current_bank(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[dict]:
    """
    Dependency для получения текущего банка из JWT токена (межбанковские запросы)
    
    Проверяет токен, который был выдан этим банком другому банку через /auth/bank-token.
    Токен содержит:
    - iss: код банка-эмитента (этот банк)
    - sub: код банка-получателя (запрашивающий банк)
    - type: "bank"
    
    Returns:
        dict с bank_code (из sub) - код запрашивающего банка
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload.get("type") != "bank":
        return None
    
    return {
        "bank_code": payload.get("sub"),  # Код запрашивающего банка
        "issuer": payload.get("iss"),      # Код банка-эмитента (этот банк)
        "type": "bank"
    }


async def get_optional_client(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Optional dependency - не выбрасывает ошибку если токена нет
    """
    if not credentials:
        return None
    
    try:
        payload = verify_token(credentials.credentials)
        if payload.get("type") == "client":
            return {
                "client_id": payload.get("sub"),
                "type": "client"
            }
    except:
        return None
    
    return None


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)

