import nats
import json
import logging
from app.config import get_settings
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class NATSClient:
    """NATS Брокер клиент сообщений."""
    
    def __init__(self):
        self.settings = get_settings()
        self.nc: nats.NATS
        self.subscriptions = {}
    
    async def connect(self):
        """Подключение к серверу NATS."""
        try:
            self.nc = await nats.connect(self.settings.nats_url)
            logger.info(f"Подключились к NATS серверу: {self.settings.nats_url}")
        except Exception as e:
            logger.error(f"Ошибка подключения к NATS серверу: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from NATS server."""
        if self.nc:
            await self.nc.drain()
            logger.info("Отключились от NATS сервера")
    
    async def publish(self, subject: str, message: dict):
        """Опубликовать сообщение в определнный subject"""
        if not self.nc:
            logger.warning("NATS клиент не подключен к серверу, пропускаем публикацию")
            return
        
        try:
            payload = json.dumps(message, default=str).encode("utf-8")
            await self.nc.publish(subject, payload)
        except Exception as e:
            logger.error(f"Ошибка публикации сообщений в NATS: {subject}: {e}")


# Global NATS client
nats_client = NATSClient()
