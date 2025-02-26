from .trade_abstract_strategy import TradeAbstractStrategy


class TradeShiftV2Strategy(TradeAbstractStrategy):
    def __init__(
            self,
            bot
    ):
        super().__init__(bot)
        self.bought_price = 0
        self.sold_price = 0
        self.order_map = []

    def on_day_start(self) -> bool:
        if not super().on_day_start():
            return False

        start_price = self.cached_current_price
        step_size = self.config.step_size
        step_size_shift = self.config.step_size_shift
        step_max_cnt = self.config.step_max_cnt

        sell_levels = []
        current_sell = start_price
        for i in range(1, step_max_cnt + 1):
            increment = step_size * (1 + step_size_shift * i)
            current_sell += increment
            sell_levels.append(self.round(current_sell))

        # Расчет уровней для покупки
        buy_levels = []
        current_buy = start_price
        for i in range(1, step_max_cnt + 1):
            decrement = step_size * (1 + step_size_shift * i)
            current_buy -= decrement
            buy_levels.append(self.round(current_buy))

        # Объединяем уровни покупки, стартовую цену и уровни продажи
        order_map = buy_levels + [self.round(start_price)] + sell_levels

        # Убираем возможные дубликаты и сортируем по возрастанию
        self.order_map = sorted(set(order_map))

        self.log(f"Определены уровни для fan v2 {self.order_map}")

        return True

    def update_orders_status(self):
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
                    # обнуляем только в случае противоположного события
                    self.sold_price = 0
                self.remove_order_from_active_list(order)

        # Аналогично для заявок на продажу
        for order_id, order in self.active_sell_orders.copy().items():
            if order_id not in active_order_ids:
                is_executed, order_state = self.client.order_is_executed(order)
                if is_executed and order_state:
                    self.apply_order_execution(order_state)
                    self.sold_price = self.get_order_avg_price(order_state)
                    self.bought_price = 0
                self.remove_order_from_active_list(order)

    def get_required_buy_levels(self):
        low_bound = self.lower_limit()
        max_price = min(
            self.cached_current_price,
            self.bought_price if self.bought_price else float("inf"),
            self.sold_price if self.sold_price else float("inf"),
        )
        levels_to_buy = [price for price in self.order_map if price < max_price]
        required_buy = levels_to_buy[-self.config.step_set_orders_cnt:] \
            if len(levels_to_buy) >= self.config.step_set_orders_cnt else levels_to_buy
        required_buy = [price for price in required_buy if price >= low_bound]
        return required_buy

    def get_required_sell_levels(self):
        up_bound = self.upper_limit()
        min_price = max(self.cached_current_price, self.sold_price, self.bought_price)
        levels_to_sell = [price for price in self.order_map if price > min_price]
        required_sell = levels_to_sell[:self.config.step_set_orders_cnt] \
            if len(levels_to_sell) >= self.config.step_set_orders_cnt else levels_to_sell
        required_sell = [price for price in required_sell if price <= up_bound]
        return required_sell

    def place_buy_orders(self):
        cur_order_prices = self.get_existing_buy_order_prices()
        cur_orders_cnt = len(cur_order_prices)
        need_to_add = self.config.step_set_orders_cnt - cur_orders_cnt

        # если их нужное количество - выходим
        if need_to_add <= 0 and not self.sold_price:
            return

        # выставляем заявки, которых нет
        required_buy = self.get_required_buy_levels()
        for price in required_buy:
            if price not in cur_order_prices:
                self.buy_limit(price, self.config.step_lots)

        # закрываем лишние заявки, которых не должно быть по плану
        for _, order in self.active_buy_orders.copy().items():
            if self.get_order_avg_price(order) not in required_buy:
                self.cancel_order(order)

    def place_sell_orders(self):
        cur_order_prices = self.get_existing_sell_order_prices()
        cur_orders_cnt = len(cur_order_prices)
        need_to_add = self.config.step_set_orders_cnt - cur_orders_cnt

        # если их нужное количество - выходим
        if need_to_add <= 0 and not self.bought_price:
            return

        # выставляем заявки, которых нет
        required_sell = self.get_required_sell_levels()
        for price in required_sell:
            if price not in cur_order_prices:
                self.sell_limit(price, self.config.step_lots)

        # закрываем лишние заявки, которых не должно быть по плану
        for _, order in self.active_sell_orders.copy().items():
            if self.get_order_avg_price(order) not in required_sell:
                self.cancel_order(order)

    def to_zero_on_end(self) -> bool:
        """Возвращает True если нужно выходить в 0 при завершении работы бота"""
        return True
