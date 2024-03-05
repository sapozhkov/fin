"""
Вторая версия скальпинг бота

Недостатки предыдущей версии:
    1. продает и тут же покупает обратно за ту же цену
    2. редко торгует (раз в час/два)

Задача:
    1. Имплемент предыдущей
    2. Учимся покупать внизу, а продавать вверху

Логика v2:
    1. состояние анализа
        - смотрим последние свечи и определяем тренд
        - прикидываем низ и верх свечи
        - ставим заявку на покупку по низу и продажу по верху
    2. сохраняем список заявок и периодически проверяем их состояние
    3. крутимся вокруг 1 акции
        - 1 заявка на покупку по низу
        - 1 заявка на продажу по верху
        - 1 акция в наличии пока в ручном режиме
    4. при исполнении заявки выставляем аналогичную повторно в соответствие с прогнозами

Мысли на будущее:
    0. смещаем заявку, если ориентировочная цена ушла, а сделка долго висит
    1. сделать 1 купленную акцию в базе (тогда можно её продать, как шорт, но без мажоритарной торговли)
        в итоге в зависимости от состояния рынка можно получать доход
        максимум 2 акции
            0 - всё продано, ждем откупа назад
            1 - одна лежит на балансе
            2 - балансная + купленная. Ждем продажи
    2. сделать отсечку, если сильно падает и уход в сон?
    3. ожидаем N минут и меняем стратегию, если ничего не происходит
        - хотим купить внизу, а туда уже не упадем
        - хотим продать вверху, а скатились вниз
        тогда фиксируем убыток и начинаем заново

За основу взят алгоритм сгенеренный ChatGPT с доработками логики
"""

import os
import time
from tinkoff.invest import Client, OrderDirection, OrderType, CandleInterval, Quotation, OrderExecutionReportStatus
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from datetime import time as datetime_time
import pytz
import logging


load_dotenv()

TOKEN = os.getenv("INVEST_TOKEN")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")

# FIGI = 'BBG004730N88'  # SBER
FIGI = 'BBG00F9XX7H4'  # RNFT


