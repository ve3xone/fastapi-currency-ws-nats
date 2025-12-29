from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Конфиг приложения."""
    
    # БД
    database_url: str = "sqlite+aiosqlite:///./data/currency_monitor.db"
    
    # NATS
    nats_url: str = "nats://localhost:4222"
    nats_subject: str = "currency.updates"
    
    # API настройки
    background_task_interval: int = 60  # сек
    api_timeout: int = 10  # сек
    
    # Внешний API который парсим (Fiat)
    exchangerate_api_url: str = "https://api.exchangerate-api.com/v4/latest"
    base_currency: str = "USD"

    # Внешний API который парсим (Fiat - CBRF)
    cbr_api_url: str = "https://www.cbr-xml-daily.ru/daily_json.js"

    # Внешний API который парсим (Crypto - Binance)
    binance_api_url: str = "https://api.binance.com"
    
    # Уровень логирования
    log_level: str = "INFO"
    
    # Режим работы фоновой задачи
    # "all" - обновляет все валюты из БД + добавляет стоковые
    # "default" - только стоковые валюты
    update_mode: str = "all"
    
    # Стоковые валюты для обновления (по умолчанию)
    default_fiat_currencies: List[str] = ["EUR", "JPY", "RUB", "CNY", "KZT"]
    default_crypto_currencies: List[str] = ["BTC", "ETH", "SOL", "XRP", "DOGE", "TON"]
    default_cbr_currencies: List[str] = ["USD", "EUR", "CNY", "BYN", "KZT"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()