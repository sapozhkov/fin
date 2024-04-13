import math
import os
import sys
import traceback
from datetime import time as datetime_time
from signal import *

import pandas as pd
from dotenv import load_dotenv
from tinkoff.invest import OrderDirection, OrderType, Quotation, MoneyValue, OrderState, PostOrderResponse

from dto.config_dto import ConfigDTO
from prod_env.accounting_helper import AbstractAccountingHelper, AccountingHelper
from prod_env.logger_helper import LoggerHelper, AbstractLoggerHelper
from prod_env.time_helper import TimeHelper, AbstractTimeHelper
from prod_env.tinkoff_client import TinkoffProxyClient, AbstractProxyClient

load_dotenv()

TOKEN = os.getenv("INVEST_TOKEN")
TICKER = 'RNFT'


class ScalpingBot:
    STATE_NEW = 1
    STATE_WORKING = 2
    STATE_FINISHED = 3

    def __init__(
            self, token, ticker,
            config: ConfigDTO | None = None,
            time_helper: AbstractTimeHelper | None = None,
            logger_helper: AbstractLoggerHelper | None = None,
            client_helper: AbstractProxyClient | None = None,
            accounting_helper: AbstractAccountingHelper | None = None,
    ):
        # хелперы
        self.config = config or ConfigDTO()
        self.time = time_helper or TimeHelper()
        self.logger = logger_helper or LoggerHelper(__name__)
        self.client = client_helper or TinkoffProxyClient(token, ticker, self.time, self.logger)
        self.accounting = accounting_helper or AccountingHelper(__file__, self.client)

        self.accounting.num = min(self.accounting.get_instrument_count(), self.config.max_shares)
        if self.config.use_shares is not None:
            self.accounting.num = min(self.accounting.num, self.config.use_shares)

        # внутренние переменные
        self.state = self.STATE_NEW
        self.start_price = 0
        self.start_count = 0

        self.active_buy_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на покупку
        self.active_sell_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на продажу

        # вот тут проводим переустановку base
        self.pretest_and_modify_config()

        self.log(f"INIT \n"
                 f"     figi - {self.client.figi} ({self.client.ticker})\n"
                 f"     config - {self.config}"
                 f"     max_shares - {self.config.max_shares}\n"
                 f"     base_shares - {self.config.base_shares}\n"
                 f"     step_size - {self.config.step_size} {self.client.currency}\n"
                 f"     step_cnt - {self.config.step_cnt}\n"
                 f"     cur_used_cnt - {self.get_current_count()}\n"
                 )

    def pretest_and_modify_config(self):
        if not self.config.pretest_period:
            return

        current_trend = self.get_rsi_trend_val(self.config.pretest_period)
        if current_trend is None:
            return

        if current_trend >= .5:
            self.config.base_shares = self.config.max_shares
        else:
            if self.config.majority_trade:
                self.config.base_shares = -self.config.max_shares
            else:
                self.config.base_shares = 0

        self.log(f"Pretest. RSI = {round(current_trend, 2)}")
        self.log(f"Change config to {self.config}")

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

    def can_trade(self) -> (bool, int):
        """
        Проверяет доступна ли торговля.
        Отдает статус "можно торговать" и количество секунд для задержки, если нет
        :return: (bool, int)
        """
        now = self.time.now()
        now_time = now.time()

        # Проверка, что сейчас будний день (0 - понедельник, 6 - воскресенье)
        if now.weekday() >= 5:
            self.stop()
            return False, 0

        start_hour_str, start_min_str = self.config.start_time.split(':')
        end_hour_str, end_min_str = self.config.end_time.split(':')

        start_time = datetime_time(int(start_hour_str), int(start_min_str))
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

        # Проверка доступности рыночной торговли через API
        if not self.client.can_trade():
            return False, self.config.sleep_no_trade

        return True, 0

    def place_order(self, order_type: int, direction: int, lots: int, price: float | None = None) \
            -> PostOrderResponse | None:

        order = self.client.place_order(lots, direction, price, order_type)
        if order is None:
            return None

        self.accounting.add_order(order)

        if order_type == OrderType.ORDER_TYPE_MARKET:
            self.accounting.add_deal_by_order(order)
            price = self.client.quotation_to_float(order.executed_order_price)
            if direction == OrderDirection.ORDER_DIRECTION_BUY:
                prefix = "BUY MARKET executed"
                price = -price
            else:
                prefix = "SELL MARKET executed"

        else:
            price = self.client.quotation_to_float(order.initial_order_price)
            if direction == OrderDirection.ORDER_DIRECTION_BUY:
                self.active_buy_orders[order.order_id] = order
                prefix = "Buy order set"
                price = -price
            else:
                self.active_sell_orders[order.order_id] = order
                prefix = "Sell order set"

        self.log(f"{prefix}, price {price} (n={self.get_current_count()})")

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
        rounded_float_price = self.client.round(float_price)
        return rounded_quotation_price == rounded_float_price

    def set_sell_order_by_buy_order(self, order: OrderState):
        price = self.client.quotation_to_float(order.executed_order_price)
        price += self.config.step_size
        self.sell_limit(price)

    def apply_order_execution(self, order: OrderState):
        price = self.client.quotation_to_float(order.executed_order_price)
        type_text = 'BUY' if order.direction == OrderDirection.ORDER_DIRECTION_BUY else 'SELL'
        self.accounting.add_deal_by_order(order)
        self.log(f"{type_text} order executed, price {price}"
                 f" (n={self.get_current_count()})")

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

    def get_current_count(self) -> int:
        return self.accounting.num

    def get_existing_buy_order_prices(self) -> list[float]:
        return [self.client.quotation_to_float(order.initial_order_price)
                for order_id, order in self.active_buy_orders.items()]

    def get_existing_sell_order_prices(self) -> list[float]:
        return [self.client.quotation_to_float(order.initial_order_price)
                for order_id, order in self.active_sell_orders.items()]

    def place_buy_orders(self):
        current_price = self.get_current_price()
        if not current_price:
            self.logger.error("Не могу выставить заявки на покупку, нулевая цена")
            return

        current_buy_orders_cnt = len(self.active_buy_orders)
        current_shares_cnt = self.get_current_count()
        current_price = math.floor(current_price / self.config.step_size) * self.config.step_size

        target_prices = [current_price - i * self.config.step_size for i in range(1, self.config.step_cnt + 1)]

        # Исключаем цены, по которым уже выставлены заявки на покупку
        existing_order_prices = self.get_existing_buy_order_prices()

        # Ставим заявки на покупку
        for price in target_prices:
            if current_buy_orders_cnt + current_shares_cnt >= self.config.max_shares:
                break
            if price in existing_order_prices:
                continue
            self.buy_limit(price)
            current_buy_orders_cnt += 1

    def place_sell_orders(self):
        current_price = self.get_current_price()
        if not current_price:
            self.logger.error("Не могу выставить заявки на продажу, нулевая цена")
            return

        # todo попробовать продублировать логику из buy метода

        count_to_sell = self.get_current_count() - len(self.active_sell_orders)
        current_price = math.ceil(current_price / self.config.step_size) * self.config.step_size
        target_prices = [current_price + i * self.config.step_size for i in range(1, count_to_sell + 1)]

        # Ставим заявки на продажу
        for price in sorted(list(target_prices), reverse=True):
            self.sell_limit(price)

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

        if res:
            prefix = "Buy" if order.direction == OrderDirection.ORDER_DIRECTION_BUY else "Sell"
            price = self.client.quotation_to_float(order.initial_order_price)
            self.log(f"{prefix} order canceled, price {price} (n={self.get_current_count()})")

    def cancel_orders_by_limits(self):
        current_price = self.get_current_price()
        if not current_price:
            self.logger.error("Не могу закрыть заявки, нулевая цена")
            return

        # берем текущую цену + сдвиг
        if self.config.threshold_buy_steps:
            threshold_price = (current_price - self.config.step_size * self.config.threshold_buy_steps)

            # перебираем активные заявки на покупку и закрываем всё, что ниже
            for order_id, order in self.active_buy_orders.copy().items():
                order_price = self.client.quotation_to_float(order.initial_order_price)
                if order_price <= threshold_price:
                    self.cancel_order(order)

        if self.config.threshold_sell_steps:
            threshold_price = (current_price + self.config.step_size * self.config.threshold_sell_steps)

            # перебираем активные заявки на продажу и закрываем всё, что ниже
            for order_id, order in self.active_sell_orders.copy().items():
                order_price = self.client.quotation_to_float(order.initial_order_price)
                if order_price >= threshold_price:
                    self.cancel_order(order)
                    self.sell()

    def continue_trading(self):
        return self.state != self.STATE_FINISHED

    def run(self):
        while self.continue_trading():
            self.run_iteration()
        self.log('END')

    def start(self):
        """Начало работы скрипта. первый старт"""

        if self.state != self.STATE_NEW:
            return

        self.state = self.STATE_WORKING

        self.start_count = self.get_current_count()
        self.start_price = self.get_current_price()
        if not self.start_price:
            self.logger.error("Ошибка первичного запроса цены. Статистика будет неверной в конце работы")
            self.start_price = 0

        # требуемое изменение портфеля
        need_operations = self.config.base_shares - self.start_count

        # докупаем недостающие по рыночной цене
        if need_operations > 0:
            for _ in range(need_operations):
                self.buy()

        if self.config.majority_trade and need_operations < 0:
            for _ in range(-need_operations):
                self.sell()

    def run_iteration(self):
        can_trade, sleep_sec = self.can_trade()
        if not can_trade:
            if sleep_sec:
                self.log(f"can not trade, sleep {TimeHelper.get_remaining_time_text(sleep_sec)}")
                self.time.sleep(sleep_sec)
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

    def stop(self):
        if self.state == self.STATE_FINISHED:
            return

        self.state = self.STATE_FINISHED

        self.log("Остановка бота...")
        self.cancel_active_orders()

        # продать откупленные инструменты
        need_to_sell = self.get_current_count() - self.config.base_shares

        if need_to_sell > 0:
            for _ in range(need_to_sell):
                self.sell()

        current_price = self.get_current_price()
        if not current_price:
            self.logger.error("Нулевая цена, статистика НЕ будет верной")

        change = (
                - self.start_price * self.start_count
                + self.accounting.sum
                + current_price * self.get_current_count()
        )

        max_start_total = self.start_price * self.config.max_shares
        if max_start_total:
            self.log(f"Итог {round(change, 2)} {self.client.currency} "
                     f"({round(100 * change / max_start_total, 2)}%)")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        config_dto = ConfigDTO(
        )
    else:
        config_dto = ConfigDTO.from_string(sys.argv[1])

    bot = ScalpingBot(TOKEN, TICKER, config_dto)

    if len(sys.argv) > 1:
        bot.log(f"Config string: {sys.argv[1]}")

    def clean(*_args):
        bot.stop()
        sys.exit(0)

    for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
        signal(sig, clean)

    try:
        bot.run()
    except Exception as e:
        traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        bot.logger.error(f"Не перехваченное исключение: {e}\nТрассировка: \n{traceback_str}")
        bot.stop()
