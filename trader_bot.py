import math
import os
import sys
from datetime import time as datetime_time
from signal import *

from dotenv import load_dotenv
from tinkoff.invest import OrderDirection, OrderType, Quotation, MoneyValue, OrderState, PostOrderResponse

from helper.accounting_helper import AbstractAccountingHelper, AccountingHelper
from helper.logger_helper import LoggerHelper, AbstractLoggerHelper
from helper.time_helper import TimeHelper, AbstractTimeHelper
from helper.tinkoff_client import TinkoffProxyClient, AbstractProxyClient

load_dotenv()

TOKEN = os.getenv("INVEST_TOKEN")
TICKER = 'RNFT'


class ScalpingBot:
    STATE_NEW = 1
    STATE_WORKING = 2
    STATE_FINISHED = 3

    def __init__(
            self, token, ticker,

            start_time='07:45',  # 10:45
            end_time='15:15',  # 18:15

            stop_loss_percent=0.3,
            quit_on_balance_up_percent=2,
            quit_on_balance_down_percent=1,

            sleep_trading=5 * 60,
            sleep_no_trade=60,

            max_shares=5,
            base_shares=None,
            threshold_buy_steps=4,
            threshold_sell_steps=8,
            step_size=.5,
            step_cnt=3,

            time_helper: AbstractTimeHelper | None = None,
            logger_helper: AbstractLoggerHelper | None = None,
            client_helper: AbstractProxyClient | None = None,
            accounting_helper: AbstractAccountingHelper | None = None,
    ):
        # хелперы
        self.time = time_helper or TimeHelper()
        self.logger = logger_helper or LoggerHelper(__name__)
        self.client = client_helper or TinkoffProxyClient(token, ticker, self.time, self.logger)
        self.accounting = accounting_helper or AccountingHelper(__file__, self.client)

        self.start_time = start_time
        self.end_time = end_time

        self.max_shares = max_shares
        self.threshold_buy_steps = threshold_buy_steps
        self.threshold_sell_steps = threshold_sell_steps
        self.step_size = step_size
        self.step_cnt = step_cnt

        # количество акций на начало дня и на конец
        self.base_shares = base_shares if base_shares is not None else round(self.max_shares / 2)

        # конфигурация
        self.commission = 0.05 / 100
        # self.quit_on_balance_up_percent = quit_on_balance_up_percent / 100
        # self.quit_on_balance_down_percent = quit_on_balance_down_percent / 100

        self.sleep_trading = sleep_trading
        self.sleep_no_trade = sleep_no_trade

        # внутренние переменные
        self.state = self.STATE_NEW

        self.active_buy_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на покупку
        self.active_sell_orders: dict[str, PostOrderResponse] = {}  # Массив активных заявок на продажу

        self.log(f"INIT \n"
                 f"     figi - {self.client.figi} ({self.client.ticker})\n"
                 f"     commission - {self.commission * 100} %\n"
                 )

    def log(self, message, repeat=False):
        self.logger.log(message, repeat)

    def can_trade(self):
        now = self.time.now()

        # Проверка, что сейчас будний день (0 - понедельник, 6 - воскресенье)
        if now.weekday() >= 5:
            return False

        start_hour_str, start_min_str = self.start_time.split(':')
        end_hour_str, end_min_str = self.end_time.split(':')

        start_time = datetime_time(int(start_hour_str), int(start_min_str))
        end_time = datetime_time(int(end_hour_str), int(end_min_str))

        # Проверка, что текущее время в заданном торговом диапазоне
        if not start_time <= now.time() <= end_time:
            return False

        # Проверка доступности рыночной торговли через API
        if not self.client.can_trade():
            return False

        return True

    def place_order(self, lots: int, operation, price: float | None = None, order_type=OrderType.ORDER_TYPE_MARKET):
        order = self.client.place_order(lots, operation, price, order_type)
        self.accounting.add_order(order)
        return order

    def buy(self, lots: int = 1, price: float | None = None):
        order = self.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY, price)
        self.accounting.add_deal_by_order(order)
        self.log(f"BUY MARKET executed, price {self.client.quotation_to_float(order.executed_order_price)}"
                 f" (n={self.accounting.num})")
        return order

    def sell(self, lots: int = 1, price: float | None = None):
        order = self.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL, price)
        self.accounting.add_deal_by_order(order)
        self.log(f"SELL MARKET executed, price {self.client.quotation_to_float(order.executed_order_price)}"
                 f" (n={self.accounting.num})")

        return order

    def sell_limit(self, price, lots=1):
        order = self.place_order(
            lots,
            OrderDirection.ORDER_DIRECTION_SELL,
            price=price,
            order_type=OrderType.ORDER_TYPE_LIMIT
        )
        self.active_sell_orders[order.order_id] = order
        return order

    def buy_limit(self, price, lots=1):
        order = self.place_order(
            lots,
            OrderDirection.ORDER_DIRECTION_BUY,
            price=price,
            order_type=OrderType.ORDER_TYPE_LIMIT
        )
        self.active_buy_orders[order.order_id] = order
        return order

    def forecast_next_candle(self, candles):
        if len(candles.candles) < 2:
            return None, None

        # Извлекаем значения high и low из свечей
        high_prices = [candle.high.units + candle.high.nano * 1e-9 for candle in candles.candles]
        low_prices = [candle.low.units + candle.low.nano * 1e-9 for candle in candles.candles]

        # Рассчитываем процентное изменение для high и low
        high_changes = [(high_prices[i] - high_prices[i - 1]) / high_prices[i - 1]
                        if high_prices[i - 1] else 0 for i in range(1, len(high_prices))]
        low_changes = [(low_prices[i] - low_prices[i - 1]) / low_prices[i - 1]
                       if low_prices[i - 1] else 0 for i in range(1, len(low_prices))]

        # Среднее процентное изменение
        avg_high_change = sum(high_changes) / len(high_changes)
        avg_low_change = sum(low_changes) / len(low_changes)

        # Применяем среднее процентное изменение к последним high и low для прогноза
        forecast_high = self.client.round(high_prices[-1] * (1 + avg_high_change))
        forecast_low = self.client.round(low_prices[-1] * (1 + avg_low_change))

        return forecast_low, forecast_high

    def equivalent_prices(self, quotation_price: Quotation | MoneyValue, float_price: float) -> bool:
        rounded_quotation_price = self.client.quotation_to_float(quotation_price)
        rounded_float_price = self.client.round(float_price)
        return rounded_quotation_price == rounded_float_price

    def set_sell_order_by_buy_order(self, order: PostOrderResponse):
        price = self.client.quotation_to_float(order.executed_order_price)
        price += self.step_size  # вот с этим параметром можно поиграть
        self.sell_limit(price)

    def check_and_apply_order_execution(self, order: OrderState | PostOrderResponse) -> bool:
        is_executed, order_state = self.client.order_is_executed(order)

        if is_executed:
            type_text = 'BUY' if order_state.direction == OrderDirection.ORDER_DIRECTION_BUY else 'SELL'
            self.accounting.add_deal_by_order(order_state)
            self.log(f"{type_text} order executed, price {self.client.quotation_to_float(order.executed_order_price)}"
                     f" (n={self.accounting.num})")

        self._remove_order_from_active_list(order)

        return is_executed

    def update_orders_status(self):
        active_order_ids = [order.order_id for order in self.client.get_active_orders()]

        # Обновление заявок на продажу
        for order_id, order in self.active_buy_orders.copy().items():
            if order_id not in active_order_ids:
                if self.check_and_apply_order_execution(order):
                    self.set_sell_order_by_buy_order(order)

        # обновляем список активных, так как список меняется в блоке выше
        active_order_ids = [order.order_id for order in self.client.get_active_orders()]

        # Аналогично для заявок на покупку
        for order_id, order in self.active_sell_orders.copy().items():
            if order_id not in active_order_ids:
                self.check_and_apply_order_execution(order)

    def get_current_price(self) -> float:
        return self.client.current_price

    def place_buy_orders(self):
        current_buy_orders_cnt = len(self.active_buy_orders)
        current_shares_cnt = self.accounting.num
        current_price = math.floor(self.get_current_price() / self.step_size) * self.step_size

        target_prices = [current_price - i * self.step_size for i in range(1, self.step_cnt + 1)]

        # Исключаем цены, по которым уже выставлены заявки на покупку
        existing_order_prices = [self.client.quotation_to_float(order.initial_order_price)
                                 for order_id, order in self.active_buy_orders.items()]

        # Ставим заявки на покупку
        for price in target_prices:
            if current_buy_orders_cnt + current_shares_cnt >= self.max_shares:
                break
            if price in existing_order_prices:
                continue
            self.buy_limit(price)
            current_buy_orders_cnt += 1

    def place_sell_orders(self, count_to_sell):
        current_price = math.ceil(self.get_current_price() / self.step_size) * self.step_size

        target_prices = [current_price + i * self.step_size for i in range(1, count_to_sell + 1)]

        # Ставим заявки на продажу
        for price in sorted(list(target_prices), reverse=True):
            self.sell_limit(price)

    def cancel_active_orders(self):
        """Отменяет все активные заявки."""
        for order_id, order in self.active_buy_orders.copy().items():
            self.cancel_order(order)

        for order_id, order in self.active_sell_orders.copy().items():
            self.cancel_order(order)

    def _remove_order_from_active_list(self, order: PostOrderResponse):
        if order.order_id in self.active_buy_orders:
            del self.active_buy_orders[order.order_id]
        if order.order_id in self.active_sell_orders:
            del self.active_sell_orders[order.order_id]

    def cancel_order(self, order: PostOrderResponse):
        self._remove_order_from_active_list(order)
        self.client.cancel_order(order)
        self.accounting.del_order(order)

    def cancel_orders_by_limits(self):
        # берем текущую цену + сдвиг
        # todo вот тут можно тоже округлить до ближайшего целого
        threshold_price = (self.get_current_price()
                           - self.step_size * self.threshold_buy_steps)

        # перебираем активные заявки на покупку и закрываем всё, что ниже
        for order_id, order in self.active_buy_orders.copy().items():
            order_price = self.client.quotation_to_float(order.initial_order_price)
            if order_price <= threshold_price:
                self.cancel_order(order)

        threshold_price = (self.get_current_price()
                           + self.step_size * self.threshold_sell_steps)

        # перебираем активные заявки на продажу и закрываем всё, что ниже
        for order_id, order in self.active_sell_orders.copy().items():
            order_price = self.client.quotation_to_float(order.initial_order_price)
            if order_price >= threshold_price:
                self.cancel_order(order)
                # todo тест. вместе с отменой заявки продаем по текущей цене
                self.sell()

    def continue_trading(self):
        return self.state != self.STATE_FINISHED

    def run(self):
        while True:
            self.run_iteration()

    def start(self):
        """Начало работы скрипта. первый старт"""

        if self.state != self.STATE_NEW:
            return

        self.state = self.STATE_WORKING

        # получаем текущее число акций
        self.accounting.num = self.accounting.get_instrument_count()

        # должно быть минимум
        need_to_buy = self.base_shares - self.accounting.num

        # докупаем недостающие по рыночной цене
        if need_to_buy > 0:
            for _ in range(need_to_buy):
                self.buy()  # в дальнейшем можно перевести на работу с лотами
            self.place_sell_orders(need_to_buy)

    def run_iteration(self):
        if self.check_stop():
            return

        if not self.can_trade():
            self.log(f"can not trade, sleep {self.sleep_no_trade}")
            self.time.sleep(self.sleep_no_trade)  # Спим, если торговать нельзя
            return

        self.start()

        # Обновляем список активных заявок, тут же заявки на продажу при удачной покупке
        self.update_orders_status()

        # закрываем заявки, которые не входят в лимиты
        self.cancel_orders_by_limits()

        # Выставляем заявки на покупку
        self.place_buy_orders()

        # todo также надо срезать заявки на продажу слишком высоко и выставлять новые по своей логике

        # self.logger.debug(f"Ждем следующего цикла, sleep {self.sleep_trading}")
        self.time.sleep(self.sleep_trading)

    def check_stop(self) -> bool:
        if not self.continue_trading():
            return False

        now = self.time.now()
        end_hour_str, end_min_str = self.end_time.split(':')

        if now.time() >= datetime_time(int(end_hour_str), int(end_min_str)):
            self.stop()
            return True

        return False

    def stop(self):
        if self.state == self.STATE_FINISHED:
            return

        self.state = self.STATE_FINISHED

        self.log("Остановка бота...")
        self.cancel_active_orders()

        # продать откупленные инструменты
        need_to_sell = self.accounting.num - self.base_shares

        if need_to_sell > 0:
            for _ in range(need_to_sell):
                self.sell()

        self.log(f"Итог {round(self.accounting.sum, 2)} {self.client.currency} "
                 f"({round(100 * self.accounting.sum / (self.client.current_price * self.max_shares), 2)}%)")


if __name__ == '__main__':
    bot = ScalpingBot(TOKEN, TICKER)


    def clean(*_args):
        bot.stop()
        sys.exit(0)


    for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
        signal(sig, clean)

    bot.run()
