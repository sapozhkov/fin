"""
Вторая версия скальпинг бота

Недостатки предыдущей версии:
    1. V продает и тут же покупает обратно за ту же цену - исправлено
    2. ~ редко торгует (раз в час/два) - в процессе

Недостатки этой
    1. готово - раз в 10 минут проводить
    2. готово - сливает деньги за счет того, что не угадывает поведение рынка и продает ниже покупки
            - пробуем сделать анализ на основе 3 последних свечей, а не 5 - не помогает
            - надо корректировать заявки если кажется, что пойдет рост, сейчас сливается за минимальную цену,
                    а потом идет сильный рост, да и слив идет иногда ниже покупки
            - надо учитывать цену покупки? а может и не надо
    3. на подъеме вроде отыгрывала норм, но проверить без фоновых акций
    4. теряет на 4 свечах, если начинает болтать туда-сюда тренд

Задача:
    1. V Имплемент предыдущей
    2. V Учимся покупать внизу, а продавать вверху
    3. V изменяющаяся заявка
    4. -> настроить стоп-лосс и тейк-профит
    5. -> нейронка для угадывания тренда

Логика v2:
    1. состояние анализа
        - смотрим последние свечи и определяем тренд
        - прикидываем низ и верх свечи
        - ставим заявку на покупку по низу и продажу по верху
    2. сохраняем список заявок и периодически проверяем их состояние
    3. крутимся вокруг 1 акции
        - 1 заявка на покупку по низу
        - 1 заявка на продажу по верху
        - 1 акция в наличии
    4. при исполнении заявки выставляем аналогичную повторно в соответствие с прогнозами

Мысли на будущее:
    0. если сильно активный рост, то можно останавливать торговлю
    0. если долго растет, то должен быть разворот. тут нужна нейронка
    0. держать про запас 1 заявку ниже рынка на рубль, чтобы откупать пробои вниз.
        Но это должно скользить от текущей цены.
        Потом что-то с ними делать
    2. сделать отсечку, если сильно падает и уход в сон?

За основу взят алгоритм сгенеренный ChatGPT с доработками логики
"""

import os
import time
from tinkoff.invest import Client, OrderDirection, OrderType, CandleInterval, Quotation, OrderExecutionReportStatus, \
    RequestError, GetCandlesResponse
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from datetime import time as datetime_time
import pytz
import logging
import sqlite3


load_dotenv()

TOKEN = os.getenv("INVEST_TOKEN")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")

# FIGI = 'BBG004730N88'  # SBER
FIGI = 'BBG00F9XX7H4'  # RNFT

logging.getLogger('tinkoff.invest').setLevel(logging.CRITICAL)


