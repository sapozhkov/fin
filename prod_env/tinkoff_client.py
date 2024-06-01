from abc import abstractmethod, ABC
from datetime import datetime, timezone, timedelta
from typing import Tuple

from tinkoff.invest import Client, RequestError, Quotation, OrderType, GetCandlesResponse, OrderExecutionReportStatus, \
    CandleInterval, PostOrderResponse, MoneyValue, OrderState, OrderDirection

from common.lib import TinkoffApi
from bot.dto import InstrumentDTO
from bot.db import TickerCache
from bot.env import AbstractLoggerHelper
from prod_env.time_helper import AbstractTimeHelper


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

    def float_to_quotation(self, price) -> Quotation:
        return Quotation(units=int(price), nano=int((self.round(price - int(price))) * 1e9))

    def quotation_to_float(self, quotation: Quotation | MoneyValue, digits=None):
        if digits is None:
            digits = self.instrument.round_signs
        return round(quotation.units + quotation.nano * 1e-9, digits)

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


class TinkoffProxyClient(AbstractProxyClient):
    def __init__(self, token, ticker, time, logger):
        super().__init__(token, ticker, time, logger)
        self.account_id = self.get_account_id()

    def get_account_id(self):
        with Client(self.token) as client:
            accounts = client.users.get_accounts().accounts
            if accounts:
                first_account_id = accounts[0].id
                return first_account_id
            else:
                raise Exception("No accounts found")

    def get_current_price(self) -> float | None:
        """
        Получает текущую цену инструмента
        :return: Текущая цена инструмента или None, если цена не может быть получена.
        """
        price = TinkoffApi.get_last_price(self.get_figi())
        if price is None:
            self.logger.error(f"Ошибка при запросе текущей цены для FIGI {self.get_figi()}")
        return price

    def can_trade(self):
        try:
            with Client(self.token) as client:
                trading_status = client.market_data.get_trading_status(figi=self.get_figi())
                if not trading_status.limit_order_available_flag:
                    self.logger.log('Торговля закрыта (ответ из API)')
                    return False
        except RequestError as e:
            self.logger.log(f"Ошибка при запросе статуса торговли: {e}")
            return False
        return True

    def place_order(self, lots: int, direction, price: float | None,
                    order_type=OrderType.ORDER_TYPE_MARKET) -> PostOrderResponse | None:
        try:
            price_quotation = self.float_to_quotation(price=price) if price else None
            with Client(self.token) as client:
                return client.orders.post_order(
                    order_id=str(datetime.now(timezone.utc)),
                    figi=self.get_figi(),
                    quantity=lots,
                    direction=direction,
                    account_id=self.account_id,
                    order_type=order_type,
                    price=price_quotation
                )
        except RequestError as e:
            self.logger.error(f"Не выставлена заявка: "
                              f"order_type: {'market' if order_type == OrderType.ORDER_TYPE_MARKET else 'limit'}, "
                              f"direction: {'buy' if direction == OrderDirection.ORDER_DIRECTION_BUY else 'sell'}, "
                              f"lots: {lots}, price: {self.round(price) if price is not None else 'None'}, Error: {e}")
            return None

    def get_candles(self, from_date, to_date, interval) -> GetCandlesResponse:
        with Client(self.token) as client:
            try:
                candles = client.market_data.get_candles(
                    figi=self.get_figi(),
                    from_=from_date,
                    to=to_date,
                    interval=interval
                )
                return candles
            except RequestError as e:
                self.logger.error(f"Ошибка при запросе свечей: {e}")
                return GetCandlesResponse([])

    def get_day_candles(self, from_date, to_date) -> GetCandlesResponse:
        return self.get_candles(from_date, to_date, interval=CandleInterval.CANDLE_INTERVAL_DAY)

    def order_is_executed(self, order: PostOrderResponse) -> Tuple[bool, OrderState | None]:
        with Client(self.token) as client:
            try:
                order_state = client.orders.get_order_state(account_id=self.account_id, order_id=order.order_id)
            except RequestError as e:
                self.logger.error(f"Ошибка при запросе статуса заявки: {e}")
                return False, None
            return (
                order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
                order_state
            )

    def get_instruments_count(self):
        with Client(self.token) as client:
            try:
                portfolio = client.operations.get_portfolio(account_id=self.account_id)
            except RequestError as e:
                self.logger.error(f"Ошибка при запросе портфеля: {e}")
                return 0
            for position in portfolio.positions:
                if position.figi == self.get_figi():
                    return position.quantity.units - position.blocked_lots.units
            return 0

    def cancel_order(self, order) -> bool:
        if not order:
            return False
        with Client(self.token) as client:
            try:
                client.orders.cancel_order(account_id=self.account_id, order_id=order.order_id)
                return True
            except RequestError as e:
                self.logger.error(f"Ошибка при закрытии заявки на покупку: {e}")
        return False

    def get_active_orders(self):
        with Client(self.token) as client:
            try:
                all_orders = client.orders.get_orders(account_id=self.account_id)
                active_orders = [order for order in all_orders.orders if order.execution_report_status
                                 != OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL]
                return active_orders
            except Exception as e:
                self.logger.error(f"Ошибка при получении активных заявок: {e}")
                return None
