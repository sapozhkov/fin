import math
from datetime import time as datetime_time
from typing import Tuple

import pandas as pd
from tinkoff.invest import OrderDirection, OrderType, Quotation, MoneyValue, OrderState, PostOrderResponse

from dto.config_dto import ConfigDTO
from lib.order_helper import OrderHelper
from lib.time_helper import TimeHelper
from prod_env.accounting_helper import AbstractAccountingHelper, AccountingHelper
from prod_env.logger_helper import LoggerHelper, AbstractLoggerHelper
from prod_env.time_helper import TimeProdEnvHelper, AbstractTimeHelper
from prod_env.tinkoff_client import TinkoffProxyClient, AbstractProxyClient


class TradingBot:
    STATE_NEW = 1
    STATE_WORKING = 2
    STATE_FINISHED = 3

    # количество секунд задержки старта работы в начале торгового дня. хак, чтобы не влететь в отсечку утром
    START_SEC_SHIFT = 1

    def __init__(
            self,
            token,
            config: ConfigDTO,
            time_helper: AbstractTimeHelper | None = None,
            logger_helper: AbstractLoggerHelper | None = None,
            client_helper: AbstractProxyClient | None = None,
            accounting_helper: AbstractAccountingHelper | None = None,
            order_helper: OrderHelper | None = None
    ):
        # хелперы и DTO
        self.config = config
        self.time = time_helper or TimeProdEnvHelper()
        self.logger = logger_helper or LoggerHelper(__name__, config.name or config.ticker)
        self.client = client_helper or TinkoffProxyClient(token, self.config.ticker, self.time, self.logger)
        self.accounting = accounting_helper or AccountingHelper(__file__, self.client)
        self.order_helper = order_helper or OrderHelper(self.client)

        if not self.is_trading_day():
            self.log("Не торговый день. Завершаем работу.")
            self.state = self.STATE_FINISHED
            return

        self.accounting.set_num(min(
            self.accounting.get_instrument_count(),
            self.config.step_max_cnt * self.config.step_lots
        ))
        if self.config.use_shares is not None:
            self.accounting.set_num(min(self.accounting.get_num(), self.config.use_shares))

        # внутренние переменные
        self.state = self.STATE_NEW
        self.start_price = 0
        self.start_count = 0
        self.cached_current_price: float | None = 0

        self.active_buy_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на покупку
        self.active_sell_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на продажу

        self.validate_and_modify_config()

        self.log(f"INIT \n"
                 f"     config - {self.config}\n"
                 f"     instrument - {self.client.instrument}\n"
                 f"     cur_used_cnt - {self.get_current_count()}\n"
                 f"     max_port - {self.round(self.start_price * self.config.step_max_cnt * self.config.step_lots)}"
                 )

    def is_trading_day(self):
        return TimeHelper.is_working_day(self.time.now())

    def validate_and_modify_config(self):
        if self.config.majority_trade and not self.client.instrument.short_enabled_flag:
            self.config.majority_trade = False
            self.config.maj_to_zero = False
            self.log(f"Change majority_trade to False. Instrument short_enabled_flag is False")
            if self.config.step_base_cnt < 0:
                self.config.step_base_cnt = 0
                self.log(f"Change step_base_cnt to 0")

        # вот тут проводим переустановку base
        self.pretest_and_modify_config()

    def pretest_and_modify_config(self):
        if not self.config.pretest_period:
            return

        current_trend = self.get_rsi_trend_val(self.config.pretest_period)
        if current_trend is None:
            return

        if current_trend >= .5:
            self.config.step_base_cnt = self.config.step_max_cnt
        else:
            if self.config.majority_trade:
                self.config.step_base_cnt = -self.config.step_max_cnt
            else:
                self.config.step_base_cnt = 0

        self.log(f"Pretest. RSI = {round(current_trend, 2)}")
        self.log(f"Change step_base_cnt to {self.config.step_base_cnt}")

    def get_rsi_trend_val(self, period) -> float | None:
        to_date = self.time.get_delta_days_date(days=1)
        from_date = self.time.get_delta_days_date(days=period * 2, from_date=to_date)  # Удваиваем период для точности

        candles = self.client.get_day_candles(from_date, to_date)

        closing_prices = pd.Series([self.client.quotation_to_float(candle.close) for candle in candles.candles])

        delta = closing_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 1 - (1 / (1 + rs))
        try:
            current_trend = rsi.iloc[-1]
        except IndexError as err:
            self.logger.error(f'Error while counting RSI: {err}')
            return None

        return current_trend

    def log(self, message, repeat=False):
        self.logger.log(message, repeat)

    def round(self, price) -> float:
        return self.client.round(price)

    def can_trade(self) -> Tuple[bool, int]:
        """
        Проверяет доступна ли торговля.
        Отдает статус "можно торговать" и количество секунд для задержки, если нет
        :return: (bool, int)
        """
        now = self.time.now()
        now_time = now.time()

        start_hour_str, start_min_str = self.config.start_time.split(':')
        end_hour_str, end_min_str = self.config.end_time.split(':')

        start_time = datetime_time(int(start_hour_str), int(start_min_str), self.START_SEC_SHIFT)
        end_time = datetime_time(int(end_hour_str), int(end_min_str))

        # ко времени запуска приближаемся шагами в половину оставшегося времени
        if now_time < start_time:
            now_sec = now_time.hour * 3600 + now_time.minute * 60 + now_time.second
            start_sec = start_time.hour * 3600 + start_time.minute * 60 + start_time.second
            delta_seconds = start_sec - now_sec
            return False, max(2, round(delta_seconds / 2))

        if now_time >= end_time:
            self.stop()
            return False, 0

        return True, 0

    def place_order(self, order_type: int, direction: int, lots: int, price: float | None = None) \
            -> PostOrderResponse | None:

        order = self.client.place_order(lots, direction, price, order_type)
        if order is None:
            return None

        self.accounting.add_order(order)
        avg_price = self.order_helper.get_avg_price(order)

        if order_type == OrderType.ORDER_TYPE_MARKET:
            self.accounting.add_deal_by_order(order)
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

        self.log(f"{prefix}, {lots} x {avg_price} {self.get_cur_count_for_log()}")

        return order

    def buy(self, lots: int = 1) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_MARKET, OrderDirection.ORDER_DIRECTION_BUY, lots, None)

    def sell(self, lots: int = 1) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_MARKET, OrderDirection.ORDER_DIRECTION_SELL, lots, None)

    def sell_limit(self, price: float, lots: int = 1) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_LIMIT, OrderDirection.ORDER_DIRECTION_SELL, lots, price)

    def buy_limit(self, price: float, lots: int = 1) -> PostOrderResponse | None:
        return self.place_order(OrderType.ORDER_TYPE_LIMIT, OrderDirection.ORDER_DIRECTION_BUY, lots, price)

    def equivalent_prices(self, quotation_price: Quotation | MoneyValue, float_price: float) -> bool:
        rounded_quotation_price = self.client.quotation_to_float(quotation_price)
        rounded_float_price = self.round(float_price)
        return rounded_quotation_price == rounded_float_price

    def set_sell_order_by_buy_order(self, order: OrderState):
        price = self.order_helper.get_avg_price(order)
        price += self.config.step_size
        self.sell_limit(price, self.config.step_lots)

    def apply_order_execution(self, order: OrderState):
        lots = self.order_helper.get_lots(order)
        avg_price = self.order_helper.get_avg_price(order)
        type_text = 'BUY' if order.direction == OrderDirection.ORDER_DIRECTION_BUY else 'SELL'
        self.accounting.add_deal_by_order(order)
        self.log(f"{type_text} order executed, {lots} x {avg_price} {self.get_cur_count_for_log()}")

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
                self._remove_order_from_active_list(order)

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
                self._remove_order_from_active_list(order)

        self.log(f"Orders: "
                 f"buy {self.get_existing_buy_order_prices()}, "
                 f"sell {self.get_existing_sell_order_prices()} ")

    def get_current_price(self) -> float | None:
        return self.client.get_current_price()

    # общее количество акций в портфеле
    def get_current_count(self) -> int:
        return self.accounting.get_num()

    # количество полных наборов лотов в портфеле
    def get_current_step_count(self) -> int:
        return self.get_current_count() // self.config.step_lots

    # остаток количества акций - сколько ЛИШНИХ от количества полных лотов
    def get_current_step_rest_count(self) -> int:
        return self.get_current_count() % self.config.step_lots

    def get_existing_buy_order_prices(self) -> list[float]:
        return [self.order_helper.get_avg_price(order)
                for order_id, order in self.active_buy_orders.items()]

    def get_existing_sell_order_prices(self) -> list[float]:
        return [self.order_helper.get_avg_price(order)
                for order_id, order in self.active_sell_orders.items()]

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

    def cancel_active_orders(self):
        """Отменяет все активные заявки."""
        for order_id, order in self.active_buy_orders.copy().items():
            self.cancel_order(order)

        for order_id, order in self.active_sell_orders.copy().items():
            self.cancel_order(order)

    def _remove_order_from_active_list(self, order: PostOrderResponse | OrderState):
        if order.order_id in self.active_buy_orders:
            del self.active_buy_orders[order.order_id]
        if order.order_id in self.active_sell_orders:
            del self.active_sell_orders[order.order_id]

    def cancel_order(self, order: PostOrderResponse):
        self._remove_order_from_active_list(order)
        res = self.client.cancel_order(order)
        self.accounting.del_order(order)

        # запрашиваем статус и если есть исполненные позиции - делаем обратную операцию
        _, order_state = self.client.order_is_executed(order)
        if order_state:
            lots_executed = order_state.lots_executed
            if lots_executed != 0:
                self.logger.error(f"!!!!!!!!!--------- сработала не полная продажа {order}")
                # зарегистрировать частичное исполнение
                self.accounting.add_deal_by_order(order_state)
                # и откатить его
                if order_state.direction == OrderDirection.ORDER_DIRECTION_BUY:
                    self.sell(lots_executed)
                else:
                    self.buy(lots_executed)

        if res:
            prefix = "Buy" if order.direction == OrderDirection.ORDER_DIRECTION_BUY else "Sell"
            lots = self.order_helper.get_lots(order)
            avg_price = self.order_helper.get_avg_price(order)
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
                order_price = self.order_helper.get_avg_price(order)
                if order_price <= threshold_price:
                    self.cancel_order(order)

        if self.config.threshold_sell_steps:
            threshold_price = (current_price + self.config.step_size * self.config.threshold_sell_steps)

            # перебираем активные заявки на продажу и закрываем всё, что ниже
            for order_id, order in self.active_sell_orders.copy().items():
                order_price = self.order_helper.get_avg_price(order)
                if order_price >= threshold_price:
                    self.cancel_order(order)

    def continue_trading(self):
        return self.state != self.STATE_FINISHED

    def run(self):
        while self.continue_trading():
            self.run_iteration()
        self.log('END')

    def update_cached_price(self):
        self.cached_current_price = self.get_current_price()

    def start(self):
        """Начало работы скрипта. первый старт"""

        if self.state != self.STATE_NEW:
            return

        self.state = self.STATE_WORKING

        self.start_count = self.get_current_count()
        self.start_price = self.cached_current_price
        if not self.start_price:
            self.logger.error("Ошибка первичного запроса цены. Статистика будет неверной в конце работы")
            self.start_price = 0

        # требуемое изменение портфеля
        need_operations = self.config.step_base_cnt * self.config.step_lots - self.get_current_count()

        # докупаем недостающие по рыночной цене
        if need_operations > 0:
            self.buy(need_operations)

        if self.config.majority_trade and need_operations < 0:
            self.sell(-need_operations)

    def run_iteration(self):
        can_trade, sleep_sec = self.can_trade()
        if not can_trade:
            if sleep_sec:
                self.log(f"can not trade, sleep {TimeProdEnvHelper.get_remaining_time_text(sleep_sec)}")
                self.time.sleep(sleep_sec)
            return

        self.update_cached_price()

        if self.check_need_stop():
            self.stop(True)
            return

        self.start()

        # Обновляем список активных заявок, тут же заявки на продажу при удачной покупке
        self.update_orders_status()

        # закрываем заявки, которые не входят в лимиты
        self.cancel_orders_by_limits()

        # Выставляем заявки
        self.place_buy_orders()
        self.place_sell_orders()

        # self.logger.debug(f"Ждем следующего цикла, sleep {self.config.sleep_trading}")
        self.time.sleep(self.config.sleep_trading)

    def check_need_stop(self):
        if not self.start_price or not (self.config.stop_up_p or self.config.stop_down_p):
            return False

        profit = self.get_current_profit()
        max_portfolio = self.start_price * self.config.step_max_cnt * self.config.step_lots

        need_profit = self.round(max_portfolio * self.config.stop_up_p)
        if self.config.stop_up_p and profit > need_profit:
            self.log(f"Останавливаем по получению нужного уровня прибыли. "
                     f"profit={profit}, stop_up_p={self.config.stop_up_p}, need_profit={need_profit}")
            return True

        need_loss = self.round(max_portfolio * self.config.stop_down_p)
        if self.config.stop_down_p and profit < -need_loss:
            self.log(f"Останавливаем по достижению критического уровня потерь. "
                     f"profit={profit}, stop_up_p={self.config.stop_down_p}, need_loss=-{need_loss}")
            return True

        return False

    def stop(self, to_zero=False):
        if self.state == self.STATE_FINISHED:
            return

        self.state = self.STATE_FINISHED

        self.log("Остановка бота...")
        self.cancel_active_orders()

        # если в конце дня надо вернуться в 0 лотов на балансе
        if self.config.maj_to_zero or to_zero:
            current_count = self.get_current_count()

            # продать откупленные инструменты
            if to_zero and current_count > 0:
                self.sell(current_count)

            # и откупить перепроданные
            if current_count < 0:
                self.buy(-current_count)

        current_price = self.get_current_price()
        if not current_price:
            self.logger.error("Нулевая цена, статистика НЕ будет верной")

        profit = self.get_current_profit(current_price)

        max_start_total = self.start_price * self.config.step_max_cnt * self.config.step_lots
        if max_start_total:
            self.log(f"Итог {round(profit, 2)} {self.client.instrument.currency} "
                     f"({round(100 * profit / max_start_total, 2)}%)\n\n")

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