class ScalpingBot:
    STATE_HAS_0 = 0
    STATE_HAS_1 = 1

    # profit_percent
    #   0.13 - 0.2
    #   0.19 - 0.3
    #
    def __init__(self, token, figi, account_id, profit_percent=0.13, stop_loss_percent=1.0):
        self.commission = 0.0005
        self.token = token
        self.figi = figi
        self.account_id = account_id
        self.profit_percent = profit_percent / 100
        self.stop_loss_percent = stop_loss_percent / 100
        self.round_signs = 1

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger_last_message = ''

        # self.sleep_no_trade = 60
        # self.sleep_trading = 20
        self.sleep_no_trade = 20
        self.sleep_trading = 10

        self.last_price = None
        self.update_current_price()

        self.last_successful_operation_time = datetime.now(timezone.utc)
        self.reset_last_operation_time()

        self.buy_order = None
        self.sell_order = None

        self.log('INIT')
        self.log(f"FIGI - {self.figi}")

        # пока в нуле
        self.state = self.STATE_HAS_0

        self.db_alg_name = f"{self.figi}_{__file__}"
        self.db_file_name = 'db/trading_bot.db'

        # Создание базы данных
        # Подключение к базе данных (файл будет создан, если не существует)
        # conn = sqlite3.connect('db/trading_bot.db')
        #
        # # Создание курсора
        # cursor = conn.cursor()
        #
        # # Создание таблицы сделок
        # cursor.execute('''
        # CREATE TABLE IF NOT EXISTS deals (
        #     id INTEGER PRIMARY KEY,
        #     algorithm_name TEXT NOT NULL,
        #     type INTEGER NOT NULL,
        #     instrument TEXT NOT NULL,
        #     datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
        #     price REAL NOT NULL,
        #     commission REAL NOT NULL,
        #     total REAL NOT NULL
        # )
        # ''')
        #
        # # Создание индексов
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_instrument_datetime ON deals (instrument, datetime)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_datetime ON deals (datetime)')
        #
        # # Закрытие соединения
        # conn.close()

    def db_add_deal_by_order(self, order):
        price = self.quotation_to_float(order.executed_order_price)
        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            price = -price
        commission = self.quotation_to_float(order.executed_commission, 2)
        self.db_add_deal(
            order.direction,
            price,
            commission,
            round(price - commission, 2)
        )

    def db_add_deal(self, deal_type, price, commission, total):
        conn = sqlite3.connect(self.db_file_name)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO deals (algorithm_name, type, instrument, price, commission, total)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (self.db_alg_name, deal_type, self.figi, price, commission, total))
        conn.commit()
        conn.close()

    def log(self, message, repeat=False):
        if self.logger_last_message != message or repeat:
            self.logger.info(message)
            self.logger_last_message = message
        
    def reset_last_operation_time(self):
        self.last_successful_operation_time = datetime.now(timezone.utc)

    def quotation_to_float(self, quotation, digits=None):
        if digits is None:
            digits = self.round_signs
        return round(quotation.units + quotation.nano * 1e-9, digits)

    def float_to_quotation(self, price) -> Quotation:
        return Quotation(units=int(price), nano=int((self.round(price - int(price))) * 1e9))

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

    def update_current_price(self):
        with Client(self.token) as client:
            # Запрашиваем стакан цен с глубиной 1
            try:
                order_book = client.market_data.get_order_book(figi=self.figi, depth=1)
            except RequestError as e:
                self.logger.error(f"Ошибка при стакана: {e}")
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

    def place_order(self, lots, operation, price=None, order_type=OrderType.ORDER_TYPE_MARKET):
        with Client(self.token) as client:
            price_quotation = self.float_to_quotation(price=price) if price else None
            try:
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
            except RequestError as e:
                self.logger.error(f"Ошибка при выставлении заявки, operation={operation}"
                                  f" price={price}, order_type= {order_type}. ({e})")
                return None

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
            interval_duration_minutes = {
                CandleInterval.CANDLE_INTERVAL_1_MIN: 1,
                CandleInterval.CANDLE_INTERVAL_5_MIN: 5,
                CandleInterval.CANDLE_INTERVAL_15_MIN: 15,
                CandleInterval.CANDLE_INTERVAL_30_MIN: 30,
                CandleInterval.CANDLE_INTERVAL_HOUR: 60,
                CandleInterval.CANDLE_INTERVAL_4_HOUR: 240,
                CandleInterval.CANDLE_INTERVAL_DAY: 1440,
            }

            to_date = datetime.now(timezone.utc)
            minutes_per_candle = interval_duration_minutes[interval]
            from_date = to_date - timedelta(minutes=minutes_per_candle * candles_count)

            try:
                candles = client.market_data.get_candles(
                    figi=self.figi,
                    from_=from_date,
                    to=to_date,
                    interval=interval
                )
                return candles
            except RequestError as e:
                self.logger.error(f"Ошибка при запросе свечей: {e}")
                return GetCandlesResponse([])

    def order_is_executed(self, order):
        with Client(self.token) as client:
            order_state = client.orders.get_order_state(account_id=self.account_id, order_id=order.order_id)
            return (
                order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
                order_state
            )

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
        forecast_high = self.round(high_prices[-1] * (1 + avg_high_change))
        forecast_low = self.round(low_prices[-1] * (1 + avg_low_change))

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
        with Client(self.token) as client:
            if self.buy_order:
                try:
                    client.orders.cancel_order(account_id=self.account_id, order_id=self.buy_order.order_id)
                    self.log(f"Buy order {self.buy_order.order_id}, "
                             f"price={self.quotation_to_float(self.buy_order.initial_order_price)} canceled")
                except RequestError as e:
                    self.logger.error(f"Ошибка при закрытии заявки на покупку: {e}")
                self.buy_order = None

        self.reset_last_operation_time()

    def cancel_sell_order(self):
        with Client(self.token) as client:
            if self.sell_order:
                try:
                    client.orders.cancel_order(account_id=self.account_id, order_id=self.sell_order.order_id)
                    self.log(f"Sell order {self.sell_order.order_id}, "
                             f"price={self.quotation_to_float(self.sell_order.initial_order_price)} canceled")
                except RequestError as e:
                    self.logger.error(f"Ошибка при закрытии заявки на продажу: {e}")
                self.sell_order = None

        self.reset_last_operation_time()

    def check_and_cansel_orders(self):
        """Сбрасываем активные заявки, если не было активных действий за последнее время"""
        no_operation_timeout_seconds = 600  # 10 минут = 600 секунд
        current_time = datetime.now(timezone.utc)
        if (current_time - self.last_successful_operation_time).total_seconds() > no_operation_timeout_seconds:
            self.log(f"{no_operation_timeout_seconds/60} минут без активности. Снимаем и переставляем заявки.")
            self.cancel_active_orders()
            self.reset_last_operation_time()

    def get_instruments_count(self):
        with Client(self.token) as client:
            portfolio = client.operations.get_portfolio(account_id=self.account_id)
            for position in portfolio.positions:
                if position.figi == self.figi:
                    return position.quantity.units
            return 0

    def equivalent_prices(self, quotation_price: Quotation, float_price: float) -> bool:
        # Преобразование Quotation в float
        quotation_to_float = quotation_price.units + quotation_price.nano * 1e-9

        # Округление до одного знака после запятой
        rounded_quotation_price = self.round(quotation_to_float)
        rounded_float_price = self.round(float_price)

        # Сравнение округленных значений
        return rounded_quotation_price == rounded_float_price

    def round(self, price):
        return round(price, self.round_signs)

    def run(self):
        while True:
            if not self.can_trade():
                self.logger.debug(f"can not trade, sleep {self.sleep_no_trade}")
                time.sleep(self.sleep_no_trade)  # Спим, если торговать нельзя
                continue

            # отслеживаем исполнение заявки на покупку
            if self.buy_order:
                order_is_executed, order_status = self.order_is_executed(self.buy_order)
                if order_is_executed:
                    self.log(f"BUY order executed, price {self.quotation_to_float(order_status.executed_order_price)}")
                    self.db_add_deal_by_order(order_status)
                    self.change_state_bought()
                    self.buy_order = None
                    self.reset_last_operation_time()

            # отслеживаем исполнение заявки на продажу
            if self.sell_order:
                order_is_executed, order_status = self.order_is_executed(self.sell_order)
                if order_is_executed:
                    self.log(f"SELL order executed, price {self.quotation_to_float(order_status.initial_order_price)}")
                    self.db_add_deal_by_order(order_status)
                    self.change_state_sold()
                    self.sell_order = None
                    self.reset_last_operation_time()

            # сбрасываем активные заявки, если не было активных действий за последнее время
            self.check_and_cansel_orders()

            # прикидываем цены
            last_candles = self.fetch_candles(candles_count=4)
            forecast_low, forecast_high = self.forecast_next_candle(last_candles)
            if forecast_low is None:
                self.log('Ошибка вычисления прогнозируемого диапазона. Перезапуск алгоритма')
                continue

            # если нет хоть одной заявки
            if not self.buy_order or not self.sell_order:
                need_profit = self.round(self.last_price * self.profit_percent)
                diff = self.round(forecast_high - forecast_low)

                self.update_current_price()

                # проверяем что есть смысл торговать на таком диапазоне цен
                if diff >= need_profit:

                    # эксперимент. сужаем рамки торговли. проверяем будет ли выхлоп по количеству и качеству сделок
                    step = 0.1
                    if diff - 2 * step >= need_profit:
                        self.log(f"Сужаем диапазон на 2 шага")
                        forecast_high = self.round(forecast_high - step)
                        forecast_low = self.round(forecast_low + step)

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

            self.logger.debug(f"Ждем следующего цикла, sleep {self.sleep_no_trade}")
            time.sleep(self.sleep_trading)


bot = ScalpingBot(TOKEN, FIGI, ACCOUNT_ID)
bot.run()
