import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Tuple
from app.config import get_settings
from app.db.database import db
from app.services.currency_service import CurrencyService
from app.nats.client import nats_client
from app.ws.manager import ws_manager
from app.schemas.currency import PriceChangeEvent, CurrencyResponse, CurrencyUpdate

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    def __init__(self):
        self.settings = get_settings()
        self.is_running = False
        self.task = None
        self.last_status = {
            "status": "idle",
            "message": "No tasks run yet",
            "updated_at": datetime.utcnow(),
            "currencies_count": 0
        }
    
    async def fetch_all_fiat_rates(self, client) -> List[Tuple[str, str, str, float]]:
        """Получаем ВСЕ фиатные курсы."""
        try:
            url = f"{self.settings.exchangerate_api_url}/{self.settings.base_currency}"
            response = await client.get(url)
            if response.status_code != 200:
                logger.error(f"Fiat API error: {response.status_code}")
                return []
                
            data = response.json()
            rates = data.get("rates", {})
            
            results = []
            for code, rate in rates.items():
                if code != self.settings.base_currency:
                    results.append(("fiat", f'{self.settings.base_currency}{code}', 
                                  f"Fiat {self.settings.base_currency}/{code}", rate))
            return results
        except Exception as e:
            logger.error(f"Error fetching all fiat: {e}")
            return []

    async def fetch_all_crypto_rates(self, client) -> List[Tuple[str, str, str, float]]:
        """Получаем ВСЕ крипто курсы с Binance (USDT pairs)."""
        try:
            url = f"{self.settings.binance_api_url}/api/v3/ticker/price"
            response = await client.get(url)
            if response.status_code != 200:
                logger.error(f"Binance API error: {response.status_code}")
                return []
            
            data = response.json()
            
            results = []
            for item in data:
                symbol = item["symbol"]
                if symbol.endswith("USDT"):
                    # Извлекаем код криптовалюты (убираем USDT)
                    code = symbol.replace("USDT", "")
                    price = float(item["price"])
                    results.append(("crypto", code, f"Crypto {code}/USDT", price))
                    
            return results
        except Exception as e:
            logger.error(f"Error fetching all crypto: {e}")
            return []

    async def fetch_all_cbr_rates(self, client) -> List[Tuple[str, str, str, float]]:
        """Получаем ВСЕ курсы ЦБ РФ."""
        try:
            response = await client.get(self.settings.cbr_api_url)
            if response.status_code != 200:
                logger.error(f"CBR API error: {response.status_code}")
                return []
            
            data = response.json()
            valute = data.get("Valute", {})
            
            results = []
            for code, item in valute.items():
                rate = item["Value"] / item["Nominal"]
                results.append(("cbr", f"{code}RUB", f"CBR {code}/RUB", rate))
            
            return results
        except Exception as e:
            logger.error(f"Error fetching all CBR: {e}")
            return []

    async def fetch_default_fiat_rates(self, client) -> List[Tuple[str, str, str, float]]:
        """Получаем только стоковые фиатные курсы."""
        try:
            url = f"{self.settings.exchangerate_api_url}/{self.settings.base_currency}"
            response = await client.get(url)
            if response.status_code != 200:
                logger.error(f"Fiat API error: {response.status_code}")
                return []
                
            data = response.json()
            rates = data.get("rates", {})
            
            results = []
            for code in self.settings.default_fiat_currencies:
                if code in rates and code != self.settings.base_currency:
                    results.append(("fiat", f'{self.settings.base_currency}{code}', 
                                  f"Fiat {self.settings.base_currency}/{code}", rates[code]))
            return results
        except Exception as e:
            logger.error(f"Error fetching default fiat: {e}")
            return []

    async def fetch_default_crypto_rates(self, client) -> List[Tuple[str, str, str, float]]:
        """Получаем только стоковые крипто курсы."""
        try:
            url = f"{self.settings.binance_api_url}/api/v3/ticker/price"
            response = await client.get(url)
            if response.status_code != 200:
                logger.error(f"Binance API error: {response.status_code}")
                return []
            
            data = response.json()
            
            results = []
            target_symbols = {f"{t}USDT": t for t in self.settings.default_crypto_currencies}
            
            for item in data:
                symbol = item["symbol"]
                if symbol in target_symbols:
                    code = target_symbols[symbol]
                    price = float(item["price"])
                    results.append(("crypto", code, f"Crypto {code}/USDT", price))
                    
            return results
        except Exception as e:
            logger.error(f"Error fetching default crypto: {e}")
            return []

    async def fetch_default_cbr_rates(self, client) -> List[Tuple[str, str, str, float]]:
        """Получаем только стоковые курсы ЦБ РФ."""
        try:
            response = await client.get(self.settings.cbr_api_url)
            if response.status_code != 200:
                logger.error(f"CBR API error: {response.status_code}")
                return []
            
            data = response.json()
            valute = data.get("Valute", {})
            
            results = []
            for code in self.settings.default_cbr_currencies:
                if code in valute:
                    item = valute[code]
                    rate = item["Value"] / item["Nominal"]
                    results.append(("cbr", f"{code}RUB", f"CBR {code}/RUB", rate))
            
            return results
        except Exception as e:
            logger.error(f"Error fetching default CBR: {e}")
            return []

    async def update_all_mode(self, session) -> int:
        """Режим 'all': обновляем все валюты из БД + добавляем стоковые."""
        try:
            updated_count = 0
            
            # 1. Получаем все доступные курсы
            async with httpx.AsyncClient(timeout=self.settings.api_timeout) as client:
                all_fiat_data, all_crypto_data, all_cbr_data = await asyncio.gather(
                    self.fetch_all_fiat_rates(client),
                    self.fetch_all_crypto_rates(client),
                    self.fetch_all_cbr_rates(client)
                )
            
            # Создаем словарь всех доступных курсов
            all_available_rates: Dict[str, Tuple[str, float, str]] = {}
            for c_type, code, name, rate in all_fiat_data + all_crypto_data + all_cbr_data:
                all_available_rates[code] = (name, rate, c_type)
            
            # 2. Получаем все валюты из БД
            db_currencies = await CurrencyService.get_all_currencies(session)
            db_currency_codes = {c.code for c in db_currencies}
            
            # 3. Обновляем существующие валюты из БД
            for currency in db_currencies:
                if currency.code in all_available_rates:
                    name, rate, c_type = all_available_rates[currency.code]
                    
                    update_data = CurrencyUpdate(rate=rate, name=name)
                    updated_currency = await CurrencyService.update_currency(
                        session, currency.id, update_data
                    )
                    
                    if updated_currency:
                        # Отправляем событие
                        await self._send_currency_event(updated_currency, "updated")
                        updated_count += 1
                        logger.debug(f"Обновлена валюта из БД: {currency.code} -> {rate}")
                else:
                    logger.warning(f"Курс для валюты из БД {currency.code} не найден в API")
            
            # 4. Добавляем стоковые валюты (если их нет в БД)
            async with httpx.AsyncClient(timeout=self.settings.api_timeout) as client:
                default_fiat_data, default_crypto_data, default_cbr_data = await asyncio.gather(
                    self.fetch_default_fiat_rates(client),
                    self.fetch_default_crypto_rates(client),
                    self.fetch_default_cbr_rates(client)
                )
            
            # Добавляем только те стоковые, которых нет в БД
            for c_type, code, name, rate in default_fiat_data + default_crypto_data + default_cbr_data:
                if code not in db_currency_codes:
                    # Добавляем новую валюту
                    currency, is_created = await CurrencyService.update_or_create_currency(
                        session, code=code, name=name, rate=rate, type=c_type
                    )
                    
                    if is_created:
                        await self._send_currency_event(currency, "created")
                        updated_count += 1
                        logger.debug(f"Добавлена стоковая валюта: {code} -> {rate}")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Ошибка в режиме all: {e}")
            return 0

    async def update_default_mode(self, session) -> int:
        """Режим 'default': обновляем только стоковые валюты."""
        try:
            updated_count = 0
            
            # Получаем только стоковые курсы
            async with httpx.AsyncClient(timeout=self.settings.api_timeout) as client:
                fiat_data, crypto_data, cbr_data = await asyncio.gather(
                    self.fetch_default_fiat_rates(client),
                    self.fetch_default_crypto_rates(client),
                    self.fetch_default_cbr_rates(client)
                )
            
            # Обрабатываем стоковые валюты
            for c_type, code, name, rate in fiat_data + crypto_data + cbr_data:
                currency, is_created = await CurrencyService.update_or_create_currency(
                    session, code=code, name=name, rate=rate, type=c_type
                )
                
                event_type = "created" if is_created else "updated"
                await self._send_currency_event(currency, event_type)
                updated_count += 1
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Ошибка в режиме default: {e}")
            return 0

    async def _send_currency_event(self, currency, event_type: str):
        """Отправляет событие о валюте через NATS и WebSocket."""
        try:
            change_percent = None
            if currency.previous_rate and currency.previous_rate != 0:
                change_percent = ((currency.rate - currency.previous_rate) / 
                                currency.previous_rate * 100)
            
            currency_resp = CurrencyResponse.from_orm(currency)
            
            event = PriceChangeEvent(
                type=event_type,
                currency=currency_resp,
                change_percent=change_percent
            )
            
            dumped_event = event.model_dump(mode="json")
            await nats_client.publish(self.settings.nats_subject, dumped_event)
            await ws_manager.broadcast(dumped_event)
            
        except Exception as e:
            logger.error(f"Ошибка при отправке события: {e}")

    async def run_once(self) -> bool:
        """Запуск цикла обновления."""
        try:
            logger.info(f"Запуск обновления курсов (режим: {self.settings.update_mode})...")
            self.last_status["status"] = "running"
            self.last_status["updated_at"] = datetime.utcnow()
            
            async with db.async_session() as session:
                if self.settings.update_mode == "all":
                    updated_count = await self.update_all_mode(session)
                else:  # default mode
                    updated_count = await self.update_default_mode(session)
            
            self.last_status["status"] = "success"
            self.last_status["message"] = f"Обновлено {updated_count} валют (режим: {self.settings.update_mode})"
            self.last_status["currencies_count"] = updated_count
            logger.info(f"Задача завершена: {updated_count} валют обновлено")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка фоновой задачи: {e}")
            self.last_status["status"] = "failed"
            self.last_status["message"] = str(e)
            return False

    async def start(self):
        if self.is_running: return
        self.is_running = True
        self.task = asyncio.create_task(self._loop())

    async def stop(self):
        self.is_running = False
        if self.task: self.task.cancel()

    async def _loop(self):
        while self.is_running:
            await self.run_once()
            await asyncio.sleep(self.settings.background_task_interval)
            
    def get_status(self):
        return self.last_status


background_manager = BackgroundTaskManager()