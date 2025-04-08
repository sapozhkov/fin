from abc import ABC, abstractmethod

from tinkoff.invest import PostOrderResponse, OrderType, OrderDirection, OrderState, Quotation, MoneyValue

from app import AppConfig
from bot.env import AbstractProxyClient, AbstractAccountingHelper
from bot.helper import OrderHelper


class TradeAbstractStrategy(ABC):
    RETRY_DEFAULT = 1
    RETRY_ON_START = 3
    RETRY_SLEEP = 20

    def __init__(
            self,
            bot,
    ):
        self.bot = bot

        self.config = bot.config
        self.time = bot.time
        self.logger = bot.logger
        self.client: AbstractProxyClient = bot.client
        self.accounting: AbstractAccountingHelper = bot.accounting

        self.active_buy_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на покупку
        self.active_sell_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на продажу

        self.start_price: float = 0
        self.start_count: int = 0
        self.update_start_price_and_counter()
        self.cached_current_price: float | None = self.start_price

    def log(self, message, repeat=False):
        self.logger.log(message, repeat)

    def update_start_price_and_counter(self):
        self.start_price = self.update_cached_price() or 0
        self.start_count = self.get_current_count()
        if not self.start_price:
            self.logger.error("Ошибка первичного запроса цены. Статистика будет неверной в конце работы")

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

        order = self.client.place_order(lots // self.client.instrument.lot, direction, price, order_type)
        if order is None:
            fail_price = price if price is not None else self.cached_current_price
            if fail_price is None:
                fail_price = 0.0
            self.accounting.add_order_fail(fail_price, lots)
            if retry > 0:
                self.logger.error(f"RETRY order. {lots}, {direction}, {price}, {order_type}, "
                                  f"sleep {self.RETRY_SLEEP}, retry num={retry}")
                self.time.sleep(self.RETRY_SLEEP)
                return self.place_order(order_type, direction, lots, price, retry-1)
            else:
                return None

        self.accounting.add_order(order)
        avg_price = self.get_order_avg_price(order)

        if order_type == OrderType.ORDER_TYPE_MARKET:
            self.accounting.add_deal_by_order(order)

            # todo del #332
            self.log(f"!!! ORDER_TYPE_MARKET operation {order}")

            if direction == OrderDirection.ORDER_DIRECTION_BUY:
                prefix = "BUY MARKET executed"
                avg_price = -avg_price
            else:
                prefix = "SELL MARKET executed"

        elif order_type == OrderType.ORDER_TYPE_BESTPRICE:

            # todo del #332
            self.log(f"!!! ORDER_TYPE_MARKET operation {order}")

            self.accounting.add_deal_by_order(order)
            if direction == OrderDirection.ORDER_DIRECTION_BUY:
                prefix = "BUY BESTPRICE executed"
                avg_price = -avg_price
            else:
                prefix = "SELL BESTPRICE executed"

        else:
            if direction == OrderDirection.ORDER_DIRECTION_BUY:
                self.active_buy_orders[order.order_id] = order
                prefix = "Buy order set"
                avg_price = -avg_price
            else:
                self.active_sell_orders[order.order_id] = order
                prefix = "Sell order set"

        self.log(f"{prefix}, {lots} x {avg_price} {self.get_cur_count_for_log()}")

        return order

    def buy(self, lots: int = 1, retry=RETRY_DEFAULT) -> PostOrderResponse | None:
        order_type = OrderType.ORDER_TYPE_MARKET if self.client.can_market_order() else OrderType.ORDER_TYPE_BESTPRICE
        return self.place_order(order_type, OrderDirection.ORDER_DIRECTION_BUY, lots, None, retry)

    def sell(self, lots: int = 1, retry=RETRY_DEFAULT) -> PostOrderResponse | None:
        order_type = OrderType.ORDER_TYPE_MARKET if self.client.can_market_order() else OrderType.ORDER_TYPE_BESTPRICE
        return self.place_order(order_type, OrderDirection.ORDER_DIRECTION_SELL, lots, None, retry)

    def sell_limit(self, price: float, lots: int = 1, retry=RETRY_DEFAULT) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_LIMIT, OrderDirection.ORDER_DIRECTION_SELL, lots, price, retry)

    def buy_limit(self, price: float, lots: int = 1, retry=RETRY_DEFAULT) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_LIMIT, OrderDirection.ORDER_DIRECTION_BUY, lots, price, retry)

    def apply_order_execution(self, order: OrderState):
        lots = OrderHelper.get_lots(order)
        avg_price = self.get_order_avg_price(order)
        type_text = 'BUY' if order.direction == OrderDirection.ORDER_DIRECTION_BUY else 'SELL'
        self.accounting.add_deal_by_order(order)
        self.log(f"{type_text} order executed, {lots} x {avg_price} {self.get_cur_count_for_log()}")

    def get_existing_buy_order_prices(self) -> list[float]:
        return [self.get_order_avg_price(order)
                for order_id, order in self.active_buy_orders.items()]

    def get_existing_sell_order_prices(self) -> list[float]:
        return [self.get_order_avg_price(order)
                for order_id, order in self.active_sell_orders.items()]

    def cancel_active_orders(self):
        self.cancel_active_buy_orders()
        self.cancel_active_sell_orders()

    def cancel_active_buy_orders(self):
        for order_id, order in self.active_buy_orders.copy().items():
            self.cancel_order(order)

    def cancel_active_sell_orders(self):
        for order_id, order in self.active_sell_orders.copy().items():
            self.cancel_order(order)

    def remove_order_from_active_list(self, order: PostOrderResponse | OrderState):
        if order.order_id in self.active_buy_orders:
            del self.active_buy_orders[order.order_id]
        if order.order_id in self.active_sell_orders:
            del self.active_sell_orders[order.order_id]

    def cancel_order(self, order: PostOrderResponse):
        self.remove_order_from_active_list(order)
        res = self.client.cancel_order(order)
        self.accounting.del_order(order)

        # запрашиваем статус и если есть исполненные позиции - делаем обратную операцию
        order_executed, order_state = self.client.order_is_executed(order)
        if order_state:
            lots_executed = order_state.lots_executed
            if lots_executed != 0:
                if order_executed:
                    self.apply_order_execution(order_state)
                    self.remove_order_from_active_list(order)
                else:
                    self.log(f"Сработало частичное исполнение лимитной заявки {order_state.lots_executed} / "
                             f"{order_state.lots_requested}")
                    # зарегистрировать частичное исполнение
                    self.accounting.add_deal_by_order(order_state, True)
                    # и откатить его
                    if order_state.direction == OrderDirection.ORDER_DIRECTION_BUY:
                        self.sell(lots_executed)
                    else:
                        self.buy(lots_executed)

        if res:
            prefix = "Buy" if order.direction == OrderDirection.ORDER_DIRECTION_BUY else "Sell"
            lots = OrderHelper.get_lots(order)
            avg_price = self.get_order_avg_price(order)
            self.log(f"{prefix} order canceled, {lots} x {avg_price} {self.get_cur_count_for_log()}")

    def cancel_orders_by_limits(self):
        current_price = self.cached_current_price
        if not current_price:
            self.logger.error("Не могу закрыть заявки, нулевая цена")
            return

        # берем текущую цену + сдвиг
        if self.config.threshold_buy_steps:
            threshold_price = (current_price - self.config.step_size * self.config.threshold_buy_steps)

            # перебираем активные заявки на покупку и закрываем всё, что ниже
            for order_id, order in self.active_buy_orders.copy().items():
                order_price = self.get_order_avg_price(order)
                if order_price <= threshold_price:
                    self.cancel_order(order)

        if self.config.threshold_sell_steps:
            threshold_price = (current_price + self.config.step_size * self.config.threshold_sell_steps)

            # перебираем активные заявки на продажу и закрываем всё, что ниже
            for order_id, order in self.active_sell_orders.copy().items():
                order_price = self.get_order_avg_price(order)
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

    def get_current_profit(self, current_price=None) -> float:
        if current_price is None:
            current_price = self.cached_current_price

        if not current_price:
            return 0

        return self.round(
            - self.start_price * self.start_count
            + self.accounting.get_sum()
            + current_price * self.get_current_count()
        )

    def get_max_start_depo(self):
        # коэф мажоритарной торговли. с ней заявок в 2 раза больше ставится, так как в 2 стороны открываем торги
        maj_k = 2 if self.config.majority_trade else 1
        return self.round(self.start_price * self.config.step_max_cnt * self.config.step_lots * maj_k)

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
        if self.config.step_lots == 0:
            return 0
        return self.get_current_count() % self.config.step_lots

    def update_cached_price(self) -> float | None:
        self.cached_current_price = self.get_current_price()
        return self.cached_current_price

    def on_day_start(self) -> bool:
        self.update_start_price_and_counter()

        if self.cached_current_price is None:
            return False

        # требуемое изменение портфеля
        need_operations = self.config.step_base_cnt * self.config.step_lots - self.get_current_count()

        max_portfolio_size = self.get_max_start_depo()
        self.log(f"START \n"
                 f"     need_operations - {need_operations}\n"
                 f"     start_price - {self.start_price} {self.client.instrument.currency}\n"
                 f"     max_port - {max_portfolio_size} {self.client.instrument.currency}"
                 )

        # докупаем недостающие по рыночной цене
        if need_operations > 0:
            self.buy(need_operations, self.RETRY_ON_START)

        # или продаем лишние. в минус без мажоритарной уйти не должны - учтено в конфиге
        if need_operations < 0:
            self.sell(-need_operations, self.RETRY_ON_START)

        return True

    def to_zero_on_end(self) -> bool:
        """Возвращает True если нужно выходить в 0 при завершении работы бота"""
        return False

    def lower_limit(self) -> float | None:
        if self.cached_current_price is None:
            return None
        return self.round(self.cached_current_price * (1 - AppConfig.ALLOWED_ORDER_RANGE))

    def upper_limit(self) -> float | None:
        if self.cached_current_price is None:
            return None
        return self.round(self.cached_current_price * (1 + AppConfig.ALLOWED_ORDER_RANGE))
