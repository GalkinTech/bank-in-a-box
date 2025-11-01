"""
Payments API - Инициирование переводов
OpenBanking Russia Payments API compatible
Спецификация: https://wiki.opendatarussia.ru/specifications (Payments API)
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from decimal import Decimal
import uuid

from database import get_db
from models import Payment, Account
from services.auth_service import get_current_client
from services.payment_service import PaymentService


router = APIRouter(prefix="/payments", tags=["Payments"])


# === Pydantic Models (OpenBanking Russia format) ===

class AmountModel(BaseModel):
    """Сумма платежа"""
    amount: str = Field(..., description="Сумма в формате строки")
    currency: str = "RUB"


class AccountIdentification(BaseModel):
    """Идентификация счета"""
    schemeName: str = "RU.CBR.PAN"
    identification: str = Field(..., description="Номер счета")
    name: Optional[str] = None


class PaymentInitiation(BaseModel):
    """Данные для инициации платежа"""
    instructionIdentification: str = Field(default_factory=lambda: f"instr-{uuid.uuid4().hex[:8]}")
    endToEndIdentification: str = Field(default_factory=lambda: f"e2e-{uuid.uuid4().hex[:8]}")
    instructedAmount: AmountModel
    debtorAccount: AccountIdentification
    creditorAccount: AccountIdentification
    remittanceInformation: Optional[dict] = None


class PaymentRequest(BaseModel):
    """Запрос создания платежа (OpenBanking Russia format)"""
    data: dict = Field(..., description="Содержит initiation")
    risk: Optional[dict] = {}


class PaymentData(BaseModel):
    """Данные платежа в ответе"""
    paymentId: str
    status: str
    creationDateTime: str
    statusUpdateDateTime: str


class PaymentResponse(BaseModel):
    """Ответ с платежом"""
    data: PaymentData
    links: dict
    meta: Optional[dict] = {}


# === Endpoints ===

@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(
    request: PaymentRequest,
    x_fapi_interaction_id: Optional[str] = Header(None, alias="x-fapi-interaction-id"),
    x_fapi_customer_ip_address: Optional[str] = Header(None, alias="x-fapi-customer-ip-address"),
    current_client: dict = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Инициирование платежа
    
    OpenBanking Russia Payments API
    POST /payments
    
    Спецификация: https://wiki.opendatarussia.ru/specifications
    """
    if not current_client:
        raise HTTPException(401, "Unauthorized")
    
    # Извлечь данные из request
    initiation = request.data.get("initiation")
    if not initiation:
        raise HTTPException(400, "Missing initiation data")
    
    amount_data = initiation.get("instructedAmount", {})
    debtor_account = initiation.get("debtorAccount", {})
    creditor_account = initiation.get("creditorAccount", {})
    
    # Описание платежа
    remittance = initiation.get("remittanceInformation", {})
    description = remittance.get("unstructured", "") if remittance else ""
    
    try:
        # Инициировать платеж
        payment, interbank = await PaymentService.initiate_payment(
            db=db,
            from_account_number=debtor_account.get("identification"),
            to_account_number=creditor_account.get("identification"),
            amount=Decimal(amount_data.get("amount", "0")),
            description=description
        )
        
        # Формируем ответ OpenBanking Russia
        now = datetime.utcnow()
        
        payment_data = PaymentData(
            paymentId=payment.payment_id,
            status=payment.status,
            creationDateTime=payment.creation_date_time.isoformat() + "Z",
            statusUpdateDateTime=payment.status_update_date_time.isoformat() + "Z"
        )
        
        return PaymentResponse(
            data=payment_data,
            links={
                "self": f"/payments/{payment.payment_id}"
            },
            meta={}
        )
        
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    x_fapi_interaction_id: Optional[str] = Header(None, alias="x-fapi-interaction-id"),
    current_client: dict = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение статуса платежа
    
    OpenBanking Russia Payments API
    GET /payments/{paymentId}
    """
    if not current_client:
        raise HTTPException(401, "Unauthorized")
    
    payment = await PaymentService.get_payment(db, payment_id)
    
    if not payment:
        raise HTTPException(404, "Payment not found")
    
    # TODO: Проверить что клиент имеет право просматривать этот платеж
    
    payment_data = PaymentData(
        paymentId=payment.payment_id,
        status=payment.status,
        creationDateTime=payment.creation_date_time.isoformat() + "Z",
        statusUpdateDateTime=payment.status_update_date_time.isoformat() + "Z"
    )
    
    return PaymentResponse(
        data=payment_data,
        links={
            "self": f"/payments/{payment_id}"
        }
    )

