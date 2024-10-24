import math

from .trade_abstract_strategy import TradeAbstractStrategy


class TradeShiftStrategy(TradeAbstractStrategy):
    def __init__(
            self,
            bot
    ):
        super().__init__(bot)
        self.bought_price = 0
        self.sold_price = 0

    def update_orders_status(self):

        self.bought_price = 0
        self.sold_price = 0

        active_orders = self.client.get_active_orders()
        if active_orders is None:
            return
        active_order_ids = [order.order_id for order in active_orders]

        # Обновление заявок на покупку
        for order_id, order in self.active_buy_orders.copy().items():
            if order_id not in active_order_ids:
                is_executed, order_state = self.client.order_is_executed(order)
                if is_executed and order_state:
                    self.apply_order_execution(order_state)
                    self.bought_price = self.get_order_avg_price(order_state)
                self.remove_order_from_active_list(order)

        # Аналогично для заявок на продажу
        for order_id, order in self.active_sell_orders.copy().items():
            if order_id not in active_order_ids:
                is_executed, order_state = self.client.order_is_executed(order)
                if is_executed and order_state:
                    self.apply_order_execution(order_state)
                    self.sold_price = self.get_order_avg_price(order_state)
                self.remove_order_from_active_list(order)

        if self.sold_price or self.bought_price:
            self.cancel_active_orders()

        # self.bot.log(f"Orders: "
        #              f"buy {self.bot.get_existing_buy_order_prices()}, "
        #              f"sell {self.bot.get_existing_sell_order_prices()} ")

        return

    def place_buy_orders(self):
        cur_order_prices = self.get_existing_buy_order_prices()
        cur_orders_cnt = len(cur_order_prices)
        need_to_add = self.config.step_set_orders_cnt - cur_orders_cnt

        # если их нужное количество - выходим
        if need_to_add <= 0:
            return

        if self.sold_price:
            # todo cancel all
            cur_set_order_price = self.sold_price
        elif cur_orders_cnt > 0:
            cur_set_order_price = min(cur_order_prices)
        else:
            current_price = self.cached_current_price
            if self.bought_price:
                current_price = self.round(self.bought_price / self.config.step_size) * self.config.step_size
            if not current_price:
                self.logger.error("Не могу выставить заявки на покупку, нулевая цена")
                return
            # cur_set_order_price = current_price + self.config.step_size / 2  # тут "+", чтобы разница в шаг как раз была
            cur_set_order_price = math.floor(current_price / self.config.step_size) * self.config.step_size

        # добавляем заявки со сдвигом учитывая сколько лотов будет в портфеле при покупке
        for i in range(need_to_add):
            # не надо превышать максимального числа заявок
            if self.get_current_step_count() + i > self.config.step_max_cnt:
                break

            # номер шага для заявки относительно количества в портфеле
            current_step_cnt = max(0, self.get_current_step_count() + i)

            # вычисление сдвига
            price_shift = self.config.step_size * (1 + current_step_cnt * self.config.step_size_shift)

            # смещение текущего значения цены
            cur_set_order_price = self.round(cur_set_order_price - price_shift)

            # выставление заявки
            self.buy_limit(cur_set_order_price, self.config.step_lots)

    def place_sell_orders(self):
        cur_order_prices = self.get_existing_sell_order_prices()
        cur_orders_cnt = len(cur_order_prices)
        need_to_add = self.config.step_set_orders_cnt - cur_orders_cnt

        # если их нужное количество - выходим
        if need_to_add <= 0:
            return

        if self.bought_price:
            cur_set_order_price = self.bought_price
        elif cur_orders_cnt > 0:
            cur_set_order_price = max(cur_order_prices)
        else:
            current_price = self.cached_current_price
            if self.sold_price:
                current_price = self.round(self.sold_price / self.config.step_size) * self.config.step_size
            if not current_price:
                self.logger.error("Не могу выставить заявки на продажу, нулевая цена")
                return
            # cur_set_order_price = current_price - self.config.step_size / 2  # тут "-", чтобы разница в шаг как раз была
            cur_set_order_price = math.ceil(current_price / self.config.step_size) * self.config.step_size

        # добавляем заявки со сдвигом учитывая сколько лотов будет в портфеле при покупке
        for i in range(need_to_add):
            # не надо превышать максимального числа заявок
            min_steps = -self.config.step_max_cnt if self.config.majority_trade else 0
            if self.get_current_step_count() - i <= min_steps:
                break

            # номер шага для заявки относительно количества в портфеле
            current_step_cnt = abs(min(0, self.get_current_step_count() - i))

            # вычисление сдвига
            price_shift = self.config.step_size * (1 + current_step_cnt * self.config.step_size_shift)

            # смещение текущего значения цены
            cur_set_order_price = self.round(cur_set_order_price + price_shift)

            # выставление заявки
            self.sell_limit(cur_set_order_price, self.config.step_lots)
