"""
Well-Known endpoints - JWKS
OpenID Connect Discovery compatible
"""
from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter(prefix="/.well-known", tags=["Well-Known"])


@router.get("/jwks.json")
async def get_jwks():
    """
    JWKS endpoint - публичные ключи банка
    
    OpenID Connect Discovery
    RFC 7517 - JSON Web Key (JWK)
    
    Используется другими банками для проверки JWT подписей
    при межбанковских запросах.
    """
    from config import config
    
    # Путь к JWKS файлу банка
    # Из /app/api/well_known.py -> /app/api -> /app -> /app/shared/keys/
    jwks_path = Path(__file__).parent.parent / "shared" / "keys" / f"{config.BANK_CODE}_jwks.json"
    
    # Базовый JWKS если файла нет
    default_jwks = {
        "keys": [{
            "kid": f"{config.BANK_CODE}-2025",
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "n": "placeholder_modulus",
            "e": "AQAB"
        }]
    }
    
    # Загрузить из файла если есть
    if jwks_path.exists():
        try:
            with open(jwks_path, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return default_jwks

