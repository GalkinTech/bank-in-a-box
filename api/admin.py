"""
Admin API - для просмотра капитала и транзакций
Iteration 3
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

from database import get_db
from models import BankCapital, InterbankTransfer, Payment, Account, BankSettings, KeyRateHistory

router = APIRouter(prefix="/admin", tags=["Admin"])


class KeyRateUpdate(BaseModel):
    """Обновление ключевой ставки"""
    rate: float
    changed_by: str = "admin"


@router.get("/capital")
async def get_capital(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить капитал банка
    
    Для админ панели
    """
    result = await db.execute(select(BankCapital))
    capitals = result.scalars().all()
    
    return {
        "banks": [
            {
                "bank_code": cap.bank_code,
                "capital": float(cap.capital),
                "initial_capital": float(cap.initial_capital),
                "change": float(cap.capital - cap.initial_capital),
                "total_deposits": float(cap.total_deposits),
                "total_loans": float(cap.total_loans),
                "updated_at": cap.updated_at.isoformat()
            }
            for cap in capitals
        ]
    }


@router.get("/transfers")
async def get_transfers(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить межбанковские переводы
    
    Для админ панели
    """
    result = await db.execute(
        select(InterbankTransfer)
        .order_by(InterbankTransfer.created_at.desc())
        .limit(limit)
    )
    transfers = result.scalars().all()
    
    return {
        "transfers": [
            {
                "transfer_id": t.transfer_id,
                "from_bank": t.from_bank,
                "to_bank": t.to_bank,
                "amount": float(t.amount),
                "status": t.status,
                "created_at": t.created_at.isoformat()
            }
            for t in transfers
        ]
    }


@router.get("/payments")
async def get_all_payments(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить все платежи банка
    
    Для админ панели
    """
    result = await db.execute(
        select(Payment)
        .order_by(Payment.creation_date_time.desc())
        .limit(limit)
    )
    payments = result.scalars().all()
    
    return {
        "payments": [
            {
                "payment_id": p.payment_id,
                "amount": float(p.amount),
                "destination_account": p.destination_account,
                "destination_bank": p.destination_bank,
                "description": p.description,
                "status": p.status,
                "created_at": p.creation_date_time.isoformat()
            }
            for p in payments
        ]
    }


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Общая статистика банка
    """
    # Капитал
    capital_result = await db.execute(select(BankCapital).limit(1))
    capital = capital_result.scalar_one_or_none()
    
    # Подсчет платежей
    payments_count_result = await db.execute(
        select(func.count(Payment.id))
    )
    payments_count = payments_count_result.scalar()
    
    # Подсчет счетов
    accounts_count_result = await db.execute(
        select(func.count(Account.id))
    )
    accounts_count = accounts_count_result.scalar()
    
    # Общая сумма на счетах
    total_balance_result = await db.execute(
        select(func.sum(Account.balance))
    )
    total_balance = total_balance_result.scalar() or 0
    
    return {
        "capital": float(capital.capital) if capital else 0,
        "initial_capital": float(capital.initial_capital) if capital else 0,
        "accounts_count": accounts_count,
        "total_balance": float(total_balance),
        "payments_count": payments_count,
        "pool_status": "balanced" if capital and abs(float(capital.capital) - float(total_balance)) < 1000 else "imbalanced"
    }


# === Key Rate Management ===

@router.get("/key-rate")
async def get_key_rate(db: AsyncSession = Depends(get_db)):
    """
    Получить текущую ключевую ставку ЦБ
    """
    # Попробовать получить из BankSettings
    result = await db.execute(
        select(BankSettings).where(BankSettings.key == "key_rate")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        current_rate = float(setting.value)
    else:
        # Default rate
        current_rate = 7.50
    
    # Get latest from history
    history_result = await db.execute(
        select(KeyRateHistory)
        .order_by(KeyRateHistory.created_at.desc())
        .limit(1)
    )
    latest_history = history_result.scalar_one_or_none()
    
    return {
        "data": {
            "current_rate": current_rate,
            "effective_from": latest_history.effective_from.isoformat() if latest_history else datetime.utcnow().isoformat(),
            "changed_by": latest_history.changed_by if latest_history else "system",
            "last_updated": latest_history.created_at.isoformat() if latest_history else datetime.utcnow().isoformat()
        }
    }


@router.put("/key-rate")
async def update_key_rate(
    update: KeyRateUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Изменить ключевую ставку ЦБ
    """
    # Валидация ставки
    if update.rate < 0 or update.rate > 100:
        raise HTTPException(400, "Rate must be between 0 and 100")
    
    # Обновить в BankSettings
    result = await db.execute(
        select(BankSettings).where(BankSettings.key == "key_rate")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = str(update.rate)
        setting.updated_at = datetime.utcnow()
    else:
        setting = BankSettings(
            key="key_rate",
            value=str(update.rate)
        )
        db.add(setting)
    
    # Добавить в историю
    history = KeyRateHistory(
        rate=Decimal(str(update.rate)),
        effective_from=datetime.utcnow(),
        changed_by=update.changed_by
    )
    db.add(history)
    
    await db.commit()
    
    return {
        "data": {
            "rate": update.rate,
            "effective_from": history.effective_from.isoformat(),
            "changed_by": update.changed_by
        },
        "meta": {
            "message": "Key rate updated successfully"
        }
    }


@router.get("/key-rate/history")
async def get_key_rate_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю изменений ключевой ставки
    """
    result = await db.execute(
        select(KeyRateHistory)
        .order_by(KeyRateHistory.created_at.desc())
        .limit(limit)
    )
    history = result.scalars().all()
    
    return {
        "data": [
            {
                "rate": float(h.rate),
                "effective_from": h.effective_from.isoformat(),
                "changed_by": h.changed_by,
                "created_at": h.created_at.isoformat()
            }
            for h in history
        ]
    }


# === Bank Settings Management ===

class BankSettingsUpdate(BaseModel):
    """Обновление настроек банка"""
    auto_approve_consents: bool


@router.get("/banks/{bank_code}/settings")
async def get_bank_settings(
    bank_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить настройки банка
    """
    # Get auto_approve_consents setting
    result = await db.execute(
        select(BankSettings).where(BankSettings.key == "auto_approve_consents")
    )
    setting = result.scalar_one_or_none()
    
    auto_approve = setting.value.lower() == "true" if setting else True
    
    return {
        "data": {
            "bank_code": bank_code,
            "auto_approve_consents": auto_approve
        }
    }


@router.put("/banks/{bank_code}/settings")
async def update_bank_settings(
    bank_code: str,
    update: BankSettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить настройки банка
    """
    # Update auto_approve_consents
    result = await db.execute(
        select(BankSettings).where(BankSettings.key == "auto_approve_consents")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = "true" if update.auto_approve_consents else "false"
        setting.updated_at = datetime.utcnow()
    else:
        setting = BankSettings(
            key="auto_approve_consents",
            value="true" if update.auto_approve_consents else "false"
        )
        db.add(setting)
    
    await db.commit()
    
    return {
        "data": {
            "bank_code": bank_code,
            "auto_approve_consents": update.auto_approve_consents
        },
        "meta": {
            "message": "Settings updated successfully"
        }
    }

