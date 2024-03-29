from datetime import datetime, timezone

from tinkoff.invest import OrderDirection

from test_env.client_test_env import ClientTestEnvHelper
from test_env.logger_test_env import LoggerTestEnvHelper
from test_env.time_test_env import TimeTestEnvHelper
from test_env.accounting_test_env import AccountingTestEnvHelper

from trader_bot import ScalpingBot
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
            last_test_date='2024-03-15',
            test_days_num=1,
            sleep_trading=5 * 60,
            sleep_no_trade=300,
            quit_on_balance_up_percent=2,
            quit_on_balance_down_percent=1,
            start_time='07:45',  # 10:45
            end_time='15:15',  # 18:15

            shares_count=0,
            max_shares=5,
            base_shares=3,
            threshold_buy_steps=5,
            threshold_sell_steps=0,
            step_size=.5,
            step_cnt=3,
    ):
        balance = 0
        success_days = 0
        balance_change_list = []
        operations_cnt = 0
        operations_cnt_list = []

        days_list = self.data_handler.get_days_list(last_test_date, test_days_num)

        self.accounting_helper.num = shares_count

        # закручиваем цикл по датам
        for test_date in days_list:
            # дальше текущего времени не убегаем
            end_time = self.get_end_time(test_date, end_time)

            # прогоняем по дню (-3 часа для компенсации часового сдвига)
            date_from = datetime.strptime(test_date + ' ' + start_time, "%Y-%m-%d %H:%M")
            date_to = datetime.strptime(test_date + ' ' + end_time, "%Y-%m-%d %H:%M")

            # задаем параметры дня
            self.time_helper.set_current_time(date_from)

            # создаем бота с настройками
            bot = ScalpingBot(
                self.token,
                self.ticker,

                start_time=start_time,
                end_time=end_time,

                sleep_trading=sleep_trading,
                sleep_no_trade=sleep_no_trade,

                quit_on_balance_up_percent=quit_on_balance_up_percent,
                quit_on_balance_down_percent=quit_on_balance_down_percent,

                max_shares=max_shares,
                base_shares=base_shares,
                threshold_buy_steps=threshold_buy_steps,
                threshold_sell_steps=threshold_sell_steps,
                step_size=step_size,
                step_cnt=step_cnt,

                time_helper=self.time_helper,
                logger_helper=self.logger_helper,
                client_helper=self.client_helper,
                accounting_helper=self.accounting_helper,
            )

            self.client_helper.set_candles_list(self.data_handler.get_candles(test_date))

            self.accounting_helper.reset()

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

            balance_change = self.accounting_helper.sum

            # хак для учета откупленных/проданных в этой итерации акций
            # current_price = bot.get_current_price()
            # while balance_change < - .5 * current_price:
            #     balance_change += current_price
            # while balance_change > .5 * current_price:
            #     balance_change -= current_price

            balance = round(balance + balance_change, 2)

            # print(f"{test_date} - s {round(balance_change, 2)} - b {balance}")

            # if balance_change < 0:
            #     print(f"{test_date} - {balance_change}")

            if balance_change > 0:
                success_days += 1

            balance_change_list.append(balance_change)

        balance = round(balance + self.accounting_helper.num * self.client_helper.current_price, 2)
        profit = balance / (self.client_helper.current_price * max_shares)

        return {
            'balance': balance,
            'profit_p': f"{round(profit, 2)}",
            'balance_change_avg': round(sum(balance_change_list) / test_days_num, 2),

            'days': test_days_num,
            'success_days': success_days,
            'success_p': round(success_days / test_days_num, 2),

            'sleep_trading': sleep_trading,

            # 'quit_on_balance_up_percent': quit_on_balance_up_percent,
            # 'quit_on_balance_down_percent': quit_on_balance_down_percent,

            'max_shares': max_shares,
            'base_shares': base_shares,
            'threshold_buy_steps': threshold_buy_steps,
            'threshold_sell_steps': threshold_sell_steps,
            'step_size': step_size,
            'step_cnt': step_cnt,

            'operations_cnt': operations_cnt,
            'operations_avg': round(sum(operations_cnt_list) / test_days_num, 2),
        }

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
