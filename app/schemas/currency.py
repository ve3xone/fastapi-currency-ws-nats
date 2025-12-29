from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CurrencyBase(BaseModel):
    code: str
    name: str
    rate: float
    type: str = "fiat"  # 'fiat' or 'crypto'

class CurrencyCreate(CurrencyBase):
    pass

class CurrencyUpdate(BaseModel):
    rate: float
    name: Optional[str] = None

class CurrencyResponse(CurrencyBase):
    id: int
    previous_rate: Optional[float] = None
    updated_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class CurrencyListResponse(BaseModel):
    total: int
    currencies: list[CurrencyResponse]

class PriceChangeEvent(BaseModel):
    type: str
    currency: CurrencyResponse
    change_percent: Optional[float] = None

class BackgroundTaskStatus(BaseModel):
    """Status of background task."""
    status: str  # "running", "success", "failed", "idle"
    message: str
    updated_at: datetime
    currencies_count: int = 0