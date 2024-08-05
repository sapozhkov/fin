from abc import ABC, abstractmethod

from tinkoff.invest import PostOrderResponse, OrderType, OrderDirection, OrderState

from bot import TradingBot
from bot.helper import OrderHelper


class TradeAbstractStrategy(ABC):
    RETRY_DEFAULT = 1
    RETRY_ON_START = 3
    RETRY_SLEEP = 5

    def __init__(
            self,
            bot
    ):
        self.bot = bot

        self.active_buy_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на покупку
        self.active_sell_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на продажу

    @abstractmethod
    def update_orders_status(self):
        pass

    @abstractmethod
    def place_buy_orders(self):
        pass

    @abstractmethod
    def place_sell_orders(self):
        pass

    def place_order(self, order_type: int, direction: int, lots: int, price: float | None = None, retry=RETRY_DEFAULT) \
            -> PostOrderResponse | None:

        order = self.bot.client.place_order(lots, direction, price, order_type)
        if order is None:
            if retry > 0:
                self.bot.logger.error(f"RETRY order. {lots}, {direction}, {price}, {order_type}, "
                                  f"sleep {self.RETRY_SLEEP}, retry num={retry}")
                self.bot.time.sleep(self.RETRY_SLEEP)
                return self.place_order(order_type, direction, lots, price, retry-1)
            else:
                return None

        self.bot.accounting.add_order(order)
        avg_price = self.bot.get_order_avg_price(order)

        if order_type == OrderType.ORDER_TYPE_MARKET:
            self.bot.accounting.add_deal_by_order(order)
            if direction == OrderDirection.ORDER_DIRECTION_BUY:
                prefix = "BUY MARKET executed"
                avg_price = -avg_price
            else:
                prefix = "SELL MARKET executed"

        else:
            if direction == OrderDirection.ORDER_DIRECTION_BUY:
                self.active_buy_orders[order.order_id] = order
                prefix = "Buy order set"
                avg_price = -avg_price
            else:
                self.active_sell_orders[order.order_id] = order
                prefix = "Sell order set"

        self.bot.log(f"{prefix}, {lots} x {avg_price} {self.bot.get_cur_count_for_log()}")

        return order

    def buy(self, lots: int = 1, retry=RETRY_DEFAULT) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_MARKET, OrderDirection.ORDER_DIRECTION_BUY, lots, None, retry)

    def sell(self, lots: int = 1, retry=RETRY_DEFAULT) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_MARKET, OrderDirection.ORDER_DIRECTION_SELL, lots, None, retry)

    def sell_limit(self, price: float, lots: int = 1, retry=RETRY_DEFAULT) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_LIMIT, OrderDirection.ORDER_DIRECTION_SELL, lots, price, retry)

    def buy_limit(self, price: float, lots: int = 1, retry=RETRY_DEFAULT) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_LIMIT, OrderDirection.ORDER_DIRECTION_BUY, lots, price, retry)

    # todo move
    def apply_order_execution(self, order: OrderState):
        lots = OrderHelper.get_lots(order)
        avg_price = self.bot.get_order_avg_price(order)
        type_text = 'BUY' if order.direction == OrderDirection.ORDER_DIRECTION_BUY else 'SELL'
        self.bot.accounting.add_deal_by_order(order)
        self.bot.log(f"{type_text} order executed, {lots} x {avg_price} {self.bot.get_cur_count_for_log()}")

    # todo move
    def get_existing_buy_order_prices(self) -> list[float]:
        return [self.bot.get_order_avg_price(order)
                for order_id, order in self.active_buy_orders.items()]

    # todo move
    def get_existing_sell_order_prices(self) -> list[float]:
        return [self.bot.get_order_avg_price(order)
                for order_id, order in self.active_sell_orders.items()]

    # todo move
    def cancel_active_orders(self):
        self.cancel_active_buy_orders()
        self.cancel_active_sell_orders()

    # todo move
    def cancel_active_buy_orders(self):
        for order_id, order in self.active_buy_orders.copy().items():
            self.cancel_order(order)

    # todo move
    def cancel_active_sell_orders(self):
        for order_id, order in self.active_sell_orders.copy().items():
            self.cancel_order(order)

    # todo move
    def remove_order_from_active_list(self, order: PostOrderResponse | OrderState):
        if order.order_id in self.active_buy_orders:
            del self.active_buy_orders[order.order_id]
        if order.order_id in self.active_sell_orders:
            del self.active_sell_orders[order.order_id]

    # todo move
    def cancel_order(self, order: PostOrderResponse):
        self.remove_order_from_active_list(order)
        res = self.bot.client.cancel_order(order)
        self.bot.accounting.del_order(order)

        # запрашиваем статус и если есть исполненные позиции - делаем обратную операцию
        order_executed, order_state = self.bot.client.order_is_executed(order)
        if order_state:
            lots_executed = order_state.lots_executed
            if lots_executed != 0:
                if order_executed:
                    self.apply_order_execution(order_state)
                    self.remove_order_from_active_list(order)
                else:
                    self.bot.logger.error(f"!!!!!!!!!--------- сработала не полная продажа {order}, {order_state}")
                    # зарегистрировать частичное исполнение
                    self.bot.accounting.add_deal_by_order(order_state)
                    # и откатить его
                    if order_state.direction == OrderDirection.ORDER_DIRECTION_BUY:
                        self.sell(lots_executed)
                    else:
                        self.buy(lots_executed)

        if res:
            prefix = "Buy" if order.direction == OrderDirection.ORDER_DIRECTION_BUY else "Sell"
            lots = OrderHelper.get_lots(order)
            avg_price = self.bot.get_order_avg_price(order)
            self.bot.log(f"{prefix} order canceled, {lots} x {avg_price} {self.bot.get_cur_count_for_log()}")

    # todo move
    def cancel_orders_by_limits(self):
        current_price = self.bot.cached_current_price
        if not current_price:
            self.bot.logger.error("Не могу закрыть заявки, нулевая цена")
            return

        # todo закрыть все заявки, если коснулись лимитов

        # берем текущую цену + сдвиг
        if self.bot.config.threshold_buy_steps:
            threshold_price = (current_price - self.bot.config.step_size * self.bot.config.threshold_buy_steps)

            # перебираем активные заявки на покупку и закрываем всё, что ниже
            for order_id, order in self.active_buy_orders.copy().items():
                order_price = self.bot.get_order_avg_price(order)
                if order_price <= threshold_price:
                    self.cancel_order(order)

        if self.bot.config.threshold_sell_steps:
            threshold_price = (current_price + self.bot.config.step_size * self.bot.config.threshold_sell_steps)

            # перебираем активные заявки на продажу и закрываем всё, что ниже
            for order_id, order in self.active_sell_orders.copy().items():
                order_price = self.bot.get_order_avg_price(order)
                if order_price >= threshold_price:
                    self.cancel_order(order)

    def round(self, price) -> float:
        return self.client.round(price)

    def get_order_avg_price(self, order: PostOrderResponse | OrderState) -> float:
        return self.round(OrderHelper.get_avg_price(order))

    def equivalent_prices(self, quotation_price: Quotation | MoneyValue, float_price: float) -> bool:
        rounded_quotation_price = self.client.q2f(quotation_price)
        rounded_float_price = self.round(float_price)
        return rounded_quotation_price == rounded_float_price

    def get_cur_count_for_log(self):
        """
        Формат '| s3 (x5+1=16) | p 1.3 rub'
        для отрицательных работает так '| s-3 (x5+3=-12)'
        """
        rest = self.get_current_step_rest_count()
        return (f"| s{self.get_current_step_count()} "
                f"(x{self.config.step_lots}"
                f"{'+' + str(rest) if rest else ''}"
                f"={self.get_current_count()}) "
                f"| p {self.get_current_profit()} {self.client.instrument.currency}"
                )

    def get_status_str(self) -> str:
        out = f"cur {self.cached_current_price} | " \
              f"buy {self.get_existing_buy_order_prices()} " \
              f"sell {self.get_existing_sell_order_prices()} " \
              f"{self.get_cur_count_for_log()}"

        if self.run_state:
            out += f"[o{self.run_state.open} " \
                   f"l{self.run_state.low} " \
                   f"h{self.run_state.high} " \
                   f"c{self.run_state.close}]"

        return out

    def get_current_price(self) -> float | None:
        return self.client.get_current_price()

    # общее количество акций в портфеле
    def get_current_count(self) -> int:
        return self.accounting.get_num()

    # количество полных наборов лотов в портфеле
    def get_current_step_count(self) -> int:
        if self.config.step_lots == 0:
            return 0
        return self.get_current_count() // self.config.step_lots

    # остаток количества акций - сколько ЛИШНИХ от количества полных лотов
    def get_current_step_rest_count(self) -> int:
        return self.get_current_count() % self.config.step_lots
