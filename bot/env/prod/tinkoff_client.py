from datetime import datetime, timezone
from typing import Tuple

from tinkoff.invest import Client, RequestError, OrderType, PostOrderResponse, OrderDirection, GetCandlesResponse, \
    CandleInterval, OrderState, OrderExecutionReportStatus, GetTradingStatusResponse

from bot.env import AbstractProxyClient
from app.helper import f2q
from app.lib import TinkoffApi


class TinkoffProxyClient(AbstractProxyClient):
    def __init__(self, ticker, time, logger, account_id: str):
        super().__init__(ticker, time, logger)
        self.account_id: str = account_id
        self.status = self._get_trade_status()

    def get_current_price(self) -> float | None:
        """
        Получает текущую цену инструмента
        :return: Текущая цена инструмента или None, если цена не может быть получена.
        """
        price = TinkoffApi.get_last_price(self.get_figi())
        if price is None:
            self.logger.error(f"Ошибка при запросе текущей цены для FIGI {self.get_figi()}")
        return price

    def _get_trade_status(self) -> GetTradingStatusResponse | None:
        try:
            with Client(self.token) as client:
                trading_status = client.market_data.get_trading_status(figi=self.get_figi())
        except RequestError as e:
            self.logger.log(f"Ошибка при запросе статуса торговли: {e}")
            return None
        return trading_status

    def update_cached_status(self):
        new_status = self._get_trade_status()
        # это защита от случаев, когда сам метод сбоит, а остальное работает
        if new_status is not None:
            self.status = new_status
        return self.status

    def can_trade(self):
        return self.status and self.status.limit_order_available_flag

    def can_limit_order(self):
        return self.status and self.status.limit_order_available_flag

    def can_market_order(self):
        return self.status and self.status.market_order_available_flag

    def can_bestprice_order(self):
        return self.status and self.status.bestprice_order_available_flag

    def place_order(self, lots: int, direction, price: float | None, order_type: int) -> PostOrderResponse | None:
        try:
            price_quotation = f2q(price) if price else None
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
            if order_type == OrderType.ORDER_TYPE_MARKET:
                order_type_text = 'market'
            elif order_type == OrderType.ORDER_TYPE_BESTPRICE:
                order_type_text = 'bestprice'
            else:
                order_type_text = 'limit'

            self.logger.error(f"Не выставлена заявка: "
                              f"order_type: {order_type_text}, "
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
