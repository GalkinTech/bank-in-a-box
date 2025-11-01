"""
SQLAlchemy модели для банка
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, ARRAY, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Client(Base):
    """Клиент банка"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True)
    person_id = Column(String(100), unique=True)  # ID из общей базы людей
    client_type = Column(String(20))  # individual / legal
    full_name = Column(String(255), nullable=False)
    segment = Column(String(50))  # employee, student, pensioner, etc.
    birth_year = Column(Integer)
    monthly_income = Column(Numeric(15, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    accounts = relationship("Account", back_populates="client")


class Account(Base):
    """Счет клиента"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    account_type = Column(String(50))  # checking, savings, deposit
    balance = Column(Numeric(15, 2), default=0)
    currency = Column(String(3), default="RUB")
    status = Column(String(20), default="active")
    opened_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Transaction(Base):
    """Транзакция по счету"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    transaction_id = Column(String(100), unique=True, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    direction = Column(String(10))  # credit / debit
    counterparty = Column(String(255))
    description = Column(Text)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="transactions")


class BankSettings(Base):
    """Настройки банка"""
    __tablename__ = "bank_settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthToken(Base):
    """Токены авторизации"""
    __tablename__ = "auth_tokens"
    
    id = Column(Integer, primary_key=True)
    token_type = Column(String(20))  # client / bank
    subject_id = Column(String(100))  # client_id или bank_code
    token_hash = Column(String(255))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConsentRequest(Base):
    """Запросы на согласие (от других банков)"""
    __tablename__ = "consent_requests"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(100), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    requesting_bank = Column(String(100))  # bank_code запрашивающего банка
    requesting_bank_name = Column(String(255))
    permissions = Column(ARRAY(String))  # ReadAccounts, ReadBalances, etc.
    reason = Column(Text)
    status = Column(String(20), default="pending")  # pending / approved / rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime)
    
    # Relationships
    client = relationship("Client")


class Consent(Base):
    """Согласие клиента (активное)"""
    __tablename__ = "consents"
    
    id = Column(Integer, primary_key=True)
    consent_id = Column(String(100), unique=True, nullable=False)
    request_id = Column(Integer, ForeignKey("consent_requests.id"))
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    granted_to = Column(String(100), nullable=False)  # bank_code
    permissions = Column(ARRAY(String), nullable=False)
    status = Column(String(20), default="active")  # active / revoked / expired
    expiration_date_time = Column(DateTime)
    creation_date_time = Column(DateTime, default=datetime.utcnow)
    status_update_date_time = Column(DateTime, default=datetime.utcnow)
    signed_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)
    last_accessed_at = Column(DateTime)
    
    # Relationships
    client = relationship("Client")


class Notification(Base):
    """Уведомления для клиентов"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    notification_type = Column(String(50))  # consent_request / consent_approved / etc
    title = Column(String(255))
    message = Column(Text)
    related_id = Column(String(100))  # request_id or consent_id
    status = Column(String(20), default="unread")  # unread / read
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client")


class Payment(Base):
    """Платеж (OpenBanking Russia Payments API)"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    payment_id = Column(String(100), unique=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)  # Счет-отправитель
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="RUB")
    destination_account = Column(String(255))  # Номер счета получателя
    destination_bank = Column(String(100))  # Код банка получателя
    description = Column(Text)
    status = Column(String(50), default="AcceptedSettlementInProcess")
    # AcceptedSettlementInProcess, AcceptedSettlementCompleted, Rejected
    creation_date_time = Column(DateTime, default=datetime.utcnow)
    status_update_date_time = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account")


