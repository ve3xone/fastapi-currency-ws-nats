from fastapi import WebSocket
import json
import logging
from typing import Set

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Управление Веб-сокетом."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Принимаем и регистрируем соединение веб-сокета."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Веб-сокет подключен. Активные соедниения: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Отключение соединения веб-сокета."""
        self.active_connections.discard(websocket)
        logger.info(f"Веб-сокет отключен. Активные соедниения: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            logger.debug("Нет активных соединений broadcast")
            return
        
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения на веб-сокет: {e}")
                disconnected.append(websocket)
        
        # Убераем соедниение
        for ws in disconnected:
            await self.disconnect(ws)
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Отправки специфичного сообщения."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Ошибка отправки специфичного сообщения в веб-сокет: {e}")
            await self.disconnect(websocket)
    
    def get_active_count(self) -> int:
        """Получить активные соединения."""
        return len(self.active_connections)


# Global WebSocket manager
ws_manager = WebSocketManager()
