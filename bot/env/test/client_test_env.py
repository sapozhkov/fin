from datetime import time as datetime_time, timedelta, datetime
from typing import Tuple

from tinkoff.invest import HistoricCandle, PostOrderResponse, MoneyValue, OrderType, GetCandlesResponse, OrderState, \
    OrderDirection, OrderExecutionReportStatus

from bot.env import AbstractProxyClient
from bot.env.test import TimeTestEnvHelper
from common.helper import TimeHelper


class ClientTestEnvHelper(AbstractProxyClient):
    START_TIME = '07:00'
    END_TIME = '15:29'

    def __init__(self,
                 token,
                 ticker,
                 logger,
                 time_helper: TimeTestEnvHelper,
                 ):
        super().__init__(token, ticker, time_helper, logger)

        self.candles_1_min_dict: dict = {}
        self.total_completed_orders = 0

        self.current_candle: HistoricCandle | None = None
        self.current_price: float = 0
        self.commission: float = 0.0005

        self.order_next_index = 0
        self.orders: dict[str, PostOrderResponse] = {}
        self.executed_orders_ids = []

    def set_current_price(self, price: float):
        self.current_price = price

    def get_current_price(self):
        return self.current_price

    def set_candles_list_by_date(self, date):
        is_today = TimeHelper.is_today(date)
        is_evening = TimeHelper.is_evening()

        candles = self.ticker_cache.get_candles(date, force_cache=is_today and is_evening)
        self.candles_1_min_dict = {(candle.time.hour, candle.time.minute): candle for candle in candles.candles}
        self.orders = {}
        self.executed_orders_ids = []

        return is_today or len(candles.candles) > 400  # в реальной дате > 500. это флаг отсутствия данных

    def set_current_candle(self, candle: HistoricCandle):
        self.current_candle = candle
        self.set_current_price(self.quotation_to_float(candle.close))

    def get_candle(self, dt) -> HistoricCandle | None:
        return self.candles_1_min_dict.get((dt.hour, dt.minute), None)

    @staticmethod
    def to_time(str_time) -> datetime_time:
        hours, minutes = map(int, str_time.split(':'))
        return datetime_time(hours, minutes)

    def can_trade(self):
        return TimeHelper.is_working_hours(self.time.now())

    def float_to_money_value(self, price) -> MoneyValue:
        return MoneyValue(self.instrument.currency, units=int(price), nano=int((self.round(price - int(price))) * 1e9))

    def get_new_order_id(self):
        self.order_next_index += 1
        return str(self.order_next_index)

    def place_order(self, lots: int, direction, price: float | None,
                    order_type=OrderType.ORDER_TYPE_MARKET) -> PostOrderResponse | None:

        # if random.randint(1, 3) == 1:
        #     print('----- Падение запроса ------')
        #     return None

        # покупка по рыночной цене
        if order_type == OrderType.ORDER_TYPE_MARKET:
            # считаем сразу исполненной по указанной цене минус комиссия
            return self.get_post_order_response_market(direction, lots)

        # иначе лимитная заявка
        elif order_type == OrderType.ORDER_TYPE_LIMIT:
            order = self.get_post_order_response_limit(direction, lots, price)
            self.orders[order.order_id] = order
            return order

        else:
            raise f"Unknown order_type: {order_type}"

    def get_candles(self, from_date, to_date, interval) -> GetCandlesResponse:
        interval_min = self.interval_duration_minutes[interval]
        ask_time_list = self.get_interval_time_list(from_date, to_date, interval_min)
        candles = []
        for hour, minute in ask_time_list:
            candles.append(self.get_calculated_candle(hour, minute, interval_min))
        return GetCandlesResponse(candles)

    def get_day_candles(self, from_date, to_date) -> GetCandlesResponse:
        return self.ticker_cache.get_day_candles(from_date, to_date)

    @staticmethod
    def get_interval_time_list(from_date, to_date, interval):
        # Округление from_date до ближайшего интервала в прошлом
        total_minutes_from = from_date.hour * 60 + from_date.minute
        rounded_minutes_from = total_minutes_from - (total_minutes_from % interval)

        # Создание новой начальной даты с округленным временем
        rounded_from_date = from_date.replace(hour=rounded_minutes_from // 60, minute=rounded_minutes_from % 60,
                                              second=0, microsecond=0)

        # Инициализация списка для хранения результатов
        result = []

        # Итерация от округленного начального времени до конечного времени с шагом, равным интервалу
        current_time = rounded_from_date
        while current_time <= to_date:
            result.append((current_time.hour, current_time.minute))
            current_time += timedelta(minutes=interval)

        return result

    @staticmethod
    def get_n_minutes(h, m, n):
        specified_time = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        prev_minutes = []

        # Вычитаем минуты и добавляем результат в список
        for i in range(n):
            previous_time = specified_time + timedelta(minutes=i)
            prev_minutes.append((previous_time.hour, previous_time.minute))

        return prev_minutes

    @staticmethod
    def time_is_greater(time_pair, current_datetime):
        """
        Проверяет, больше ли или равно заданное время (час и минута) текущему времени.

        :param time_pair: Кортеж, содержащий час и минуту (например, (14, 30)).
        :param current_datetime: Объект datetime с текущим временем.
        :return: True, если заданное время больше или равно текущему, иначе False.
        """
        hour, minute = time_pair
        # Создаем объект datetime для заданного времени с использованием даты из current_datetime
        given_datetime = current_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)

        return given_datetime > current_datetime

    def get_calculated_candle(self, hour, minute, n=5) -> HistoricCandle:
        """
        Отдает свечи, рассчитанные на основе минутных, но только нва текущий день
        (данные собираются из массива self.candles_1_min_dict)
        :param hour: час
        :param minute: минута
        :param n: интервал (минут)
        :return: HistoricCandle
        """
        previous_minutes = self.get_n_minutes(hour, minute, n)

        open_ = None
        high = 0
        low = 1000000000
        close = self.float_to_quotation(0)
        volume = 0
        is_complete = True

        now = self.time.now()

        for time_pair in previous_minutes:
            t1: HistoricCandle | None = self.candles_1_min_dict.get(time_pair, None)
            if t1 is None:
                continue
            if self.time_is_greater(time_pair, now):
                is_complete = False
                continue
            if open_ is None:
                open_ = t1.open
            high = max(high, self.quotation_to_float(t1.high))
            low = min(low, self.quotation_to_float(t1.low))
            close = t1.close
            volume += t1.volume

        if open_ is None:
            open_ = self.float_to_quotation(0)

        return HistoricCandle(
            high=self.float_to_quotation(high),
            low=self.float_to_quotation(low),
            open=open_,
            close=close,
            volume=volume,
            time=datetime(now.year, now.month, now.day, hour, minute),
            is_complete=is_complete,
        )

    def order_is_executed(self, order: PostOrderResponse) -> Tuple[bool, OrderState | None]:

        # покупка по рыночной цене
        if order.order_type == OrderType.ORDER_TYPE_MARKET:
            # считаем сразу исполненной по указанной цене минус комиссия
            return (
                True,
                self.get_order_state(order)
            )

        # иначе лимитная заявка
        elif order.order_type == OrderType.ORDER_TYPE_LIMIT:
            res = False

            if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
                if order.order_id in self.executed_orders_ids:
                    res = True
                    self.total_completed_orders += 1

            elif order.direction == OrderDirection.ORDER_DIRECTION_SELL:
                if order.order_id in self.executed_orders_ids:
                    res = True
                    self.total_completed_orders += 1

            return (
                res,
                self.get_order_state(order)
            )

        else:
            raise f"Unknown order_type: {order.order_type}"

    def get_instruments_count(self):
        raise 'Not implemented'

    def cancel_order(self, order) -> bool:
        if order.order_id in self.orders:
            del self.orders[order.order_id]
            return True
        return False

    def get_active_orders(self):
        return [order for order_id, order in self.orders.items() if order_id not in self.executed_orders_ids]

    def get_post_order_response_market(self, direction, lots, ):
        # Реальный ответ от официального клиента на
        # 2 лота по 243.5 руб
        # PostOrderResponse(
        #     order_id='46100948036',
        #     execution_report_status= < OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL: 1 >,
        #     lots_requested = 2,
        #     lots_executed = 2,
        #     initial_order_price = MoneyValue(currency='rub', units=470, nano=600000000),
        #     executed_order_price = MoneyValue(currency='rub', units=234, nano=500000000),
        #     total_order_amount = MoneyValue(currency='rub', units=469, nano=0),
        #     initial_commission = MoneyValue(currency='rub', units=0, nano=240000000), - на все инструменты
        #     executed_commission = MoneyValue(currency='rub', units=0, nano=0), - вот тут почему-то нули
        #     aci_value = MoneyValue(currency='', units=0, nano=0),
        #     figi = 'BBG00F9XX7H4',
        #     direction = < OrderDirection.ORDER_DIRECTION_BUY: 1 >,
        #     initial_security_price = MoneyValue(currency='rub', units=235, nano=300000000),
        #     order_type = < OrderType.ORDER_TYPE_MARKET: 2 >,
        #     message = '',
        #     initial_order_price_pt = Quotation(units=0, nano=0),
        #     instrument_uid = 'c74855***********************a202904',
        #     order_request_id = '2024-04-22 13:37:55.118713+00:00',
        #     response_metadata = ResponseMetadata(
        #       tracking_id='d680***********************4220a',
        #       server_time=datetime.datetime(2024, 4, 22, 13, 37, 55, 818008, tzinfo=datetime.timezone.utc)
        #     ))

        return PostOrderResponse(
            order_id=self.get_new_order_id(),
            execution_report_status=OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
            order_type=OrderType.ORDER_TYPE_LIMIT,
            direction=direction,
            lots_requested=lots,
            lots_executed=lots,
            initial_order_price=self.float_to_money_value(lots * self.current_price),
            executed_order_price=self.float_to_money_value(self.current_price),
            total_order_amount=self.float_to_money_value(lots * self.current_price),
            initial_commission=self.float_to_money_value(lots * self.current_price * self.commission),
            executed_commission=self.float_to_money_value(0),  # как в оригинале
            initial_security_price=self.float_to_money_value(self.current_price),
        )

    def get_post_order_response_limit(self, direction, lots, price):
        # OrderResponse(
        #   order_id='R252613501',
        #   execution_report_status= < OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_NEW: 4 >,
        #   lots_requested = 2,
        #   lots_executed = 0,
        #   initial_order_price = MoneyValue(currency='rub', units=470, nano=0),
        #   executed_order_price = MoneyValue(currency='rub', units=0,nano=0),
        #   total_order_amount = MoneyValue(currency='rub', units=0, nano=0),
        #   initial_commission = MoneyValue(currency='rub', units=0, nano=240000000),
        #   executed_commission = MoneyValue(currency='rub', units=0, nano=0),
        #   aci_value = MoneyValue(currency='', units=0, currency='rub', units=235, nano=0),
        #   order_type = < OrderType.ORDER_TYPE_LIMIT: 1 >,
        #   message = '',
        #   initial_order_price_pt = Quotation(units=0,nano=0),
        #   instrument_uid = 'c74***904',
        #   order_request_id = '2024-04-22 14:13:57.484562+00:00',
        #   response_metadata = ResponseMetadata(
        #     tracking_id='bd***1f0',
        #     server_time=datetime.datetime(2024, 4, 22, 14, 13, 59, 82995, tzinfo=datetime.timezone.utc)
        #   ))
        return PostOrderResponse(
            order_id=self.get_new_order_id(),
            execution_report_status=OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_NEW,
            order_type=OrderType.ORDER_TYPE_LIMIT,
            direction=direction,
            lots_requested=lots,
            lots_executed=0,
            initial_order_price=self.float_to_money_value(lots * price),
            executed_order_price=self.float_to_money_value(0),
            total_order_amount=self.float_to_money_value(0),
            initial_commission=self.float_to_money_value(lots * price * self.commission),
            executed_commission=self.float_to_money_value(0),
        )

    def get_order_state(self, order: PostOrderResponse) -> OrderState:
        # OrderState(
        #   order_id='R252613501',
        #   execution_report_status= < OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL: 1 >,
        #   lots_requested = 2,
        #   lots_executed = 2,
        #   initial_order_price = MoneyValue(currency='rub', units=470, nano=0),
        #   executed_order_price = MoneyValue(currency='rub', units=468, nano=590000000), !!! а вот тут произведение
        #   total_order_amount = MoneyValue(currency='rub', units=468, nano=590000000),
        #   average_position_price = MoneyValue(currency='rub', units=234, nano=295000000),
        #   initial_commission = MoneyValue(currency='rub', units=0, nano=240000000),
        #   executed_commission = MoneyValue(currency='rub', units=0, nano=230000000),
        #   figi = 'BBG00F9XX7H4',
        #   direction = < OrderDirection.ORDER_DIRECTION_BUY: 1 >,
        #   initial_security_price = MoneyValue(currency='rub', units=235, nano=0),
        #   stages = [
        #     OrderStage(
        #       price=MoneyValue(currency='rub', units=234, nano=295000000),
        #       quantity=2,
        #       trade_id='D125637207',
        #       execution_time=datetime.datetime(2024, 4, 22, 14, 13, 58, 978563, tzinfo=datetime.timezone.utc)
        #     ),
        #   ],
        #   service_commission = MoneyValue(currency='rub', units=0, nano=0),
        #   currency = 'rub',
        #   order_type = < OrderType.ORDER_TYPE_LIMIT: 1 >,
        #   order_date = datetime.datetime(2024, 4, 22, 14, 13, 58, 982707, tzinfo=datetime.timezone.utc),
        #   instrument_uid = 'c748***904',
        #   order_request_id = '2024-04-22 14:13:57.484562 00:00'
        # )
        #
        # Для нового 2 х 236,5
        # OrderState(
        #   order_id='46106857072',
        #   execution_report_status= < OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_NEW: 4 >,
        #   lots_requested = 2,
        #   lots_executed = 0,
        #   initial_order_price = MoneyValue(currency='rub', units=473, nano=0),
        #   executed_order_price = MoneyValue(currency='rub', units=0,nano=0),
        #   total_order_amount = MoneyValue(currency='rub', units=473, nano=0),
        #   average_position_price = MoneyValue(currency='rub', units=0,nano=0),
        #   initial_commission = MoneyValue(currency='rub', units=0, nano=240000000),
        #   executed_commission = MoneyValue(currency='rub', units=0, nano=0),
        #   figi = 'BBG00F9XX7H4',
        #   direction = < OrderDirection.ORDER_DIRECTION_SELL: 2 >,
        #   initial_security_price = MoneyValue(currency='rub', units=236, nano=500000000),
        #   stages = [],
        #   service_commission = MoneyValue(currency='rub', units=0, nano=0),
        #   currency = 'rub', order_type = < OrderType.ORDER_TYPE_LIMIT: 1 >,
        #   order_date = datetime.datetime(2024, 4, 22, 14, 41, 41, 164931, tzinfo=datetime.timezone.utc),
        #   instrument_uid = 'c7***904',
        #   order_request_id = '2024-04-22 14:41:39.559532 00:00')

        is_executed = order.order_id in self.executed_orders_ids or order.order_type == OrderType.ORDER_TYPE_MARKET
        price_0 = self.float_to_quotation(0)
        avg_init_price = self.float_to_money_value(
            self.quotation_to_float(order.initial_order_price) / order.lots_requested)
        return OrderState(
            order_id=order.order_id,
            order_type=order.order_type,
            direction=order.direction,
            lots_requested=order.lots_requested,
            lots_executed=order.lots_requested if is_executed else 0,
            initial_order_price=order.initial_order_price,
            executed_order_price=order.initial_order_price if is_executed else price_0,
            total_order_amount=order.initial_order_price if is_executed else price_0,
            average_position_price=avg_init_price if is_executed else price_0,
            initial_commission=order.initial_commission,
            executed_commission=order.initial_commission if is_executed else price_0,
            initial_security_price=avg_init_price,
            service_commission=self.float_to_money_value(0),
            execution_report_status=OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL
            if is_executed else OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_NEW,
        )
