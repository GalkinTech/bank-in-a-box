"""
Payment Service - логика переводов
Iteration 3
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from datetime import datetime
from typing import Optional, Tuple
import uuid

from models import Account, Payment, InterbankTransfer, BankCapital, Client
from config import config


class PaymentService:
    """Сервис для обработки платежей"""
    
    @staticmethod
    async def initiate_payment(
        db: AsyncSession,
        from_account_number: str,
        to_account_number: str,
        amount: Decimal,
        description: str = ""
    ) -> Tuple[Payment, Optional[InterbankTransfer]]:
        """
        Инициация платежа
        
        Returns:
            (Payment, InterbankTransfer или None)
        """
        # Найти счет отправителя
        result = await db.execute(
            select(Account).where(Account.account_number == from_account_number)
        )
        from_account = result.scalar_one_or_none()
        
        if not from_account:
            raise ValueError("Source account not found")
        
        if from_account.balance < amount:
            raise ValueError("Insufficient funds")
        
        # Создать payment
        payment_id = f"pay-{uuid.uuid4().hex[:12]}"
        
        payment = Payment(
            payment_id=payment_id,
            account_id=from_account.id,
            amount=amount,
            currency="RUB",
            destination_account=to_account_number,
            description=description,
            status="AcceptedSettlementInProcess"
        )
        
        # Списать со счета отправителя
        from_account.balance -= amount
        
        # Попытаться найти получателя в своем банке
        result = await db.execute(
            select(Account).where(Account.account_number == to_account_number)
        )
        to_account = result.scalar_one_or_none()
        
        interbank_transfer = None
        
        db.add(payment)
        
        if to_account:
            # Внутрибанковский перевод
            to_account.balance += amount
            payment.status = "AcceptedSettlementCompleted"
            payment.destination_bank = config.BANK_CODE
            payment.status_update_date_time = datetime.utcnow()
        else:
            # Межбанковский перевод
            # TODO: Вызвать API другого банка через прокси
            # Пока помечаем как обработан
            payment.destination_bank = "external"
            payment.status = "AcceptedSettlementCompleted"  # В MVP: мгновенное исполнение
            payment.status_update_date_time = datetime.utcnow()
            
            # Создать запись межбанкового перевода
            transfer_id = f"transfer-{uuid.uuid4().hex[:12]}"
            interbank_transfer = InterbankTransfer(
                transfer_id=transfer_id,
                payment_id=None,  # Пока без FK
                from_bank=config.BANK_CODE,
                to_bank="external",
                amount=amount,
                status="completed"
            )
            db.add(interbank_transfer)
        
        await db.commit()
        await db.refresh(payment)
        
        return payment, interbank_transfer
    
    @staticmethod
    async def get_payment(
        db: AsyncSession,
        payment_id: str
    ) -> Optional[Payment]:
        """Получить статус платежа"""
        result = await db.execute(
            select(Payment).where(Payment.payment_id == payment_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_bank_capital(
        db: AsyncSession,
        amount_change: Decimal,
        reason: str = ""
    ):
        """
        Обновить капитал банка
        
        amount_change: положительное = увеличение, отрицательное = уменьшение
        """
        bank_code = config.BANK_CODE
        
        # Получить или создать запись капитала
        result = await db.execute(
            select(BankCapital).where(BankCapital.bank_code == bank_code)
        )
        capital_record = result.scalar_one_or_none()
        
        if not capital_record:
            # Создать если нет
            capital_record = BankCapital(
                bank_code=bank_code,
                capital=Decimal("3500000.00"),  # Начальный капитал
                initial_capital=Decimal("3500000.00")
            )
            db.add(capital_record)
        
        # Обновить капитал
        capital_record.capital += amount_change
        capital_record.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return capital_record

