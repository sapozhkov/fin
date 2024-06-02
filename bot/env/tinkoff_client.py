from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Tuple

from tinkoff.invest import CandleInterval, Quotation, MoneyValue, OrderType, PostOrderResponse, GetCandlesResponse, \
    OrderState

from bot.db import TickerCache
from bot.dto import InstrumentDTO
from bot.env import AbstractTimeHelper, AbstractLoggerHelper
from app import q2f


class AbstractProxyClient(ABC):
    interval_duration_minutes = {
        CandleInterval.CANDLE_INTERVAL_1_MIN: 1,
        CandleInterval.CANDLE_INTERVAL_5_MIN: 5,
        CandleInterval.CANDLE_INTERVAL_15_MIN: 15,
        CandleInterval.CANDLE_INTERVAL_30_MIN: 30,
        CandleInterval.CANDLE_INTERVAL_HOUR: 60,
        CandleInterval.CANDLE_INTERVAL_4_HOUR: 240,
        CandleInterval.CANDLE_INTERVAL_DAY: 1440,
    }

    def __init__(
            self,
            token,
            ticker,
            time: AbstractTimeHelper,
            logger: AbstractLoggerHelper
    ):
        # авто расчет надо переделать если будут инструменты с шагом не кратным десятой доле #26
        self.token = token
        self.time: AbstractTimeHelper = time
        self.logger = logger
        self.ticker_cache = TickerCache(ticker)
        self.instrument: InstrumentDTO = self.get_instrument()

    @abstractmethod
    def can_trade(self):
        pass

    def q2f(self, quotation: Quotation | MoneyValue, digits=None):
        if digits is None:
            digits = self.instrument.round_signs
        return q2f(quotation, digits)

    def round(self, price):
        return round(round(price / self.instrument.min_increment) * self.instrument.min_increment,
                     self.instrument.round_signs)

    @abstractmethod
    def place_order(self, lots: int, direction, price: float | None,
                    order_type=OrderType.ORDER_TYPE_MARKET) -> PostOrderResponse | None:
        pass

    # Базовая функция для загрузки данных последних свечей
    def fetch_candles(self, interval=CandleInterval.CANDLE_INTERVAL_5_MIN, candles_count=5):
        to_date = self.time.now()
        minutes_per_candle = self.interval_duration_minutes[interval]
        from_date = to_date - timedelta(minutes=minutes_per_candle * candles_count)
        return self.get_candles(from_date, to_date, interval)

    @abstractmethod
    def get_candles(self, from_date, to_date, interval) -> GetCandlesResponse:
        pass

    @abstractmethod
    def get_day_candles(self, from_date, to_date) -> GetCandlesResponse:
        pass

    @abstractmethod
    def order_is_executed(self, order: PostOrderResponse) -> Tuple[bool, OrderState | None]:
        pass

    @abstractmethod
    def get_instruments_count(self):
        pass

    @abstractmethod
    def cancel_order(self, order) -> bool:
        pass

    @abstractmethod
    def get_active_orders(self):
        pass

    @abstractmethod
    def get_current_price(self):
        pass

    def get_instrument(self) -> InstrumentDTO:
        return self.ticker_cache.get_instrument()

    def get_figi(self) -> str:
        return self.get_instrument().figi
