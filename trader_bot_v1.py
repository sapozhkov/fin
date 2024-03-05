"""
Первая версия скальпинг бота

Задача: Обкатать технологию. Проверить, что механизм в принципе работает.

За основу взят алгоритм сгенеренный ChatGPT с доработками логики

Недостатки:
    1. редко торгует (раз в час/два)
    2. продает и тут же покупает обратно за ту же цену

Логика:
    1. смотрим каких заявок больше
    2. если покупателей, то
        2.1 покупаем сами
        2.2 выставляем лимитную заявку на продажу чуть дороже (комиссия + небольшой %)
        2.3 после продажи идем к п.1
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
    def __init__(self, token, figi, account_id, profit_percent=0.15, stop_loss_percent=1.0):
        self.commission = 0.0005
        self.token = token
        self.figi = figi
        self.account_id = account_id
        self.profit_percent = profit_percent / 100
        self.stop_loss_percent = stop_loss_percent / 100

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

    def analyze_order_book(self):
        order_book = self.fetch_order_book()

        self.update_values(order_book)

        spread = self.analyze_spread(order_book)
        market_side = self.analyze_market_side(order_book)

        self.logger.debug(f"market side - {market_side} ||| "
                          f"sel{self.side_sellers} buy{self.side_buyers} bal{self.side_balanced}")

        # Здесь можно добавить дополнительную логику на основе анализа
        # Например, принимать решение о покупке, если спред узкий и доминируют покупатели
        # todo spread and spread <= self.desired_spread and
        if market_side == "buyers":
            self.logger.debug(f"можно покупать")
            return True  # Сигнал к покупке
        else:
            self.logger.debug(f"не надо пока покупать")
            # todo а может надо продавать
            return False  # Ожидание лучшего момента для входа

    def check_market_growth(self):
        # todo Проверка, вырастет ли рынок
        #   это место под нейронку
        return True

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

    def sell_is_executed(self, sell_order):
        with Client(self.token) as client:
            order_state = client.orders.get_order_state(account_id=self.account_id, order_id=sell_order.order_id)
            return order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL

    def run(self):

        self.logger.info('INIT')

        while True:
            if not self.can_trade():
                self.logger.debug(f"can not trade, sleep {self.sleep_no_trade}")
                time.sleep(self.sleep_no_trade)  # Спим, если торговать нельзя
                continue

            # если есть покупка
            if self.buy_order:
                self.logger.debug(f"куплено. ждем пока вырастет")

                # если ушла ниже нижнего порога, то продаем как есть

                # проверяем что с заявкой на продажу
                # если продано - продолжаем
                if self.sell_is_executed(self.sell_order):
                    self.logger.debug(f"ПРОДАНО, все норм, продолжаем")
                    self.buy_order = None
                    self.sell_order = None

                # если еще не исполнена, то ждем
                else:
                    time.sleep(self.sleep_trading)
                    continue

            self.analyze_order_book()

            if self.check_market_growth():

                # todo buy_price = self.place_order(OrderDirection.ORDER_DIRECTION_BUY, lots=1)
                buy_price = self.last_price

                sell_price = self.last_price * (1 + self.profit_percent)
                stop_loss_price = self.last_price * (1 - self.stop_loss_percent)
                get_max_recent_price = self.get_max_recent_price()
                get_min_recent_price = self.get_min_recent_price()

                # Покупаем 1 лот
                self.buy_order = self.buy()
                # executed_order_price

                # Ставим лимитную заявку на продажу
                self.sell_order = self.sell_limit(sell_price)

                # todo покупаем за лучшую цену
                # todo выставляем заявку на продажу
                # todo сохраняем id заявки, чтобы по ней слить
                # todo выставляем стоп лосс если получается на ту же заявку. если не получится, то трекаем каждый заход
                # todo пока висят заявки не продаем

                # todo надо понимать, что мы купили и не докупать еще пока не продадим

                if sell_price < get_max_recent_price:
                    self.logger.debug('вроде можно покупать')
                    self.logger.debug(f"берем за {self.last_price}")
                    self.logger.debug(f"пытаемся продать за {sell_price}")
                    self.logger.debug(f"цена поднималась до  {get_max_recent_price} за последнее время")
                    self.logger.debug(f"сливаемся если падает в  {stop_loss_price}")
                else:
                    self.logger.debug('!!!!! не покупаем - не отрастет')
                    self.logger.debug(f"берем за {self.last_price}")
                    self.logger.debug(f"пытаемся продать за {sell_price}")
                    self.logger.debug(f"цена поднималась до  {get_max_recent_price} за последнее время")

                # Проверка условий для снятия заявки или продажи
                # Это упрощенный пример, вам нужно будет реализовать логику проверки

                self.logger.debug(f"отторговали, ждем следующего цикла, sleep {self.sleep_no_trade}")
                time.sleep(self.sleep_trading)  # Спим, если рынок не вырастет
            else:
                self.logger.debug(f"падающий рынок, не торгуем, sleep {self.sleep_no_trade}")
                time.sleep(self.sleep_no_trade)  # Спим, если рынок не вырастет


bot = ScalpingBot(TOKEN, FIGI, ACCOUNT_ID)
bot.run()
