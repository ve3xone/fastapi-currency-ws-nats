from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.models import Base
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """Ассинхронный БД менаджер."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session = None
    
    async def connect(self):
        """Инциализация подключения к БД."""
        self.engine = create_async_engine(
            self.settings.database_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
        
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        # Создаем таблицы
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Успешно подключились к БД и таблицы созданы")
    
    async def disconnect(self):
        """Закрытие соединения к БД."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Отключились от БД")
    
    def get_session(self) -> sessionmaker:
        """Get async session factory."""
        return self.async_session


# Global database instance
db = Database()


async def get_async_session() -> AsyncSession:
    """Dependency for getting async session."""
    if db.async_session is None:
        raise RuntimeError("БД не проинцилизирована")
    
    async with db.async_session() as session:
        yield session
