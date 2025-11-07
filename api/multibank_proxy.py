"""
Multibank Proxy API - Проксирование запросов к другим банкам
Реализует правильный OpenBanking flow через consent (согласия)
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import logging
import asyncio
import json
from urllib.parse import urlencode

from config import config as app_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multibank", tags=["Internal: Multibank"], include_in_schema=False)

# Креды команды и клиента (из конфигурации или окружения)
TEAM_CLIENT_ID = app_config.TEAM_CLIENT_ID or os.getenv("TEAM_CLIENT_ID", "team200")
TEAM_CLIENT_SECRET = app_config.TEAM_CLIENT_SECRET or os.getenv("TEAM_CLIENT_SECRET", "5OAaa4DYzYKfnOU6zbR34ic5qMm7VSMB")
CLIENT_USERNAME = app_config.CLIENT_USERNAME or os.getenv("CLIENT_USERNAME", "team018-1")
CLIENT_PASSWORD = app_config.CLIENT_PASSWORD or os.getenv("CLIENT_PASSWORD", "password")


class BankTokenRequest(BaseModel):
    bank_url: str


class ConsentRequest(BaseModel):
    bank_url: str
    bank_token: str
    client_id: str  # ID клиента в целевом банке


class AccountsWithConsentRequest(BaseModel):
    bank_url: str
    bank_token: str
    consent_id: str
    client_id: str


class LoginRequest(BaseModel):
    bank_url: str
    username: str = "demo-client-001"
    password: str = "password"


class ProxyRequest(BaseModel):
    bank_url: str
    endpoint: str
    token: str


def _safe_json(response: httpx.Response) -> Optional[dict]:
    try:
        return response.json()
    except ValueError:
        return None


async def _run_curl(method: str, url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None, json_payload: Optional[dict] = None) -> dict:
    query = f"?{urlencode(params, doseq=True)}" if params else ""
    cmd = ["curl", "-sS", "-X", method.upper(), f"{url}{query}"]

    headers = headers or {}
    for key, value in headers.items():
        cmd.extend(["-H", f"{key}: {value}"])

    data_arg = None
    if json_payload is not None:
        body = json.dumps(json_payload)
        cmd.extend(["-H", "Content-Type: application/json", "-d", body])

    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_text = stderr.decode().strip() or stdout.decode().strip() or "curl exited with non-zero code"
        raise HTTPException(502, f"Curl failed ({proc.returncode}): {error_text}")

    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        raise HTTPException(502, f"Invalid JSON returned by bank: {stdout.decode().strip()}")


async def _post_with_fallback(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None, json_payload: Optional[dict] = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=app_config.OPEN_BANKING_TIMEOUT) as client:
            response = await client.post(url, params=params, json=json_payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        detail = _safe_json(exc.response) or exc.response.text
        raise HTTPException(exc.response.status_code, detail)
    except httpx.RequestError as exc:
        logger.warning("POST %s failed via httpx (%s). Falling back to curl", url, exc)
        return await _run_curl("POST", url, params=params, headers=headers, json_payload=json_payload)


async def _get_with_fallback(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=app_config.OPEN_BANKING_TIMEOUT) as client:
            response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        detail = _safe_json(exc.response) or exc.response.text
        raise HTTPException(exc.response.status_code, detail)
    except httpx.RequestError as exc:
        logger.warning("GET %s failed via httpx (%s). Falling back to curl", url, exc)
        return await _run_curl("GET", url, params=params, headers=headers)


@router.post("/bank-token")
async def get_bank_token(request: BankTokenRequest):
    """
    ШАГ 1: Получить банковский токен для межбанковых операций
    
    Использует креды команды (client_id и client_secret)
    """
    return await _post_with_fallback(
        f"{request.bank_url}/auth/bank-token",
        params={
            "client_id": TEAM_CLIENT_ID,
            "client_secret": TEAM_CLIENT_SECRET
        },
        headers={"accept": "application/json"}
    )


@router.post("/request-consent")
async def request_consent(request: ConsentRequest):
    """
    ШАГ 2: Запросить согласие на доступ к счетам клиента
    
    Требуется банковский токен из шага 1
    """
    # Запрос на создание consent (формат согласно API банков)
    consent_data = {
        "client_id": request.client_id,
        "permissions": [
            "ReadAccountsBasic", 
            "ReadAccountsDetail", 
            "ReadBalances", 
            "ReadTransactionsDetail"
        ],
        "expiration_date": "2025-12-31T23:59:59.000Z"
    }

    return await _post_with_fallback(
        f"{request.bank_url}/account-consents/request",
        headers={
            "Authorization": f"Bearer {request.bank_token}",
            "Content-Type": "application/json",
            "x-requesting-bank": TEAM_CLIENT_ID
        },
        json_payload=consent_data
    )


@router.post("/accounts-with-consent")
async def get_accounts_with_consent(request: AccountsWithConsentRequest):
    """
    ШАГ 3: Получить счета клиента используя consent
    
    Требуется банковский токен и consent_id из предыдущих шагов
    """
    url = f"{request.bank_url}/accounts"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {request.bank_token}",
        "x-consent-id": request.consent_id,
        "x-requesting-bank": TEAM_CLIENT_ID
    }
    params = {"client_id": request.client_id}

    return await _get_with_fallback(url, params=params, headers=headers)


@router.post("/login")
async def proxy_login(request: LoginRequest):
    """
    УСТАРЕВШИЙ: Прямой логин (оставлен для обратной совместимости)
    
    Используйте новый flow: bank-token -> request-consent -> accounts-with-consent
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{request.bank_url}/auth/login",
                json={
                    "username": request.username,
                    "password": request.password
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(response.status_code, "Authentication failed")
            
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(504, "Bank server timeout")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Connection error: {str(e)}")


@router.post("/accounts")
async def proxy_accounts(request: ProxyRequest):
    """
    Проксирует запрос получения счетов к другому банку
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{request.bank_url}{request.endpoint}",
                headers={
                    "Authorization": f"Bearer {request.token}"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(response.status_code, "Failed to fetch accounts")
            
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(504, "Bank server timeout")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Connection error: {str(e)}")


@router.post("/balances-with-consent")
async def get_balance_with_consent(
    account_id: str,
    bank_url: str,
    bank_token: str,
    consent_id: str
):
    """
    Получить баланс счета используя consent (правильный OpenBanking flow)
    """
    url = f"{bank_url}/accounts/{account_id}/balances"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {bank_token}",
        "x-consent-id": consent_id,
        "x-requesting-bank": TEAM_CLIENT_ID
    }

    return await _get_with_fallback(url, headers=headers)


@router.get("/accounts/{account_id}/balances")
async def proxy_balance(
    account_id: str,
    bank_url: str,
    token: str
):
    """
    УСТАРЕВШИЙ: Получить баланс (старый метод, оставлен для совместимости)
    
    Используйте balances-with-consent для правильного OpenBanking flow
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{bank_url}/accounts/{account_id}/balances",
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(response.status_code, "Failed to fetch balance")
            
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(504, "Bank server timeout")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Connection error: {str(e)}")

