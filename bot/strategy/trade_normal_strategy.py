import math

from tinkoff.invest import OrderState

from .trade_abstract_strategy import TradeAbstractStrategy

# todo подумать что еще можно сюда утащить. кажется можно переместить часть, отвечающую именно за хранение данных
"""
apply_order_execution
set_sell_order_by_buy_order
remove_order_from_active_list
get_existing_buy_order_prices
get_existing_sell_order_prices

"""


class TradeNormalStrategy(TradeAbstractStrategy):
    def update_orders_status(self):
        active_orders = self.client.get_active_orders()
        if active_orders is None:
            return
        active_order_ids = [order.order_id for order in active_orders]

        # Обновление заявок на продажу
        for order_id, order in self.active_buy_orders.copy().items():
            if order_id not in active_order_ids:
                is_executed, order_state = self.client.order_is_executed(order)
                if is_executed and order_state:
                    self.apply_order_execution(order_state)
                    self.set_sell_order_by_buy_order(order_state)
                self.remove_order_from_active_list(order)

        # обновляем список активных, так как список меняется в блоке выше
        active_orders = self.client.get_active_orders()
        if active_orders is None:
            return
        active_order_ids = [order.order_id for order in active_orders]

        # Аналогично для заявок на покупку
        for order_id, order in self.active_sell_orders.copy().items():
            if order_id not in active_order_ids:
                is_executed, order_state = self.client.order_is_executed(order)
                if is_executed and order_state:
                    self.apply_order_execution(order_state)
                self.remove_order_from_active_list(order)

        self.log(f"Orders: "
                     f"buy {self.get_existing_buy_order_prices()}, "
                     f"sell {self.get_existing_sell_order_prices()} ")

    def place_buy_orders(self):
        current_price = self.cached_current_price
        if not current_price:
            self.logger.error("Не могу выставить заявки на покупку, нулевая цена")
            return

        current_buy_orders_cnt = len(self.active_buy_orders)
        current_step_cnt = self.get_current_step_count()
        current_price = math.floor(current_price / self.config.step_size) * self.config.step_size

        target_prices = [current_price - i * self.config.step_size
                         for i in range(1, self.config.step_set_orders_cnt + 1)]
        # target_prices = [self.round(current_price - i * self.config.step_size) for i in range(1,
        # self.config.step_set_orders_cnt + 1)]

        # Исключаем цены, по которым уже выставлены заявки на покупку
        existing_order_prices = self.get_existing_buy_order_prices()

        # Ставим заявки на покупку
        for price in target_prices:
            if current_buy_orders_cnt + current_step_cnt >= self.config.step_max_cnt:
                break
            if price in existing_order_prices:
                continue
            self.buy_limit(price, self.config.step_lots)
            current_buy_orders_cnt += 1

    def place_sell_orders(self):
        current_price = self.cached_current_price
        if not current_price:
            self.logger.error("Не могу выставить заявки на продажу, нулевая цена")
            return

        current_sell_orders_cnt = len(self.active_sell_orders)
        current_step_cnt = self.get_current_step_count()
        current_price = math.ceil(current_price / self.config.step_size) * self.config.step_size

        # target_prices = [current_price + i * self.config.step_size
        #                  for i in range(1, self.config.step_set_orders_cnt + 1)]
        target_prices = [self.round(current_price + i * self.config.step_size)
                         for i in range(1, self.config.step_set_orders_cnt + 1)]

        # Исключаем цены, по которым уже выставлены заявки
        existing_order_prices = self.get_existing_sell_order_prices()

        # Ставим заявки на продажу
        for price in target_prices:
            min_steps = -self.config.step_max_cnt if self.config.majority_trade else 0
            if current_step_cnt - current_sell_orders_cnt <= min_steps:
                break
            if price in existing_order_prices:
                continue
            self.sell_limit(price, self.config.step_lots)
            current_sell_orders_cnt += 1

    def set_sell_order_by_buy_order(self, order: OrderState):
        price = self.get_order_avg_price(order)
        price += self.config.step_size
        self.sell_limit(price, self.config.step_lots)
