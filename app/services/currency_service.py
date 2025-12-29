from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.models import Currency
from app.schemas.currency import CurrencyCreate, CurrencyUpdate, CurrencyResponse
import logging

logger = logging.getLogger(__name__)


class CurrencyService:
    """Основная БД логика для курсов валют."""
    
    @staticmethod
    async def get_all_currencies(session: AsyncSession) -> list[Currency]:
        """Получить все валюты из БД."""
        result = await session.execute(select(Currency))
        return result.scalars().all()

    @staticmethod
    async def get_currency_by_id(session: AsyncSession, currency_id: int) -> Currency | None:
        """Получить валюту по числовому ID."""
        result = await session.execute(
            select(Currency).where(Currency.id == currency_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_currency_by_code(session: AsyncSession, code: str) -> Currency | None:
        """Получить валюту по code."""
        result = await session.execute(
            select(Currency).where(Currency.code == code)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_currency(
        session: AsyncSession,
        currency: CurrencyCreate
    ) -> Currency:
        """Создать валюту."""
        db_currency = Currency(
            code=currency.code,
            name=currency.name,
            rate=currency.rate
        )
        session.add(db_currency)
        await session.commit()
        await session.refresh(db_currency)
        logger.info(f"Валюта создана: {currency.code}")
        return db_currency
    
    @staticmethod
    async def update_currency(
        session: AsyncSession,
        currency_id: int,
        currency_update: CurrencyUpdate
    ) -> Currency | None:
        """Обновить валюту."""
        result = await session.execute(
            select(Currency).where(Currency.id == currency_id)
        )
        db_currency = result.scalar_one_or_none()
        
        if not db_currency:
            return None

        db_currency.previous_rate = db_currency.rate

        if currency_update.rate is not None:
            db_currency.rate = currency_update.rate
        if currency_update.name is not None:
            db_currency.name = currency_update.name
        
        await session.commit()
        await session.refresh(db_currency)
        logger.info(f"Валюта обновлена: {db_currency.code}")
        return db_currency
    
    @staticmethod
    async def update_or_create_currency(
        session: AsyncSession,
        code: str,
        name: str,
        rate: float,
        type: str = "fiat"
    ) -> tuple[Currency, bool]:
        existing = await CurrencyService.get_currency_by_code(session, code)
        
        if existing:
            # Обновляем
            update_data = CurrencyUpdate(rate=rate, name=name)
            await CurrencyService.update_currency(session, existing.id, update_data)
            return existing, False
        else:
            # Создаем с типом
            db_currency = Currency(
                code=code, 
                name=name, 
                rate=rate, 
                type=type
            )
            session.add(db_currency)
            await session.commit()
            await session.refresh(db_currency)
            return db_currency, True

    @staticmethod
    async def delete_currency(
        session: AsyncSession,
        currency_id: int
    ) -> bool:
        """Удалить валюту."""
        result = await session.execute(
            select(Currency).where(Currency.id == currency_id)
        )
        db_currency = result.scalar_one_or_none()
        
        if not db_currency:
            return False
        
        await session.delete(db_currency)
        await session.commit()
        logger.info(f"Валюта удалена: {db_currency.code}")
        return True
    
    @staticmethod
    async def delete_all_currencies(session: AsyncSession) -> int:
        """Удалить все валюты."""
        result = await session.execute(delete(Currency))
        await session.commit()
        count = result.rowcount
        logger.info(f"Валют удаленно: {count}")
        return count
