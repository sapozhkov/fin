import os
import sys
from datetime import time as datetime_time
from signal import *

from dotenv import load_dotenv
from tinkoff.invest import OrderDirection, OrderType, Quotation, MoneyValue

from helper.accounting_helper import AbstractAccountingHelper, AccountingHelper
from helper.logger_helper import LoggerHelper, AbstractLoggerHelper
from helper.time_helper import TimeHelper, AbstractTimeHelper
from helper.tinkoff_client import TinkoffProxyClient, AbstractProxyClient

load_dotenv()

TOKEN = os.getenv("INVEST_TOKEN")
TICKER = 'RNFT'


class ScalpingBot:
    STATE_HAS_0 = 0
    STATE_HAS_1 = 1

    def __init__(
            self, token, ticker,

            profit_steps=5,
            stop_loss_percent=1.0,
            candles_count=4,

            sleep_trading=5 * 60,
            sleep_no_trade=300,
            no_operation_timeout_seconds=300,

            always_sell_koef=0.5,

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

        # конфигурация
        self.commission = 0.0005
        self.profit_steps = profit_steps
        self.stop_loss_percent = stop_loss_percent / 100
        self.always_sell_koef = always_sell_koef / 100

        self.candles_count = candles_count

        self.sleep_trading = sleep_trading
        self.sleep_no_trade = sleep_no_trade
        self.no_operation_timeout_seconds = no_operation_timeout_seconds

        # внутренние переменные
        self.state = self.STATE_HAS_0

        self.last_successful_operation_time = self.time.now()
        self.reset_last_operation_time()

        self.buy_order = None
        self.sell_order = None

        self.log(f"INIT \n"
                 f"     figi - {self.client.figi} ({self.client.ticker})\n"
                 f"     candles_count - {self.candles_count}\n"
                 f"     min profit - {self.profit_steps} steps * {self.client.step_size} = "
                 f"{self.client.round(self.profit_steps * self.client.step_size)} {self.client.currency}\n"
                 f"     stop_loss_percent - {stop_loss_percent} %\n"
                 f"     commission - {self.commission * 100} %\n"
                 f"     no_operation_timeout_seconds - {self.no_operation_timeout_seconds} sec\n"
                 f"     sleep_trading - {self.sleep_trading} sec\n"
                 f"     sleep_no_trade - {self.sleep_no_trade} sec\n"
                 )

    def log(self, message, repeat=False):
        self.logger.log(message, repeat)

    def reset_last_operation_time(self):
        self.last_successful_operation_time = self.time.now()

    def can_trade(self):
        now = self.time.now()

        # Проверка, что сейчас будний день (0 - понедельник, 6 - воскресенье)
        if now.weekday() >= 5:
            return False

        # Проверка, что текущее время между 10:45 и 18:15
        if not (datetime_time(10 - self.time.tmz, 45) <= now.time() <= datetime_time(18 - self.time.tmz, 15)):
            return False

        # Проверка доступности рыночной торговли через API
        if not self.client.can_trade():
            return False

        return True

    def place_order(self, lots: int, operation, price: float | None = None, order_type=OrderType.ORDER_TYPE_MARKET):
        return self.client.place_order(lots, operation, price, order_type)

    def buy(self, lots: int = 1, price: float | None = None):
        return self.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY, price)

    def sell(self, lots: int = 1, price: float | None = None):
        return self.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL, price)

    def sell_limit(self, price, lots=1):
        return self.place_order(
            lots,
            OrderDirection.ORDER_DIRECTION_SELL,
            price=price,
            order_type=OrderType.ORDER_TYPE_LIMIT
        )

    def buy_limit(self, price, lots=1):
        return self.place_order(
            lots,
            OrderDirection.ORDER_DIRECTION_BUY,
            price=price,
            order_type=OrderType.ORDER_TYPE_LIMIT
        )

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

    def change_state_bought(self):
        self.state = self.STATE_HAS_1

    def change_state_sold(self):
        self.state = self.STATE_HAS_0

    def can_buy(self):
        return self.state == self.STATE_HAS_0

    def can_sell(self):
        return self.state == self.STATE_HAS_1

    def cancel_active_orders(self):
        """Отменяет все активные заявки."""
        self.cancel_buy_order()
        self.cancel_sell_order()

    def cancel_buy_order(self):
        if self.buy_order is None:
            return False

        if self.client.cancel_order(self.buy_order):
            self.log(f"Buy order {self.buy_order.order_id}, "
                     f"price={self.client.quotation_to_float(self.buy_order.initial_order_price)} canceled")
        self.buy_order = None

    def cancel_sell_order(self):
        if self.sell_order is None:
            return

        if self.client.cancel_order(self.sell_order):
            self.log(f"Sell order {self.sell_order.order_id}, "
                     f"price={self.client.quotation_to_float(self.sell_order.initial_order_price)} canceled")
        self.sell_order = None

    def check_is_inactive(self):
        """Проверяем на бездействие в течение заданного времени"""
        current_time = self.time.now()
        if ((current_time - self.last_successful_operation_time).total_seconds() >=
                self.no_operation_timeout_seconds):
            self.log(f"{self.no_operation_timeout_seconds / 60} "
                     f"минут без активности. Снимаем и переставляем заявки.")
            return True
        return False

    def equivalent_prices(self, quotation_price: Quotation | MoneyValue, float_price: float) -> bool:
        rounded_quotation_price = self.client.quotation_to_float(quotation_price)
        rounded_float_price = self.client.round(float_price)
        return rounded_quotation_price == rounded_float_price

    def stop(self):
        self.log("Остановка бота...")
        self.cancel_active_orders()

        # продать откупленные инструменты
        if self.state == self.STATE_HAS_1:
            order_status = self.sell()
            self.log(f"SELL order executed, price {self.client.quotation_to_float(order_status.executed_order_price)}")
            self.accounting.add_deal_by_order(order_status)
            self.change_state_sold()
            self.sell_order = None

    def run(self):
        while True:
            self.run_iteration()

    def run_iteration(self):
        if not self.can_trade():
            self.log(f"can not trade, sleep {self.sleep_no_trade}")
            self.time.sleep(self.sleep_no_trade)  # Спим, если торговать нельзя
            print('.', end='')
            return

        # отслеживаем исполнение заявки на покупку
        if self.buy_order:
            order_is_executed, order_status = self.client.order_is_executed(self.buy_order)
            if order_is_executed:
                self.log(f"BUY order executed, price "
                         f"{self.client.quotation_to_float(order_status.executed_order_price)}")
                self.accounting.add_deal_by_order(order_status)
                self.change_state_bought()
                self.buy_order = None
                self.reset_last_operation_time()

        # отслеживаем исполнение заявки на продажу
        if self.sell_order:
            order_is_executed, order_status = self.client.order_is_executed(self.sell_order)
            if order_is_executed:
                self.log(f"SELL order executed, price "
                         f"{self.client.quotation_to_float(order_status.executed_order_price)}")
                self.accounting.add_deal_by_order(order_status)
                self.change_state_sold()
                self.sell_order = None
                self.reset_last_operation_time()

        # сбрасываем заявку на покупку при бездействии
        if self.check_is_inactive() and self.buy_order:
            self.cancel_buy_order()
            self.reset_last_operation_time()

        # прикидываем цены
        last_candles = self.client.fetch_candles(candles_count=self.candles_count)
        forecast_low, forecast_high = self.forecast_next_candle(last_candles)
        if forecast_low is None:
            self.log('Ошибка вычисления прогнозируемого диапазона. Перезапуск алгоритма')
            return

        need_profit = self.client.round(self.profit_steps * self.client.step_size)
        diff = self.client.round(forecast_high - forecast_low)

        # проверяем что есть смысл торговать на таком диапазоне цен
        if diff >= need_profit:

            # эксперимент. сужаем рамки торговли. проверяем будет ли выхлоп по количеству и качеству сделок
            step = 0.1
            if diff - 2 * step >= need_profit:
                self.log(f"Сужаем диапазон на 2 шага")
                forecast_high = self.client.round(forecast_high - step)
                forecast_low = self.client.round(forecast_low + step)

            # можем покупать
            if self.can_buy():
                # есть заявка
                if self.buy_order:
                    # цена отличается - меняем
                    if not self.equivalent_prices(self.buy_order.initial_order_price, forecast_low):
                        self.log(f"Меняем цену покупки на {forecast_low}")
                        self.cancel_buy_order()
                        self.buy_order = self.buy_limit(forecast_low)

                # нет заявки - ставим
                else:
                    self.buy_order = self.buy_limit(forecast_low)
                    if self.buy_order:
                        self.log(f"Размещена заявка на покупку по {forecast_low}")
                    else:
                        self.log(f"НЕ Размещена заявка на покупку по {forecast_low}")

            # можем продавать
            if self.can_sell():
                # есть заявка
                if self.sell_order:
                    # цена отличается - меняем
                    if not self.equivalent_prices(self.sell_order.initial_order_price, forecast_high):
                        self.log(f"Меняем цену продажи на {forecast_high}")
                        self.cancel_sell_order()
                        self.sell_order = self.sell_limit(forecast_high)

                # нет заявки - ставим
                else:
                    self.sell_order = self.sell_limit(forecast_high)
                    if self.sell_order:
                        self.log(f"Размещена заявка на продажу по {forecast_high}")
                    else:
                        self.log(f"НЕ Размещена заявка на продажу по {forecast_high}")

        # если не в диапазоне торговли
        elif self.always_sell_koef:

            # можем продавать
            if self.can_sell():

                base_price = self.accounting.last_buy_price \
                    if self.accounting.last_buy_price else self.client.current_price
                need_sell_price = base_price * (1 + self.always_sell_koef)

                # есть заявка
                if self.sell_order:

                    # цена отличается - меняем
                    if not self.equivalent_prices(self.sell_order.initial_order_price, need_sell_price):
                        self.log(f"Меняем цену продажи (резервная) на {need_sell_price}")
                        self.cancel_sell_order()
                        self.sell_order = self.sell_limit(need_sell_price)

                # нет заявки - ставим
                else:
                    self.sell_order = self.sell_limit(need_sell_price)
                    if self.sell_order:
                        self.log(f"Размещена заявка на продажу (резервная) по {need_sell_price}")
                    else:
                        self.log(f"НЕ Размещена заявка на продажу (резервная) по {need_sell_price}")

        else:
            self.log(f"Пока не торгуем. "
                     f"Ожидаемая разница в торгах - {diff}, а требуется минимум {need_profit} ")

        self.logger.debug(f"Ждем следующего цикла, sleep {self.sleep_trading}")
        self.time.sleep(self.sleep_trading)


if __name__ == '__main__':
    bot = ScalpingBot(TOKEN, TICKER)


    def clean(*_args):
        bot.stop()
        sys.exit(0)


    for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
        signal(sig, clean)

    bot.run()
