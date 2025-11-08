"""
Cards API - Управление банковскими картами
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid
import random

from ..database import get_db
from ..models import Card, Account, Client
from ..services.auth_service import require_any_token, require_client
from ..services.consent_service import ConsentService


router = APIRouter(prefix="/cards", tags=["8 Карты"])


# === Pydantic Models ===

class CardResponse(BaseModel):
    """Данные карты в ответе"""
    cardId: str
    cardNumber: str  # Маскированный номер (4 последние цифры)
    cardNumberFull: Optional[str] = None  # Полный номер (только для владельца)
    cardType: str  # debit, credit
    cardName: str
    holderName: str
    expiryMonth: int
    expiryYear: int
    accountNumber: str  # Счет, к которому привязана карта
    accountBalance: Optional[str] = None
    status: str
    dailyLimit: Optional[str] = None
    monthlyLimit: Optional[str] = None
    issuedAt: str


class CreateCardRequest(BaseModel):
    """Запрос на создание новой карты"""
    account_number: str = Field(..., description="Номер счета для привязки карты")
    card_name: Optional[str] = Field("Visa Classic", description="Название карты")
    card_type: Optional[str] = Field("debit", description="Тип карты: debit или credit")


class UpdateCardStatusRequest(BaseModel):
    """Запрос на изменение статуса карты"""
    status: str = Field(..., description="Новый статус: active, blocked, expired")


class CardLimitsRequest(BaseModel):
    """Запрос на обновление лимитов карты"""
    daily_limit: Optional[float] = Field(None, description="Дневной лимит")
    monthly_limit: Optional[float] = Field(None, description="Месячный лимит")


# === Helper Functions ===

def generate_card_number(bank_code: str) -> str:
    """Генерация номера карты (16 цифр) по алгоритму Луна"""
    # BIN коды для разных банков
    bins = {
        'vbank': '427610',
        'abank': '427620',
        'sbank': '427630'
    }
    
    from ..config import config
    bin_code = bins.get(config.BANK_CODE, '427600')
    
    # 9 случайных цифр
    account_number = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    
    # Контрольная цифра по алгоритму Луна (упрощенная версия)
    card_without_check = bin_code + account_number
    check_digit = str((10 - sum(int(d) for d in card_without_check) % 10) % 10)
    
    return card_without_check + check_digit


def mask_card_number(card_number: str) -> str:
    """Маскирование номера карты (показываем только последние 4 цифры)"""
    if len(card_number) < 4:
        return card_number
    return "**** **** **** " + card_number[-4:]


# === Endpoints ===

@router.get("", summary="1. Получить список карт")
async def get_cards(
    client_id: Optional[str] = Query(None, description="ID клиента (для bank_token)"),
    x_requesting_bank: Optional[str] = Header(None, alias="X-Requesting-Bank"),
    x_consent_id: Optional[str] = Header(None, alias="X-Consent-Id"),
    token_data: dict = Depends(require_any_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех карт клиента
    
    **Возвращает:**
    - Список карт с маскированными номерами
    - Информацию о привязанных счетах
    - Лимиты и статусы
    
    **Межбанковый доступ:**
    - Требуется согласие с permission `ReadCards`
    - Заголовки: `X-Requesting-Bank`, `X-Consent-Id`
    """
    # Определяем, чей это запрос
    if x_requesting_bank:
        # Межбанковский запрос - требуется согласие
        if not client_id:
            raise HTTPException(400, "client_id required for interbank requests")
        
        # Проверить согласие
        consent = await ConsentService.check_consent(
            db=db,
            client_person_id=client_id,
            requesting_bank=x_requesting_bank,
            permissions=["ReadCards"],
            consent_id=x_consent_id
        )
        
        if not consent:
            raise HTTPException(
                403,
                {
                    "error": "CONSENT_REQUIRED",
                    "message": "Valid consent with 'ReadCards' permission required",
                    "how_to_get_consent": "POST /account-consents with permissions: ['ReadCards']"
                }
            )
        
        target_client_id = client_id
    else:
        # Локальный запрос
        if token_data.get("type") == "client":
            target_client_id = token_data.get("client_id")
        elif client_id:
            target_client_id = client_id
        else:
            raise HTTPException(401, "Unauthorized")
    
    # Найти клиента
    result = await db.execute(
        select(Client).where(Client.person_id == target_client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Получить все карты клиента
    cards_result = await db.execute(
        select(Card, Account).join(Account).where(
            Card.client_id == client.id
        ).order_by(Card.issued_at.desc())
    )
    
    cards_accounts = cards_result.all()
    
    cards_list = []
    for card, account in cards_accounts:
        cards_list.append(CardResponse(
            cardId=card.card_id,
            cardNumber=mask_card_number(card.card_number),
            cardType=card.card_type,
            cardName=card.card_name,
            holderName=card.holder_name,
            expiryMonth=card.expiry_month,
            expiryYear=card.expiry_year,
            accountNumber=account.account_number,
            accountBalance=str(account.balance),
            status=card.status,
            dailyLimit=str(card.daily_limit) if card.daily_limit else None,
            monthlyLimit=str(card.monthly_limit) if card.monthly_limit else None,
            issuedAt=card.issued_at.isoformat() + "Z"
        ))
    
    return {
        "data": {
            "cards": cards_list,
            "total": len(cards_list)
        },
        "meta": {}
    }


@router.get("/{card_id}", summary="2. Получить детали карты")
async def get_card_details(
    card_id: str,
    show_full_number: bool = Query(False, description="Показать полный номер карты"),
    client_id: Optional[str] = Query(None, description="ID клиента (для bank_token)"),
    x_requesting_bank: Optional[str] = Header(None, alias="X-Requesting-Bank"),
    x_consent_id: Optional[str] = Header(None, alias="X-Consent-Id"),
    token_data: dict = Depends(require_any_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о карте
    
    **Параметры:**
    - `show_full_number=true` - показать полный номер (только для владельца)
    
    **Межбанковый доступ:**
    - Требуется согласие с permission `ReadCards`
    - Полный номер карты доступен только владельцу (локальный запрос)
    """
    # Определяем, чей это запрос
    if x_requesting_bank:
        # Межбанковский запрос - требуется согласие
        if not client_id:
            raise HTTPException(400, "client_id required for interbank requests")
        
        # Проверить согласие
        consent = await ConsentService.check_consent(
            db=db,
            client_person_id=client_id,
            requesting_bank=x_requesting_bank,
            permissions=["ReadCards"],
            consent_id=x_consent_id
        )
        
        if not consent:
            raise HTTPException(403, {
                "error": "CONSENT_REQUIRED",
                "message": "Valid consent with 'ReadCards' permission required"
            })
        
        target_client_id = client_id
        # Межбанковый запрос не может видеть полный номер
        show_full_number = False
    else:
        # Локальный запрос
        if token_data.get("type") == "client":
            target_client_id = token_data.get("client_id")
        elif client_id:
            target_client_id = client_id
        else:
            raise HTTPException(401, "Unauthorized")
    
    # Найти клиента
    result = await db.execute(
        select(Client).where(Client.person_id == target_client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Найти карту
    card_result = await db.execute(
        select(Card, Account).join(Account).where(
            Card.card_id == card_id,
            Card.client_id == client.id
        )
    )
    
    card_account = card_result.first()
    
    if not card_account:
        raise HTTPException(404, "Card not found")
    
    card, account = card_account
    
    return {
        "data": CardResponse(
            cardId=card.card_id,
            cardNumber=mask_card_number(card.card_number),
            cardNumberFull=card.card_number if show_full_number else None,
            cardType=card.card_type,
            cardName=card.card_name,
            holderName=card.holder_name,
            expiryMonth=card.expiry_month,
            expiryYear=card.expiry_year,
            accountNumber=account.account_number,
            accountBalance=str(account.balance),
            status=card.status,
            dailyLimit=str(card.daily_limit) if card.daily_limit else None,
            monthlyLimit=str(card.monthly_limit) if card.monthly_limit else None,
            issuedAt=card.issued_at.isoformat() + "Z"
        ),
        "meta": {}
    }


@router.post("", summary="3. Выпустить новую карту")
async def create_card(
    request: CreateCardRequest,
    client_id: Optional[str] = Query(None, description="ID клиента (для bank_token)"),
    x_requesting_bank: Optional[str] = Header(None, alias="X-Requesting-Bank"),
    x_consent_id: Optional[str] = Header(None, alias="X-Consent-Id"),
    token_data: dict = Depends(require_any_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Выпустить новую карту и привязать к счету
    
    **Требования:**
    - Счет должен быть типа checking или savings
    - Счет должен принадлежать клиенту
    - К одному счету можно привязать несколько карт
    
    **Межбанковый доступ:**
    - Требуется согласие с permission `ManageCards`
    """
    # Определяем, чей это запрос
    if x_requesting_bank:
        # Межбанковский запрос - требуется согласие
        if not client_id:
            raise HTTPException(400, "client_id required for interbank requests")
        
        # Проверить согласие
        consent = await ConsentService.check_consent(
            db=db,
            client_person_id=client_id,
            requesting_bank=x_requesting_bank,
            permissions=["ManageCards"],
            consent_id=x_consent_id
        )
        
        if not consent:
            raise HTTPException(403, {
                "error": "CONSENT_REQUIRED",
                "message": "Valid consent with 'ManageCards' permission required"
            })
        
        target_client_id = client_id
    else:
        # Локальный запрос
        if token_data.get("type") == "client":
            target_client_id = token_data.get("client_id")
        elif client_id:
            target_client_id = client_id
        else:
            raise HTTPException(401, "Unauthorized")
    
    # Найти клиента
    result = await db.execute(
        select(Client).where(Client.person_id == target_client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Найти счет
    account_result = await db.execute(
        select(Account).where(
            Account.account_number == request.account_number,
            Account.client_id == client.id,
            Account.account_type.in_(['checking', 'savings'])
        )
    )
    account = account_result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(404, "Account not found or invalid type. Only checking/savings accounts can have cards.")
    
    # Валидация типа карты
    if request.card_type not in ['debit', 'credit']:
        raise HTTPException(400, "Invalid card_type. Must be 'debit' or 'credit'")
    
    # Генерировать номер карты
    from ..config import config
    card_number = generate_card_number(config.BANK_CODE)
    
    # Проверить уникальность
    existing = await db.execute(
        select(Card).where(Card.card_number == card_number)
    )
    if existing.scalar_one_or_none():
        # Повторить генерацию
        card_number = generate_card_number(config.BANK_CODE)
    
    # Имя держателя
    holder_name = client.full_name.upper()
    
    # Срок действия: 3 года
    expiry_month = random.randint(1, 12)
    expiry_year = datetime.now().year + 3
    
    # Лимиты по умолчанию в зависимости от сегмента
    limits = {
        'student': (Decimal('50000'), Decimal('200000')),
        'pensioner': (Decimal('30000'), Decimal('150000')),
        'employee': (Decimal('100000'), Decimal('500000')),
        'entrepreneur': (Decimal('200000'), Decimal('1000000')),
        'vip': (Decimal('500000'), Decimal('3000000')),
        'business': (Decimal('1000000'), Decimal('5000000'))
    }
    
    daily_limit, monthly_limit = limits.get(
        client.segment, 
        (Decimal('100000'), Decimal('500000'))
    )
    
    # Создать карту
    new_card = Card(
        card_id=f"card-{uuid.uuid4().hex[:12]}",
        account_id=account.id,
        client_id=client.id,
        card_number=card_number,
        card_type=request.card_type,
        card_name=request.card_name,
        holder_name=holder_name,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        daily_limit=daily_limit,
        monthly_limit=monthly_limit,
        status='active',
        issued_at=datetime.utcnow()
    )
    
    db.add(new_card)
    await db.commit()
    await db.refresh(new_card)
    
    return {
        "data": CardResponse(
            cardId=new_card.card_id,
            cardNumber=mask_card_number(new_card.card_number),
            cardNumberFull=new_card.card_number,  # Показываем полный номер при создании
            cardType=new_card.card_type,
            cardName=new_card.card_name,
            holderName=new_card.holder_name,
            expiryMonth=new_card.expiry_month,
            expiryYear=new_card.expiry_year,
            accountNumber=account.account_number,
            accountBalance=str(account.balance),
            status=new_card.status,
            dailyLimit=str(new_card.daily_limit) if new_card.daily_limit else None,
            monthlyLimit=str(new_card.monthly_limit) if new_card.monthly_limit else None,
            issuedAt=new_card.issued_at.isoformat() + "Z"
        ),
        "meta": {
            "message": "Card created successfully. Save the card number in a secure place!"
        }
    }


@router.put("/{card_id}/status", summary="4. Изменить статус карты")
async def update_card_status(
    card_id: str,
    request: UpdateCardStatusRequest,
    client_id: Optional[str] = Query(None, description="ID клиента (для bank_token)"),
    x_requesting_bank: Optional[str] = Header(None, alias="X-Requesting-Bank"),
    x_consent_id: Optional[str] = Header(None, alias="X-Consent-Id"),
    token_data: dict = Depends(require_any_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Изменить статус карты (блокировка/разблокировка)
    
    **Статусы:**
    - `active` - активна
    - `blocked` - заблокирована
    - `expired` - истек срок действия
    
    **Межбанковый доступ:**
    - Требуется согласие с permission `ManageCards`
    """
    # Определяем, чей это запрос
    if x_requesting_bank:
        # Межбанковский запрос - требуется согласие
        if not client_id:
            raise HTTPException(400, "client_id required for interbank requests")
        
        # Проверить согласие
        consent = await ConsentService.check_consent(
            db=db,
            client_person_id=client_id,
            requesting_bank=x_requesting_bank,
            permissions=["ManageCards"],
            consent_id=x_consent_id
        )
        
        if not consent:
            raise HTTPException(403, {
                "error": "CONSENT_REQUIRED",
                "message": "Valid consent with 'ManageCards' permission required"
            })
        
        target_client_id = client_id
    else:
        # Локальный запрос
        if token_data.get("type") == "client":
            target_client_id = token_data.get("client_id")
        elif client_id:
            target_client_id = client_id
        else:
            raise HTTPException(401, "Unauthorized")
    
    # Найти клиента
    result = await db.execute(
        select(Client).where(Client.person_id == target_client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Найти карту
    card_result = await db.execute(
        select(Card).where(
            Card.card_id == card_id,
            Card.client_id == client.id
        )
    )
    card = card_result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(404, "Card not found")
    
    # Валидация статуса
    if request.status not in ['active', 'blocked', 'expired']:
        raise HTTPException(400, "Invalid status. Must be 'active', 'blocked', or 'expired'")
    
    # Обновить статус
    old_status = card.status
    card.status = request.status
    
    if request.status == 'blocked':
        card.blocked_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "data": {
            "cardId": card.card_id,
            "oldStatus": old_status,
            "newStatus": card.status,
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        },
        "meta": {
            "message": f"Card status changed from {old_status} to {request.status}"
        }
    }


@router.put("/{card_id}/limits", summary="5. Обновить лимиты карты")
async def update_card_limits(
    card_id: str,
    request: CardLimitsRequest,
    client_id: Optional[str] = Query(None, description="ID клиента (для bank_token)"),
    x_requesting_bank: Optional[str] = Header(None, alias="X-Requesting-Bank"),
    x_consent_id: Optional[str] = Header(None, alias="X-Consent-Id"),
    token_data: dict = Depends(require_any_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить дневной и месячный лимиты карты
    
    **Межбанковый доступ:**
    - Требуется согласие с permission `ManageCards`
    """
    # Определяем, чей это запрос
    if x_requesting_bank:
        # Межбанковский запрос - требуется согласие
        if not client_id:
            raise HTTPException(400, "client_id required for interbank requests")
        
        # Проверить согласие
        consent = await ConsentService.check_consent(
            db=db,
            client_person_id=client_id,
            requesting_bank=x_requesting_bank,
            permissions=["ManageCards"],
            consent_id=x_consent_id
        )
        
        if not consent:
            raise HTTPException(403, {
                "error": "CONSENT_REQUIRED",
                "message": "Valid consent with 'ManageCards' permission required"
            })
        
        target_client_id = client_id
    else:
        # Локальный запрос
        if token_data.get("type") == "client":
            target_client_id = token_data.get("client_id")
        elif client_id:
            target_client_id = client_id
        else:
            raise HTTPException(401, "Unauthorized")
    
    # Найти клиента
    result = await db.execute(
        select(Client).where(Client.person_id == target_client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Найти карту
    card_result = await db.execute(
        select(Card).where(
            Card.card_id == card_id,
            Card.client_id == client.id
        )
    )
    card = card_result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(404, "Card not found")
    
    # Обновить лимиты
    if request.daily_limit is not None:
        card.daily_limit = Decimal(str(request.daily_limit))
    
    if request.monthly_limit is not None:
        card.monthly_limit = Decimal(str(request.monthly_limit))
    
    await db.commit()
    
    return {
        "data": {
            "cardId": card.card_id,
            "dailyLimit": str(card.daily_limit) if card.daily_limit else None,
            "monthlyLimit": str(card.monthly_limit) if card.monthly_limit else None,
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        },
        "meta": {
            "message": "Card limits updated successfully"
        }
    }


@router.delete("/{card_id}", summary="6. Удалить карту")
async def delete_card(
    card_id: str,
    client_id: Optional[str] = Query(None, description="ID клиента (для bank_token)"),
    x_requesting_bank: Optional[str] = Header(None, alias="X-Requesting-Bank"),
    x_consent_id: Optional[str] = Header(None, alias="X-Consent-Id"),
    token_data: dict = Depends(require_any_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить карту (перевыпуск или закрытие)
    
    **Важно:** Счет остается активным, удаляется только карта
    
    **Межбанковый доступ:**
    - Требуется согласие с permission `ManageCards`
    """
    # Определяем, чей это запрос
    if x_requesting_bank:
        # Межбанковский запрос - требуется согласие
        if not client_id:
            raise HTTPException(400, "client_id required for interbank requests")
        
        # Проверить согласие
        consent = await ConsentService.check_consent(
            db=db,
            client_person_id=client_id,
            requesting_bank=x_requesting_bank,
            permissions=["ManageCards"],
            consent_id=x_consent_id
        )
        
        if not consent:
            raise HTTPException(403, {
                "error": "CONSENT_REQUIRED",
                "message": "Valid consent with 'ManageCards' permission required"
            })
        
        target_client_id = client_id
    else:
        # Локальный запрос
        if token_data.get("type") == "client":
            target_client_id = token_data.get("client_id")
        elif client_id:
            target_client_id = client_id
        else:
            raise HTTPException(401, "Unauthorized")
    
    # Найти клиента
    result = await db.execute(
        select(Client).where(Client.person_id == target_client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Найти карту
    card_result = await db.execute(
        select(Card).where(
            Card.card_id == card_id,
            Card.client_id == client.id
        )
    )
    card = card_result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(404, "Card not found")
    
    # Удалить карту
    await db.delete(card)
    await db.commit()
    
    return {
        "data": {
            "cardId": card_id,
            "deletedAt": datetime.utcnow().isoformat() + "Z"
        },
        "meta": {
            "message": "Card deleted successfully"
        }
    }

