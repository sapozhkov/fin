"""
Вторая версия скальпинг бота

Недостатки предыдущей версии:
    1. V продает и тут же покупает обратно за ту же цену - исправлено
    2. ~ редко торгует (раз в час/два) - в процессе

Недостатки этой
    1. раз в 10 минут проводить
    2. сливает деньги за счет того, что не угадывает поведение рынка и продает ниже покупки
            - пробуем сделать анализ на основе 3 последних свечей, а не 5 - не помогает
            - надо корректировать заявки если кажется, что пойдет рост, сейчас сливается за минимальную цену,
                    а потом идет сильный рост, да и слив идет иногда ниже покупки
            - надо учитывать цену покупки? а может и не надо

Задача:
    1. V Имплемент предыдущей
    2. 0 Учимся покупать внизу, а продавать вверху

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
    0. держать про запас 1 заявку ниже рынка на рубль, чтобы откупать пробои вниз.
        Но это должно скользить от текущей цены.
        Потом что-то с ними делать
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
from tinkoff.invest import Client, OrderDirection, OrderType, CandleInterval, Quotation, OrderExecutionReportStatus, \
    RequestError, GetCandlesResponse
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

logging.getLogger('tinkoff.invest').setLevel(logging.CRITICAL)


class ScalpingBot:
    STATE_HAS_0 = 0
    STATE_HAS_1 = 1
    STATE_HAS_2 = 2

    def __init__(self, token, figi, account_id, profit_percent=0.13, stop_loss_percent=1.0):
        self.commission = 0.0005
        self.token = token
        self.figi = figi
        self.account_id = account_id
        self.profit_percent = profit_percent / 100
        self.stop_loss_percent = stop_loss_percent / 100

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

        # plt.ion()  # Включаем интерактивный режим
        # self.figure, self.ax = plt.subplots()

        self.log('INIT')
        self.log(f"FIGI - {self.figi}")

        # в пуле должна быть 1 акция
        # todo можно автоматически откупать при отсечке бездействия, но, кажется, это приведет только к потерям
        #   надо протестировать, может и 1 в пуле тоже не очень хорошо и начинать надо всегда снизу
        if self.get_instruments_count() == 0:
            self.buy()
            self.log('Покупаем первую акцию в пул')
        self.state = self.STATE_HAS_1

    def log(self, message, repeat=False):
        if self.logger_last_message != message or repeat:
            self.logger.info(message)
            self.logger_last_message = message
        
    def reset_last_operation_time(self):
        self.last_successful_operation_time = datetime.now(timezone.utc)

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
            return order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL

    @staticmethod
    def forecast_next_candle(candles):
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
        forecast_high = round(high_prices[-1] * (1 + avg_high_change), 2)
        forecast_low = round(low_prices[-1] * (1 + avg_low_change), 2)

        return forecast_low, forecast_high

    def change_state_bought(self):
        self.state = min(self.STATE_HAS_2, self.state + 1)

    def change_state_sold(self):
        self.state = max(self.STATE_HAS_0, self.state - 1)

    def can_buy(self):
        return self.state != self.STATE_HAS_2

    def can_sell(self):
        return self.state != self.STATE_HAS_0

    def cancel_active_orders(self):
        """Отменяет все активные заявки."""
        with Client(self.token) as client:
            if self.buy_order:
                client.orders.cancel_order(account_id=self.account_id, order_id=self.buy_order.order_id)
                self.log(f"Buy order {self.buy_order.order_id}, price={self.buy_order.initial_order_price} canceled")
                self.buy_order = None

            if self.sell_order:
                client.orders.cancel_order(account_id=self.account_id, order_id=self.sell_order.order_id)
                self.log(f"Sell order {self.sell_order.order_id}, price={self.sell_order.initial_order_price} canceled")
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

    def run(self):
        while True:
            if not self.can_trade():
                self.logger.debug(f"can not trade, sleep {self.sleep_no_trade}")
                time.sleep(self.sleep_no_trade)  # Спим, если торговать нельзя
                continue

            # отслеживаем исполнение заявки на покупку
            if self.buy_order and self.order_is_executed(self.buy_order):
                # todo вот это можно обновить и взять актуальную цену продажу
                self.log(f"BUY order executed, price {self.buy_order.initial_order_price}")
                self.change_state_bought()
                self.buy_order = None
                self.reset_last_operation_time()

            # отслеживаем исполнение заявки на продажу
            if self.sell_order and self.order_is_executed(self.sell_order):
                # todo вот это можно обновить и взять актуальную цену продажу
                self.log(f"SELL order executed, price {self.sell_order.initial_order_price}")
                self.change_state_sold()
                self.sell_order = None
                self.reset_last_operation_time()

            # сбрасываем активные заявки, если не было активных действий за последнее время
            self.check_and_cansel_orders()

            # прикидываем цены
            last_candles = self.fetch_candles(candles_count=3)
            forecast_low, forecast_high = self.forecast_next_candle(last_candles)
            if forecast_low is None:
                self.log('Ошибка вычисления прогнозируемого диапазона. Перезапуск алгоритма')
                continue

            # если нет хоть одной заявки
            if not self.buy_order or not self.sell_order:
                need_profit = round(self.last_price * self.profit_percent, 1)

                diff = round(forecast_high - forecast_low, 2)

                self.update_current_price()

                # проверяем что есть смысл торговать на таком диапазоне цен
                if diff >= need_profit:

                    # todo эксперимент. сужаем рамки торговли. проверяем будет ли выхлоп по количеству и качеству сделок
                    step = 0.1
                    if diff - 2 * step >= need_profit:
                        self.log(f"Сужаем диапазон на 2 шага")
                        forecast_high -= step
                        forecast_low += step

                    if not self.buy_order and self.can_buy():
                        self.buy_order = self.buy_limit(forecast_low)
                        if self.buy_order:
                            self.log(f"Размещена заявка на покупку по {forecast_low}")
                        else:
                            self.log(f"НЕ Размещена заявка на покупку по {forecast_low}")

                    if not self.sell_order and self.can_sell():
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
