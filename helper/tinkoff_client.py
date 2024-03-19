from abc import abstractmethod, ABC
from datetime import datetime, timezone, timedelta

from tinkoff.invest import Client, RequestError, Quotation, OrderType, GetCandlesResponse, OrderExecutionReportStatus, \
    CandleInterval, PostOrderResponse, MoneyValue

from helper.time_helper import AbstractTimeHelper


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

    def __init__(self):
        # авто расчет надо переделать если будут инструменты с шагом не кратным десятой доле #26
        self.round_signs = 0
        self.step_size = 0
        self.figi = ''
        self.currency = ''
        self.current_price = 0.0
        self.time: AbstractTimeHelper | None = None

    @abstractmethod
    def can_trade(self):
        pass

    def float_to_quotation(self, price) -> Quotation:
        return Quotation(units=int(price), nano=int((self.round(price - int(price))) * 1e9))

    def quotation_to_float(self, quotation: Quotation | MoneyValue, digits=None):
        if digits is None:
            digits = self.round_signs
        return round(quotation.units + quotation.nano * 1e-9, digits)

    def round(self, price):
        return round(price, self.round_signs)

        # авто расчет надо переделать если будут инструменты с шагом не кратным десятой доле #26
        # вариант:
        # def align_price_to_increment(self, price, min_price_increment):
        #     increments_count = price / min_price_increment
        #     aligned_increments_count = round(increments_count)
        #     aligned_price = aligned_increments_count * min_price_increment
        #     return aligned_price

    @abstractmethod
    def place_order(self, lots: int, operation,
                    price: float | None, order_type=OrderType.ORDER_TYPE_MARKET) -> PostOrderResponse | None:
        pass

    # Базовая функция для загрузки данных последних свечей
    def fetch_candles(self, interval=CandleInterval.CANDLE_INTERVAL_5_MIN, candles_count=5):
        to_date = self.time.now()
        minutes_per_candle = self.interval_duration_minutes[interval]
        from_date = to_date - timedelta(minutes=minutes_per_candle * candles_count)

        candles = self.get_candles(from_date, to_date, interval)

        # обновляем текущую цену инструмента
        if candles.candles:
            last_candle = candles.candles[-1]
            self.current_price = self.quotation_to_float(last_candle.close)

        return candles

    @abstractmethod
    def get_candles(self, from_date, to_date, interval):
        pass

    @abstractmethod
    def order_is_executed(self, order):
        pass

    @abstractmethod
    def get_instruments_count(self):
        pass

    @abstractmethod
    def cancel_order(self, order):
        pass


class TinkoffProxyClient(AbstractProxyClient):
    def __init__(self, token, ticker, time, logger):
        super().__init__()
        self.token = token
        self.ticker = ticker
        self.time = time
        self.logger = logger

        self.set_ticker_params()
        self.account_id = self.get_account_id()

    def get_account_id(self):
        with Client(self.token) as client:
            accounts = client.users.get_accounts().accounts
            if accounts:
                first_account_id = accounts[0].id
                return first_account_id
            else:
                raise Exception("No accounts found")

    def set_ticker_params(self):
        with Client(self.token) as client:
            instruments = client.instruments.shares()
            for instrument in instruments.instruments:
                if instrument.ticker == self.ticker:
                    self.figi = instrument.figi
                    self.currency = instrument.currency
                    min_increment = instrument.min_price_increment.units + instrument.min_price_increment.nano * 1e-9
                    min_increment_str = str(min_increment)
                    decimal_point_index = min_increment_str.find('.')
                    if decimal_point_index == -1:
                        self.round_signs = 0
                    else:
                        self.round_signs = len(min_increment_str) - decimal_point_index - 1
                    self.step_size = self.round(min_increment)
                    return
        raise Exception("No figi found")

    def can_trade(self):
        try:
            with Client(self.token) as client:
                trading_status = client.market_data.get_trading_status(figi=self.figi)
                if not trading_status.limit_order_available_flag:
                    self.logger.log('Торговля закрыта (ответ из API)')
                    return False
        except RequestError as e:
            self.logger.log(f"Ошибка при запросе статуса торговли: {e}")
            return False
        return True

    def place_order(self, lots: int, operation,
                    price: float | None, order_type=OrderType.ORDER_TYPE_MARKET) -> PostOrderResponse | None:
        try:
            price_quotation = self.float_to_quotation(price=price) if price else None
            with Client(self.token) as client:
                return client.orders.post_order(
                    order_id=str(datetime.now(timezone.utc)),
                    figi=self.figi,
                    quantity=lots,
                    direction=operation,
                    account_id=self.account_id,
                    order_type=order_type,
                    price=price_quotation
                )
        except RequestError as e:
            self.logger.error(f"Ошибка при выставлении заявки, operation={operation}"
                              f" price={price}, order_type= {order_type}. ({e})")
            return None

    def get_candles(self, from_date, to_date, interval):
        with Client(self.token) as client:
            try:
                candles = client.market_data.get_candles(
                    figi=self.figi,
                    from_=from_date,
                    to=to_date,
                    interval=interval
                )
                return candles
            except RequestError as e:
                self.logger.error(f"Ошибка при запросе свечей: {e}")
                return GetCandlesResponse([])

    def order_is_executed(self, order):
        with Client(self.token) as client:
            order_state = client.orders.get_order_state(account_id=self.account_id, order_id=order.order_id)
            return (
                order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
                order_state
            )

    def get_instruments_count(self):
        with Client(self.token) as client:
            portfolio = client.operations.get_portfolio(account_id=self.account_id)
            for position in portfolio.positions:
                if position.figi == self.figi:
                    return position.quantity.units
            return 0

    def cancel_order(self, order):
        if not order:
            return False
        with Client(self.token) as client:
            try:
                return client.orders.cancel_order(account_id=self.account_id, order_id=order.order_id)
            except RequestError as e:
                self.logger.error(f"Ошибка при закрытии заявки на покупку: {e}")
        return False
