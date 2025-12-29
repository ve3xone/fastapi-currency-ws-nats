from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_async_session
from app.services.currency_service import CurrencyService
from app.tasks.background import background_manager
from app.schemas.currency import (
    CurrencyCreate, CurrencyResponse, CurrencyUpdate,
    CurrencyListResponse, BackgroundTaskStatus
)
from app.ws.manager import ws_manager
from datetime import datetime
from app.config import get_settings
import httpx

router = APIRouter(prefix="/api/v1", tags=["currencies"])
settings = get_settings()


@router.get(
    "/provider/assets",
    summary="Получение валют с сервисов для парсинга",
)
async def get_available_assets_to_add():
    """
    Возвращает список всех доступных для отслеживания активов (Фиат + Крипта).
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        available_assets = {
            "fiat": [],
            "crypto": [],
            "cbr": []
        }
        
        # Получаем Фиат (Supported Codes)
        try:
            url = f"{settings.exchangerate_api_url}/{settings.base_currency}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                available_assets["fiat"] = [
                    {"code": k, "name": f"Fiat {k}"} for k in data.get("rates", {}).keys()
                ]
        except Exception as e:
            available_assets["fiat_error"] = str(e)

        # Получаем Крипту с Binance (Exchange Info)
        try:
            url = f"{settings.binance_api_url}/api/v3/exchangeInfo"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                symbols = data.get("symbols", [])
                
                crypto_list = []
                for s in symbols:
                    if s["status"] == "TRADING" and s["quoteAsset"] == "USDT":
                        crypto_list.append({
                            "code": s["baseAsset"], # BTC
                            "symbol": s["symbol"],  # BTCUSDT
                            "name": f"{s['baseAsset']}/USDT"
                        })
                # сортируем
                available_assets["crypto"] = sorted(crypto_list, key=lambda x: x["code"])
        except Exception as e:
            available_assets["crypto_error"] = str(e)

        # Получаем список ЦБ
        try:
            url = settings.cbr_api_url
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                valute = data.get("Valute", {})
                available_assets["cbr"] = [
                    {
                        "code": f"{v['CharCode']}RUB",
                        "name": f"CBR {v['Name']} (RUB)",
                        "nominal": v['Nominal']
                    }
                    for v in valute.values()
                ]
        except Exception as e:
            available_assets["cbr_error"] = str(e)
            
        return {
            "total_fiat": len(available_assets["fiat"]),
            "total_crypto": len(available_assets["crypto"]),
            "total_cbr": len(available_assets["cbr"]),
            "assets": available_assets
        }


@router.get(
    "/currencies", 
    response_model=CurrencyListResponse,
    summary="Получить все напарсенные валюты",
)
async def get_currencies(
    session: AsyncSession = Depends(get_async_session)
):
    """Получение всех созданных валют."""
    currencies = await CurrencyService.get_all_currencies(session)
    return CurrencyListResponse(
        total=len(currencies),
        currencies=[CurrencyResponse.from_orm(c) for c in currencies]
    )


@router.get(
    "/currencies/{identifier}", 
    response_model=CurrencyResponse,
    summary="Получить выбранную валюту",
)
async def get_currency(
    identifier: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Получить валюту по ID (число) или по коду (строка, например 'BTC', 'USDRUB').
    """
    currency = None

    if identifier.isdigit():
        currency = await CurrencyService.get_currency_by_id(session, int(identifier))

    if not currency:
        currency = await CurrencyService.get_currency_by_code(session, identifier.upper())

    if not currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Currency with identifier '{identifier}' not found",
        )

    return CurrencyResponse.from_orm(currency)


@router.post(
    "/currencies", 
    response_model=CurrencyResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Создать валюту",
)
async def create_currency(
    currency: CurrencyCreate,
    session: AsyncSession = Depends(get_async_session)
):
    db_currency = await CurrencyService.create_currency(session, currency)
    return CurrencyResponse.from_orm(db_currency)


@router.patch(
    "/currencies/{identifier}", 
    response_model=CurrencyResponse,
    summary="Обновление валюты по ID или коду",
)
async def patch_currency(
    identifier: str,
    currency_update: CurrencyUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Примеры:
      PATCH /api/v1/currencies/1
      PATCH /api/v1/currencies/BTC
    """
    currency = None
    if identifier.isdigit():
        currency = await CurrencyService.get_currency_by_id(session, int(identifier))
    if not currency:
        currency = await CurrencyService.get_currency_by_code(session, identifier.upper())

    if not currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency not found",
        )

    updated = await CurrencyService.update_currency(session, currency.id, currency_update)
    return CurrencyResponse.from_orm(updated)


@router.delete(
    "/currencies/{identifier}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить валюту"
)
async def delete_currency(
    identifier: str,
    session: AsyncSession = Depends(get_async_session)
):
    currency = None
    if identifier.isdigit():
        currency = await CurrencyService.get_currency_by_id(session, int(identifier))
    
    if not currency:
        currency = await CurrencyService.get_currency_by_code(session, identifier.upper())
        
    if not currency:
        raise HTTPException(status_code=404, detail="Not found")

    await CurrencyService.delete_currency(session, currency.id)


@router.post(
    "/tasks/run", 
    response_model=BackgroundTaskStatus,
    summary="Запустить фоновую задачу"
)
async def run_background_task():
    """Manually trigger background task."""
    await background_manager.run_once()
    status_data = background_manager.get_status()
    
    return BackgroundTaskStatus(
        status=status_data["status"],
        message=status_data["message"],
        updated_at=status_data["updated_at"],
        currencies_count=status_data["currencies_count"]
    )


@router.get(
    "/tasks/status", 
    response_model=BackgroundTaskStatus,
    summary="Получить статус об фоновой задаче"
)
async def get_task_status():
    """Get background task status."""
    status_data = background_manager.get_status()
    
    return BackgroundTaskStatus(
        status=status_data["status"],
        message=status_data["message"],
        updated_at=status_data["updated_at"],
        currencies_count=status_data["currencies_count"]
    )


@router.get(
    "/health",
    summary="Узнать работоспособность сервиса"
)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "active_ws_connections": ws_manager.get_active_count()
    }