class ScalpingBot:
    STATE_HAS_0 = 0
    STATE_HAS_1 = 1
    STATE_HAS_2 = 2

    def __init__(self, token, figi, account_id, profit_percent=0.15, stop_loss_percent=1.0):
        self.commission = 0.0005
        self.token = token
        self.figi = figi
        self.account_id = account_id
        self.profit_percent = profit_percent / 100
        self.stop_loss_percent = stop_loss_percent / 100

        self.state = self.STATE_HAS_1

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

        # self.sleep_no_trade = 60
        # self.sleep_trading = 20
        self.sleep_no_trade = 20
        self.sleep_trading = 10

        order_book = self.fetch_order_book()

        self.last_price = self.quotation_to_float(order_book.last_price)
        self.desired_spread = self.last_price * 0.001  # todo подумать. это было на глаз сделано

        self.side_buyers = 0
        self.side_sellers = 0
        self.side_balanced = 0

        self.buy_order = None
        self.sell_order = None

        self.logger.info(f"FIGI - {self.figi}")
        self.logger.debug(f"desired_spread - {self.desired_spread}")

    @staticmethod
    def quotation_to_float(quotation):
        return quotation.units + quotation.nano * 1e-9

    @staticmethod
    def float_to_quotation(price) -> Quotation:
        return Quotation(units=int(price), nano=int((round(price - int(price), 1)) * 1e9))

    @staticmethod
    def can_trade():
        # Установите часовой пояс, соответствующий рынку, на котором вы торгуете
        market_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(market_tz)

        # Проверка, что сейчас будний день (0 - понедельник, 6 - воскресенье)
        if now.weekday() >= 5:
            return False

        # Проверка, что текущее время между 10:00 и 19:00
        if not (datetime_time(10, 0) <= now.time() <= datetime_time(18, 40)):
            return False

        # todo дописать. где-то был как раз нужный код
        # Здесь добавьте логику проверки доступности торговли через API
        # Это будет зависеть от API, которое вы используете
        # Пример:
        # return self.check_market_status_via_api()

        return True

    def fetch_order_book(self):
        with Client(self.token) as client:
            order_book = client.market_data.get_order_book(figi=self.figi, depth=10)
        return order_book

    def update_values(self, order_book):
        self.last_price = self.quotation_to_float(order_book.last_price)

    def analyze_spread(self, order_book):
        if not (order_book.asks and order_book.bids):
            return None
        best_ask = order_book.asks[0].price  # Лучшая цена продажи
        best_bid = order_book.bids[0].price  # Лучшая цена покупки
        spread = best_ask - best_bid
        self.logger.debug(f"Spread {spread}")
        return spread

    def analyze_market_side(self, order_book):
        total_bid_volume = sum([bid.quantity for bid in order_book.bids])
        total_ask_volume = sum([ask.quantity for ask in order_book.asks])

        if total_bid_volume > total_ask_volume:
            self.side_buyers += 1
            return "buyers"
        elif total_bid_volume < total_ask_volume:
            self.side_sellers += 1
            return "sellers"
        else:
            self.side_balanced += 1
            return "balanced"

    def place_order(self, lots, operation, price=None, order_type=OrderType.ORDER_TYPE_MARKET):
        with Client(self.token) as client:
            price_quotation = self.float_to_quotation(price=price) if price else None
            order_response = client.orders.post_order(
                order_id=str(datetime.now(timezone.utc)),
                figi=self.figi,
                quantity=lots,
                direction=operation,
                account_id=ACCOUNT_ID,
                order_type=order_type,
                price=price_quotation
            )
            return order_response

    def buy(self, lots=1, price=None):
        return self.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY, price)

    def sell(self, lots=1, price=None):
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
        with Client(self.token) as client:
            to_date = datetime.now(timezone.utc)
            from_date = to_date - timedelta(minutes=interval.value * candles_count)

            candles = client.market_data.get_candles(
                figi=self.figi,
                from_=from_date,
                to=to_date,
                interval=interval
            )
        return candles

    # Функция для получения максимальной цены
    def get_max_recent_price(self, interval=CandleInterval.CANDLE_INTERVAL_5_MIN, candles_count=5):
        candles = self.fetch_candles(interval, candles_count)
        max_price = max(candle.high.units + candle.high.nano * 1e-9 for candle in candles.candles)
        return max_price

    # Функция для получения минимальной цены
    def get_min_recent_price(self, interval=CandleInterval.CANDLE_INTERVAL_5_MIN, candles_count=5):
        candles = self.fetch_candles(interval, candles_count)
        min_price = min(candle.low.units + candle.low.nano * 1e-9 for candle in candles.candles)
        return min_price

    def order_is_executed(self, order):
        with Client(self.token) as client:
            order_state = client.orders.get_order_state(account_id=self.account_id, order_id=order.order_id)
            return order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL

    @staticmethod
    def forecast_next_candle(candles):
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
        forecast_high = high_prices[-1] * (1 + avg_high_change)
        forecast_low = low_prices[-1] * (1 + avg_low_change)

        return forecast_low, forecast_high

    def run(self):

        self.logger.info('INIT')

        while True:
            if not self.can_trade():
                self.logger.debug(f"can not trade, sleep {self.sleep_no_trade}")
                time.sleep(self.sleep_no_trade)  # Спим, если торговать нельзя
                continue

            # отслеживаем исполнение заявки на покупку
            if self.buy_order and self.order_is_executed(self.buy_order):
                # todo вот это можно обновить и взять актуальную цену продажу
                self.logger.info(f"BUY order executed, price {self.buy_order.initial_order_price}")
                self.change_state_bought()
                self.buy_order = None

            # отслеживаем исполнение заявки на продажу
            if self.sell_order and self.order_is_executed(self.sell_order):
                # todo вот это можно обновить и взять актуальную цену продажу
                self.logger.info(f"SELL order executed, price {self.sell_order.initial_order_price}")
                self.change_state_sold()
                self.sell_order = None

            # если нет хоть одной заявки
            if not self.buy_order or not self.sell_order:

                # прикидываем цены
                last_candles = self.fetch_candles()
                forecast_low, forecast_high = self.forecast_next_candle(last_candles)

                if not self.buy_order and self.can_buy():
                    self.logger.debug(f"Заявка на покупку по  {forecast_low}")
                    self.buy_order = self.buy_limit(forecast_low)

                if not self.sell_order and self.can_sell():
                    self.logger.debug(f"Заявка на продажу по  {forecast_high}")
                    self.sell_order = self.sell_limit(forecast_high)

            self.logger.debug(f"отторговали, ждем следующего цикла, sleep {self.sleep_no_trade}")
            time.sleep(self.sleep_trading)

    def change_state_bought(self):
        self.state = min(self.STATE_HAS_2, self.state + 1)

    def change_state_sold(self):
        self.state = max(self.STATE_HAS_0, self.state - 1)

    def can_buy(self):
        return self.state != self.STATE_HAS_2

    def can_sell(self):
        return self.state != self.STATE_HAS_0


bot = ScalpingBot(TOKEN, FIGI, ACCOUNT_ID)
bot.run()