class InterbankTransfer(Base):
    """Межбанковский перевод (для отслеживания капитала)"""
    __tablename__ = "interbank_transfers"
    
    id = Column(Integer, primary_key=True)
    transfer_id = Column(String(100), unique=True, nullable=False)
    payment_id = Column(String(100), ForeignKey("payments.payment_id"))
    from_bank = Column(String(100), nullable=False)  # Код банка-отправителя
    to_bank = Column(String(100), nullable=False)  # Код банка-получателя
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String(50), default="processing")  # processing / completed / failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class BankCapital(Base):
    """Капитал банка (для экономической модели)"""
    __tablename__ = "bank_capital"
    
    id = Column(Integer, primary_key=True)
    bank_code = Column(String(100), unique=True, nullable=False)
    capital = Column(Numeric(15, 2), nullable=False)  # Текущий капитал
    initial_capital = Column(Numeric(15, 2), nullable=False)  # Начальный капитал
    total_deposits = Column(Numeric(15, 2), default=0)  # Сумма депозитов клиентов
    total_loans = Column(Numeric(15, 2), default=0)  # Выданные кредиты
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base):
    """Финансовый продукт банка"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(String(100), unique=True, nullable=False)
    product_type = Column(String(50), nullable=False)  # deposit, credit_card, loan
    name = Column(String(255), nullable=False)
    description = Column(Text)
    interest_rate = Column(Numeric(5, 2))  # Процентная ставка
    min_amount = Column(Numeric(15, 2))  # Минимальная сумма
    max_amount = Column(Numeric(15, 2))  # Максимальная сумма
    term_months = Column(Integer)  # Срок в месяцах
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductAgreement(Base):
    """Договор клиента с продуктом (кредит, депозит, карта)"""
    __tablename__ = "product_agreements"
    
    id = Column(Integer, primary_key=True)
    agreement_id = Column(String(100), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"))  # Связанный счет
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String(50), default="active")  # active, closed, defaulted
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client")
    product = relationship("Product")


class ProductApplication(Base):
    """Заявка на продукт (заглушка для API заявок)
    Хранит минимально необходимые поля, используемые эндпоинтами product_applications.
    """
    __tablename__ = "product_applications"
    
    id = Column(Integer, primary_key=True)
    application_id = Column(String(100), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    requested_amount = Column(Numeric(15, 2), nullable=False)
    requested_term_months = Column(Integer)
    status = Column(String(50), default="pending")  # pending, under_review, approved, rejected, cancelled
    decision = Column(String(50))  # approved / rejected
    decision_reason = Column(Text)
    approved_amount = Column(Numeric(15, 2))
    approved_rate = Column(Numeric(7, 4))
    application_data = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    decision_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomerLead(Base):
    """Лид (потенциальный клиент) для персональных предложений"""
    __tablename__ = "customer_leads"
    
    id = Column(Integer, primary_key=True)
    customer_lead_id = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))
    email = Column(String(255))
    interested_products = Column(ARRAY(String))
    source = Column(String(100), default="api")
    status = Column(String(50), default="pending")
    estimated_income = Column(Numeric(15, 2))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    contacted_at = Column(DateTime)
    converted_to_client_id = Column(Integer)  # ID клиента после конверсии (если был)


class ProductOffer(Base):
    """Персональное предложение по продукту"""
    __tablename__ = "product_offers"
    
    id = Column(Integer, primary_key=True)
    offer_id = Column(String(100), unique=True, nullable=False)
    customer_lead_id = Column(String(100))  # внешний id лида (строка)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    personalized_rate = Column(Numeric(7, 4))
    personalized_amount = Column(Numeric(15, 2))
    personalized_term_months = Column(Integer)
    status = Column(String(50), default="pending")  # pending, accepted, expired, cancelled
    valid_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)
    viewed_at = Column(DateTime)
    responded_at = Column(DateTime)


class ProductOfferConsent(Base):
    """Согласие на получение персональных предложений"""
    __tablename__ = "product_offer_consents"
    
    id = Column(Integer, primary_key=True)
    consent_id = Column(String(100), unique=True, nullable=False)
    customer_lead_id = Column(String(100))
    client_id = Column(Integer, ForeignKey("clients.id"))
    permissions = Column(ARRAY(String))
    status = Column(String(50), default="active")  # active, revoked, expired
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)


class VRPConsent(Base):
    """VRP согласие (Variable Recurring Payments)"""
    __tablename__ = "vrp_consents"
    
    id = Column(Integer, primary_key=True)
    consent_id = Column(String(100), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    status = Column(String(50), default="Authorised")
    max_individual_amount = Column(Numeric(15, 2))
    max_amount_period = Column(Numeric(15, 2))
    period_type = Column(String(20))  # day, week, month, year
    max_payments_count = Column(Integer)
    valid_from = Column(DateTime)
    valid_to = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    authorised_at = Column(DateTime)
    revoked_at = Column(DateTime)


class VRPPayment(Base):
    """Платеж по VRP согласию"""
    __tablename__ = "vrp_payments"
    
    id = Column(Integer, primary_key=True)
    payment_id = Column(String(100), unique=True, nullable=False)
    vrp_consent_id = Column(String(100), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="RUB")
    destination_account = Column(String(255))
    destination_bank = Column(String(100))
    description = Column(Text)
    status = Column(String(50), default="AcceptedSettlementInProcess")
    is_recurring = Column(Boolean, default=True)
    recurrence_frequency = Column(String(20))  # daily, weekly, monthly
    next_payment_date = Column(DateTime)
    creation_date_time = Column(DateTime, default=datetime.utcnow)
    status_update_date_time = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)

class KeyRateHistory(Base):
    """История изменений ключевой ставки ЦБ"""
    __tablename__ = "key_rate_history"
    
    id = Column(Integer, primary_key=True)
    rate = Column(Numeric(5, 2), nullable=False)  # Например 7.50%
    effective_from = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(String(100))  # admin
    created_at = Column(DateTime, default=datetime.utcnow)

