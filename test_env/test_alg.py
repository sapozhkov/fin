import copy
from datetime import datetime, timezone, timedelta
from time import sleep

import pandas as pd
from tinkoff.invest import OrderDirection, Client, CandleInterval

from test_env.client_test_env import ClientTestEnvHelper
from test_env.logger_test_env import LoggerTestEnvHelper
from test_env.time_test_env import TimeTestEnvHelper
from test_env.accounting_test_env import AccountingTestEnvHelper

from trader_bot import ScalpingBot
from dto.config_dto import ConfigDTO
from lib.historical_candles import HistoricalCandles


class TestAlgorithm:
    def __init__(
            self,
            token,
            ticker,
            figi,
            do_printing=False
    ):
        self.token = token
        self.ticker = ticker
        self.figi = figi

        self.data_handler = HistoricalCandles(token, figi, ticker)
        self.time_helper = TimeTestEnvHelper()
        self.logger_helper = LoggerTestEnvHelper(self.time_helper, do_printing)

        self.client_helper = ClientTestEnvHelper(self.ticker, self.logger_helper, self.time_helper)
        self.client_helper.set_ticker_params(1, 0.1, self.figi, 'RUR')

        self.accounting_helper = AccountingTestEnvHelper(self.client_helper)

    def test(
            self,

            config: ConfigDTO,

            last_test_date,
            test_days_num,
            shares_count=0,
            pretest_days=0,
    ):
        profit = 0
        success_days = 0
        balance_change_list = []
        operations_cnt = 0
        operations_cnt_list = []

        days_list = self.data_handler.get_days_list(last_test_date, test_days_num)

        self.accounting_helper.num = shares_count

        # для расчета прибыли за весь период. купил в начале, в конце продал
        started_t = False
        start_price_t = 0
        end_price_t = 0

        base_config = copy.copy(config)

        # закручиваем цикл по датам
        for test_date in days_list:

            # if pretest_days:
            #     config = self.pretest_and_get_config(
            #         config=base_config,
            #         current_date=test_date,
            #         shares_count=shares_count,
            #         test_days_num=pretest_days,
            #         prev_config=config
            #     )

            # дальше текущего времени не убегаем
            config.end_time = self.get_end_time(test_date, config.end_time)

            # прогоняем по дню (-3 часа для компенсации часового сдвига)
            date_from = datetime.strptime(test_date + ' ' + config.start_time, "%Y-%m-%d %H:%M")
            date_to = datetime.strptime(test_date + ' ' + config.end_time, "%Y-%m-%d %H:%M")

            # задаем параметры дня
            self.time_helper.set_current_time(date_from)

            trend_val = self.calculate_rsi_trend(pretest_days)
            trend_val_norm = max(0, min(1, 0.5 + (trend_val - 0.5) * 5 / 3))
            config.base_shares = round(config.max_shares * trend_val_norm)
            # print(f"{test_date} - tv {round(trend_val, 2)} / {round(trend_val_norm, 2)} - b {config.base_shares}")

            # создаем бота с настройками
            bot = ScalpingBot(
                self.token,
                self.ticker,

                config=config,
                time_helper=self.time_helper,
                logger_helper=self.logger_helper,
                client_helper=self.client_helper,
                accounting_helper=self.accounting_helper,
            )

            self.client_helper.set_candles_list(self.data_handler.get_candles(test_date))

            self.accounting_helper.reset()

            started = False
            start_price = 0
            start_cnt = 0

            # Использование итератора для вывода каждой пары час-минута
            for dt in self.data_handler.get_hour_minute_pairs(date_from, date_to):
                if not bot.continue_trading():
                    break

                # задаем время
                self.time_helper.set_time(dt)

                candle = self.client_helper.get_candle(dt)
                if candle is None:
                    self.logger_helper.error(f"No candle for {dt}")
                    continue

                # задаем текущее значение свечи
                self.client_helper.set_current_candle(candle)

                # при первом запуске
                if not started:
                    started = True
                    start_price = self.client_helper.get_current_price()
                    start_cnt = self.accounting_helper.num

                    if not started_t:
                        started_t = True
                        start_price_t = start_price

                for order_id, order in self.client_helper.orders.items():
                    if order_id in self.client_helper.executed_orders_ids:
                        continue
                    price = self.client_helper.quotation_to_float(order.initial_order_price)
                    if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
                        low_buy_price = self.client_helper.quotation_to_float(candle.low)
                        order_executed = price >= low_buy_price
                        # order_executed_on_border = price == low_buy_price
                    else:
                        high_sell_price = self.client_helper.quotation_to_float(candle.high)
                        order_executed = price <= high_sell_price
                        # order_executed_on_border = price == high_sell_price

                    if order_executed:
                        self.client_helper.executed_orders_ids.append(order_id)

                # если пора просыпаться
                if self.time_helper.is_time_to_awake():
                    # print(dt.strftime("%H:%M"))
                    # запускаем итерацию торгового алгоритма
                    bot.run_iteration()

            bot.stop()

            operations = len(self.accounting_helper.get_deals())
            operations_cnt += operations
            operations_cnt_list.append(operations)

            end_price = self.client_helper.get_current_price()
            end_cnt = self.accounting_helper.num

            balance_change = (
                    - start_price * start_cnt
                    + self.accounting_helper.sum
                    + end_price * end_cnt
            )

            end_price_t = end_price

            profit = round(profit + balance_change, 2)

            # print(f"{test_date} - s {round(balance_change, 2)} - b {profit}")

            # #51 для перебирания дат с потерями
            # if balance_change < 0:
            #     print(f"{test_date} - {round(balance_change, 2)}")

            if balance_change > 0:
                success_days += 1

            balance_change_list.append(balance_change)

        profit_p = round(profit / (start_price_t * config.max_shares), 2) if start_price_t and config.max_shares else 0

        # это для обычной торговли. купил в начале, в конце продал
        potential_profit = round((end_price_t - start_price_t) * config.max_shares, 2)
        # сколько от обычной торговли в процентах ты сделал
        potential_profit_p = round(profit / potential_profit, 2) if potential_profit > 0 else 0

        # todo это надо превратить в формализованную выдачу в классе
        return {
            'pretest_days': pretest_days,
            'profit': profit,
            'profit_p': f"{profit_p}",
            'config': config,

            'profit_avg': round(sum(balance_change_list) / test_days_num, 2),

            'pot_profit': potential_profit,
            'pot_profit_p': potential_profit_p,

            'days': test_days_num,
            'success_days': success_days,
            'success_p': round(success_days / test_days_num, 2),

            'op_cnt': operations_cnt,
            'op_avg': round(sum(operations_cnt_list) / test_days_num, 2),
        }

    def calculate_rsi_trend(self, period=10):
        with Client(self.token) as client:
            to_date = self.time_helper.now() - timedelta(days=1)
            from_date = to_date - timedelta(days=period * 2 - 1)  # Удваиваем период для точности RSI

            candles = client.market_data.get_candles(
                figi=self.figi,
                from_=from_date,
                to=to_date,
                interval=CandleInterval.CANDLE_INTERVAL_DAY
            )

            closing_prices = pd.Series([candle.close.units + candle.close.nano * 1e-9 for candle in candles.candles])
            delta = closing_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # Нормализуем RSI для получения значения от 0 до 1
            try:
                normalized_rsi = rsi / 100
                current_trend = normalized_rsi.iloc[-1]
            except Exception:
                return 0

            return current_trend

    @staticmethod
    def get_end_time(test_date, end_time):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if test_date != today:
            return end_time

        # Преобразование end_time в объект datetime с учетом test_date
        end_time_dt = datetime.strptime(f"{test_date} {end_time}", "%Y-%m-%d %H:%M")
        end_time_dt = end_time_dt.replace(tzinfo=timezone.utc)

        # Получение текущего времени
        current_time = datetime.now(timezone.utc)

        # Выбор минимального значения из текущего времени и end_time
        min_time = min(current_time, end_time_dt)

        return min_time.strftime("%H:%M")

    # пока не используется, но сохраним код на будущее
    def pretest_and_get_config(
            self,
            config: ConfigDTO,
            current_date,
            shares_count=0,
            test_days_num=None,
            prev_config: ConfigDTO | None = None,
    ):
        configs = [
            (max_shares, step_size)
            for max_shares in [config.max_shares]
            # for max_shares in [config.max_shares-1, config.max_shares, config.max_shares+1]
            for step_size in [config.step_size-.1, config.step_size, config.step_size+.1]
        ]

        if prev_config is not None:
            configs += [
                (max_shares, step_size)
                for max_shares in [prev_config.max_shares]
                # for max_shares in [prev_config.max_shares-1, prev_config.max_shares, prev_config.max_shares+1]
                for step_size in [prev_config.step_size-.1, prev_config.step_size, prev_config.step_size+.1]
            ]

            # Используем set для получения уникальных объектов
            configs = list(set(configs))

        results = []
        for (max_shares, step_size) in configs:
            tmp_config = copy.copy(config)
            tmp_config.max_shares = max_shares
            tmp_config.step_size = step_size

            prev_date = self.get_prev_date(current_date)
            # print(f"Рассчитываем дату {current_date}")
            # print(f"    для этого анализируем дату {prev_date}")

            result = self.test(
                last_test_date=prev_date,
                test_days_num=test_days_num,
                config=tmp_config,

                shares_count=shares_count,

                pretest_days=0,  # ! важно, чтобы тут 0 был, иначе уйдем в рекурсию
            )
            results.append(result)

        # сортируем по прибыльности все
        sorted_results = sorted(results, key=lambda x: float(x['profit_p']))
        # print(f"all {sorted_results}")

        # выбираем самую прибыльную настройку и выдаем её системе
        best = sorted_results.pop()
        # print(f"best {best['config']}")

        return best['config']

    def get_prev_date(self, last_test_date):
        days = self.data_handler.get_days_list(last_test_date, 2)
        days.reverse()
        return days.pop()
