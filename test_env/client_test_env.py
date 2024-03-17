from datetime import time as datetime_time, datetime, timedelta

from tinkoff.invest import OrderType, PostOrderResponse, OrderDirection, MoneyValue, HistoricCandle, \
    GetCandlesResponse

from helper.tinkoff_client import AbstractProxyClient


class ClientTestEnvHelper(AbstractProxyClient):
    buy_id = '1'
    sell_id = '2'

    def __init__(self, ticker, logger, time_helper, candles_1_min):
        super().__init__()
        self.ticker = ticker
        self.logger = logger
        self.time = time_helper
        # todo тут проверить нужен ли временной сдвиг на tmz
        self.candles_1_min_dict = {(candle.time.hour, candle.time.minute): candle for candle in candles_1_min.candles}

        self.buy_order = None
        self.buy_order_executed = False
        self.buy_order_executed_on_border = False

        self.sell_order = None
        self.sell_order_executed = False
        self.sell_order_executed_on_border = False

        self.total_completed_orders = 0
        self.total_completed_orders_on_border = 0

        self.current_candle: HistoricCandle | None = None
        self.current_price: float = 0
        self.commission: float = 0.0005

    def set_current_candle(self, candle: HistoricCandle):
        self.current_candle = candle
        self.current_price = self.quotation_to_float(candle.close)

    def get_candle(self, dt) -> HistoricCandle | None:
        return self.candles_1_min_dict.get((dt.hour, dt.minute), None)

    def set_ticker_params(self, round_signs, step_size, figi, currency):
        self.round_signs = round_signs
        self.step_size = step_size
        self.figi = figi
        self.currency = currency

    def can_trade(self):
        now = self.time.now()

        # Проверка, что сейчас будний день (0 - понедельник, 6 - воскресенье)
        if now.weekday() >= 5:
            return False

        # Проверка, что текущее время между 10:00 и 18:40
        if not (datetime_time(10 - self.time.tmz, 00) <= now.time() <= datetime_time(18 - self.time.tmz, 40)):
            return False

        return True

    def float_to_money_value(self, price) -> MoneyValue:
        return MoneyValue(self.currency, units=int(price), nano=int((self.round(price - int(price))) * 1e9))

    def place_order(self, lots: int, operation,
                    price: float | None, order_type=OrderType.ORDER_TYPE_MARKET) -> PostOrderResponse:
        order_id = self.buy_id if operation == OrderDirection.ORDER_DIRECTION_BUY else self.sell_id

        # покупка по рыночной цене
        if order_type == OrderType.ORDER_TYPE_MARKET:
            # считаем сразу исполненной по указанной цене минус комиссия
            return PostOrderResponse(
                order_id=order_id,
                order_type=order_type,
                direction=operation,
                initial_order_price=self.float_to_money_value(price),
                executed_order_price=self.float_to_money_value(price),
                initial_commission=self.float_to_money_value(self.current_price * self.commission),
                executed_commission=self.float_to_money_value(self.current_price * self.commission),
            )

        # иначе лимитная заявка
        elif order_type == OrderType.ORDER_TYPE_LIMIT:

            if operation == OrderDirection.ORDER_DIRECTION_BUY:
                self.buy_order_executed = False
                self.buy_order_executed_on_border = False
            elif operation == OrderDirection.ORDER_DIRECTION_SELL:
                self.sell_order_executed = False
                self.sell_order_executed_on_border = False

            return PostOrderResponse(
                order_id=order_id,
                order_type=order_type,
                direction=operation,
                initial_order_price=self.float_to_money_value(price),
                executed_order_price=self.float_to_money_value(0),
                initial_commission=self.float_to_money_value(self.current_price * self.commission),
                executed_commission=self.float_to_money_value(0),
            )

        else:
            raise f"Unknown order_type: {order_type}"

    def get_candles(self, from_date, to_date, interval):
        interval_min = self.interval_duration_minutes[interval]
        ask_time_list = self.get_interval_time_list(from_date, to_date, interval_min)
        candles = []
        for hour, minute in ask_time_list:
            candles.append(self.get_calculated_candle(hour, minute, interval_min))
        return GetCandlesResponse(candles)

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

        # Проверка, является ли последнее добавленное время равным to_date
        # Если нет, добавляем следующую пару
        last_time = result[-1]
        last_datetime = datetime(from_date.year, from_date.month, from_date.day, last_time[0], last_time[1])
        if last_datetime < to_date:
            next_time = last_datetime + timedelta(minutes=interval)
            result.append((next_time.hour, next_time.minute))

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

    def get_calculated_candle(self, hour, minute, n=5):
        previous_minutes = self.get_n_minutes(hour, minute, n)
        # todo важно!!! вот тут надо выбирать не все запрошенные, а не старше текущей даты

        open_ = None
        high = 0
        low = 1000000000
        close = 0
        volume = 0

        for time_pair in previous_minutes:
            t1 = self.candles_1_min_dict[time_pair]
            if open_ is None:
                open_ = t1.open
            high = max(high, self.quotation_to_float(t1.high))
            low = min(low, self.quotation_to_float(t1.low))
            close = t1.close
            volume += t1.volume

        now = self.time.now()

        return HistoricCandle(
            high=self.float_to_quotation(high),
            low=self.float_to_quotation(low),
            open=open_,
            close=close,
            volume=volume,
            time=datetime(now.year, now.month, now.day, hour, minute),
            is_complete=True
        )

    def order_is_executed(self, order: PostOrderResponse):

        # покупка по рыночной цене
        if order.order_type == OrderType.ORDER_TYPE_MARKET:
            # считаем сразу исполненной по указанной цене минус комиссия
            return (
                True,
                order
            )

        # иначе лимитная заявка
        elif order.order_type == OrderType.ORDER_TYPE_LIMIT:
            order_price = self.quotation_to_float(order.initial_order_price)
            res = False

            if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
                if self.buy_order_executed:
                    res = True
                    order.executed_order_price = self.float_to_money_value(order_price)
                    order.executed_commission = self.float_to_money_value(self.current_price * self.commission)

                    self.total_completed_orders += 1
                    if self.buy_order_executed_on_border:
                        self.total_completed_orders_on_border += 1

            elif order.order_type == OrderDirection.ORDER_DIRECTION_SELL:
                if self.sell_order_executed:
                    res = True
                    order.executed_order_price = self.float_to_money_value(order_price)
                    order.executed_commission = self.float_to_money_value(self.current_price * self.commission)

                    self.total_completed_orders += 1
                    if self.sell_order_executed_on_border:
                        self.total_completed_orders_on_border += 1

            return (
                res,
                order  # todo вот тут может отстрелить, так как не тот объект отдается, который ожидается
            )

        else:
            raise f"Unknown order_type: {order.order_type}"

    def get_instruments_count(self):
        raise 'Not implemented'

    def cancel_order(self, order):
        if not order:
            return False
        return True
