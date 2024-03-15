import os
import sys
import time
from datetime import datetime, timezone, timedelta
from datetime import time as datetime_time
from signal import *

import pytz
from dotenv import load_dotenv
from tinkoff.invest import OrderDirection, OrderType, CandleInterval, Quotation

from helper.tinkoff_client import TinkoffProxyClient
from helper.database import Database
from helper.logger import LoggerHelper

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
    ):
        self.logger = LoggerHelper(__name__)

        self.client = TinkoffProxyClient(token, ticker, self.logger)

        self.commission = 0.0005
        self.profit_steps = profit_steps
        self.stop_loss_percent = stop_loss_percent / 100

        self.candles_count = candles_count

        self.no_operation_timeout_seconds = 300

        self.sleep_no_trade = 60
        self.sleep_trading = 300

        self.db = Database(__file__, self.client)

        self.last_price = None
        self.update_current_price()
        self.state = self.STATE_HAS_0

        self.last_successful_operation_time = datetime.now(timezone.utc)
        self.reset_last_operation_time()

        self.buy_order = None
        self.sell_order = None

        self.log('INIT')
        self.log(f"FIGI - {self.client.figi} ({self.client.ticker})")

    def log(self, message, repeat=False):
        self.logger.log(message, repeat)
        
    def reset_last_operation_time(self):
        self.last_successful_operation_time = datetime.now(timezone.utc)

    def can_trade(self):
        # Установите часовой пояс, соответствующий рынку, на котором вы торгуете
        market_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(market_tz)

        # Проверка, что сейчас будний день (0 - понедельник, 6 - воскресенье)
        if now.weekday() >= 5:
            return False

        # Проверка, что текущее время между 10:30 и 18:40
        if not (datetime_time(10, 30) <= now.time() <= datetime_time(18, 40)):
            return False

        # Проверка доступности рыночной торговли через API
        if not self.client.can_trade():
            return False

        return True

    def update_current_price(self):
        order_book = self.client.get_order_book()
        if order_book is None:
            self.logger.error(f"Ошибка при запросе стакана")
            return

        # Последняя цена может быть определена как среднее между лучшим предложением покупки и продажи
        if order_book.bids and order_book.asks:
            best_bid = order_book.bids[0].price.units + order_book.bids[0].price.nano * 1e-9
            best_ask = order_book.asks[0].price.units + order_book.asks[0].price.nano * 1e-9
            current_price = (best_bid + best_ask) / 2
        else:
            current_price = None  # В случае отсутствия данных в стакане

        if current_price:
            self.last_price = current_price

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

    # Базовая функция для загрузки данных последних свечей
    def fetch_candles(self, interval=CandleInterval.CANDLE_INTERVAL_5_MIN, candles_count=5):
        to_date = datetime.now(timezone.utc)
        minutes_per_candle = self.client.interval_duration_minutes[interval]
        from_date = to_date - timedelta(minutes=minutes_per_candle * candles_count)

        return self.client.get_candles(from_date, to_date, interval)

    def forecast_next_candle(self, candles):
        if len(candles.candles) < 2:
            return None, None

        # Извлекаем значения high и low из свечей
        high_prices = [candle.high.units + candle.high.nano * 1e-9 for candle in candles.candles]
        low_prices = [candle.low.units + candle.low.nano * 1e-9 for candle in candles.candles]

        # Рассчитываем процентное изменение для high и low
        high_changes = [(high_prices[i] - high_prices[i - 1]) / high_prices[i - 1] for i in range(1, len(high_prices))]
        low_changes = [(low_prices[i] - low_prices[i - 1]) / low_prices[i - 1] for i in range(1, len(low_prices))]

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

        self.reset_last_operation_time()

    def cancel_sell_order(self):
        if self.sell_order is None:
            return

        if self.client.cancel_order(self.sell_order):
            self.log(f"Sell order {self.sell_order.order_id}, "
                     f"price={self.client.quotation_to_float(self.sell_order.initial_order_price)} canceled")
        self.sell_order = None

        self.reset_last_operation_time()

    def check_and_cansel_orders(self):
        """Сбрасываем активные заявки, если не было активных действий за последнее время"""
        current_time = datetime.now(timezone.utc)
        if ((current_time - self.last_successful_operation_time).total_seconds() >=
                self.no_operation_timeout_seconds):
            self.log(f"{self.no_operation_timeout_seconds/60} "
                     f"минут без активности. Снимаем и переставляем заявки.")
            self.cancel_active_orders()
            self.reset_last_operation_time()

    def equivalent_prices(self, quotation_price: Quotation, float_price: float) -> bool:
        # Преобразование Quotation в float
        quotation_to_float = quotation_price.units + quotation_price.nano * 1e-9

        # Округление до одного знака после запятой
        rounded_quotation_price = self.client.round(quotation_to_float)
        rounded_float_price = self.client.round(float_price)

        # Сравнение округленных значений
        return rounded_quotation_price == rounded_float_price

    def stop(self):
        self.log("Остановка бота...")
        self.cancel_active_orders()

        # продать откупленные инструменты
        if self.state == self.STATE_HAS_1:
            order_status = self.sell()
            self.log(f"SELL order executed, price {self.client.quotation_to_float(order_status.executed_order_price)}")
            self.db.add_deal_by_order(order_status)
            self.change_state_sold()
            self.sell_order = None

    def run(self):
        while True:
            if not self.can_trade():
                self.log(f"can not trade, sleep {self.sleep_no_trade}")
                time.sleep(self.sleep_no_trade)  # Спим, если торговать нельзя
                print('.', end='')
                continue

            # отслеживаем исполнение заявки на покупку
            if self.buy_order:
                order_is_executed, order_status = self.client.order_is_executed(self.buy_order)
                if order_is_executed:
                    self.log(f"BUY order executed, price "
                             f"{self.client.quotation_to_float(order_status.executed_order_price)}")
                    self.db.add_deal_by_order(order_status)
                    self.change_state_bought()
                    self.buy_order = None
                    self.reset_last_operation_time()

            # отслеживаем исполнение заявки на продажу
            if self.sell_order:
                order_is_executed, order_status = self.client.order_is_executed(self.sell_order)
                if order_is_executed:
                    self.log(f"SELL order executed, price "
                             f"{self.client.quotation_to_float(order_status.executed_order_price)}")
                    self.db.add_deal_by_order(order_status)
                    self.change_state_sold()
                    self.sell_order = None
                    self.reset_last_operation_time()

            # сбрасываем активные заявки, если не было активных действий за последнее время
            self.check_and_cansel_orders()

            # прикидываем цены
            last_candles = self.fetch_candles(candles_count=self.candles_count)
            forecast_low, forecast_high = self.forecast_next_candle(last_candles)
            if forecast_low is None:
                self.log('Ошибка вычисления прогнозируемого диапазона. Перезапуск алгоритма')
                continue

            need_profit = self.client.round(self.profit_steps * self.client.step_size)
            diff = self.client.round(forecast_high - forecast_low)

            self.update_current_price()

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

            else:
                self.log(f"Пока не торгуем. "
                         f"Ожидаемая разница в торгах - {diff}, а требуется минимум {need_profit} ")

            self.logger.debug(f"Ждем следующего цикла, sleep {self.sleep_trading}")
            time.sleep(self.sleep_trading)


if __name__ == '__main__':
    bot = ScalpingBot(TOKEN, TICKER)

    def clean(*_args):
        bot.stop()
        sys.exit(0)

    for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
        signal(sig, clean)

    bot.run()
