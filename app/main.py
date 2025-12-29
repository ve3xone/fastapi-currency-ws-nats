import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.db.database import db
from app.nats.client import nats_client
from app.ws.manager import ws_manager
from app.tasks.background import background_manager
from app.api.routes import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Запуск
    logger.info("Запуск приложения...")
    settings = get_settings()
    
    await db.connect()
    
    try:
        await nats_client.connect()
    except Exception as e:
        logger.error(f"Не удалось подключиться к NATS: {e}")
    
    await background_manager.start()
    logger.info("Успешно приложение запущенно")
    
    yield
    
    # ВЫХОД ЙОУ
    logger.info("Выход из приложения...")
    await background_manager.stop()
    await nats_client.disconnect()
    await db.disconnect()
    
    logger.info("Успешно приложение завершенно")


app = FastAPI(
    title="API монитора валют",
    description="""
Мониторинг обменных курсов валют в реальном времени с использованием WebSocket и NATS

Парсинг выполняю с ЦБ РФ, Binance, exchangerate-api.com
    """,
    version="1.0.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.websocket("/ws/currencies")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time currency updates."""
    await ws_manager.connect(websocket)
    
    try:
        # Отправка сообщения
        await ws_manager.send_personal(
            websocket,
            {"type": "connected", "message": "Connected to currency updates"}
        )
        
        # Пока сооединение активно все идет
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from WebSocket client: {data}")
            
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
        logger.info("Веб-сокет отключен.")
    except Exception as e:
        logger.error(f"Ошибка веб-сокет: {e}")
        await ws_manager.disconnect(websocket)


@app.get("/", summary="Рут хд")
async def root():
    """Рут"""
    return {
        "message": "Всем ку это монитор валют крч",
        "docs": "/docs",
        "api_v1": "/api/v1"
    }


@app.on_event("startup")
async def startup_event():
    """Log startup."""
    logger.info("Startup event fired")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown."""
    logger.info("Shutdown event fired")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
