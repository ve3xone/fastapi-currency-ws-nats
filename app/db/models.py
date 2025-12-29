from sqlalchemy import Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Currency(Base):
    """Currency exchange rate model"""
    
    __tablename__ = "currencies"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)  # "EUR", "BTC"
    name = Column(String(100), nullable=False)
    rate = Column(Float, nullable=False)
    previous_rate = Column(Float, nullable=True)
    type = Column(String(10), default="fiat")  # 'fiat' or 'crypto'
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Currency {self.code} ({self.type}): {self.rate}>"
