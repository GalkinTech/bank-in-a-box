"""
Конфигурация банка OneBank
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class BankConfig(BaseSettings):
    """Настройки банка"""
    
    # === ИДЕНТИФИКАЦИЯ БАНКА ===
    BANK_CODE: str = "onebank"
    BANK_NAME: str = "OneBank"
    BANK_DESCRIPTION: str = "Единый мультибанковский финансовый аналитический центр"
    
    # === DATABASE ===
    DATABASE_URL: str = "postgresql://bankuser:bankpass@db:5432/mybank_db"
    
    # === SECURITY ===
    SECRET_KEY: str = "qovalenko-123-onebank"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # === API ===
    API_VERSION: str = "2.1"
    API_BASE_PATH: str = ""
    
    # === REGISTRY (для федеративной архитектуры) ===
    REGISTRY_URL: str = "http://directory.hackapi.tech"
    PUBLIC_URL: str = "https://onebank.ru"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Игнорировать дополнительные поля из .env
    )


# Singleton instance
config = BankConfig()

