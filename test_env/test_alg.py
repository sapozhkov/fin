from datetime import datetime, timezone

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
            profit_steps=5,
            candles_count=4,
            sleep_trading=5 * 60,
            sleep_no_trade=300,
            take_profit_percent=1.5,
            quit_on_balance_up_percent=2,
            quit_on_balance_down_percent=1,
            start_time='07:45',  # 10:45
            end_time='15:15',  # 18:15
            no_operation_timeout_seconds=300,
    ):
        balance = 0
        success_days = 0
        balance_change_list = []
        operations_cnt = 0
        operations_not_closed_cnt = 0
        operations_cnt_list = []

        days_list = self.data_handler.get_days_list(last_test_date, test_days_num)

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

                profit_steps=profit_steps,
                candles_count=candles_count,

                sleep_trading=sleep_trading,
                sleep_no_trade=sleep_no_trade,
                no_operation_timeout_seconds=no_operation_timeout_seconds,

                take_profit_percent=take_profit_percent,
                quit_on_balance_up_percent=quit_on_balance_up_percent,
                quit_on_balance_down_percent=quit_on_balance_down_percent,

                time_helper=self.time_helper,
                logger_helper=self.logger_helper,
                client_helper=self.client_helper,
                accounting_helper=self.accounting_helper,
            )

            bot.reset_last_operation_time()
            self.client_helper.set_candles_list(self.data_handler.get_candles(test_date))

            self.accounting_helper.reset()

            # Использование итератора для вывода каждой пары час-минута
            for dt in self.data_handler.get_hour_minute_pairs(date_from, date_to):
                if not bot.continue_trading:
                    break

                # задаем время
                self.time_helper.set_time(dt)

                candle = self.client_helper.get_candle(dt)
                if candle is None:
                    self.logger_helper.error(f"No candle for {dt}")
                    continue

                # задаем текущее значение свечи
                self.client_helper.set_current_candle(candle)

                # анализируем заявки - успешные помечаем
                if bot.buy_order:
                    buy_price = self.client_helper.quotation_to_float(bot.buy_order.initial_order_price)
                    low_buy_price = self.client_helper.quotation_to_float(candle.low)
                    if buy_price >= low_buy_price:
                        self.client_helper.buy_order_executed = True
                        self.client_helper.buy_order_executed_on_border = buy_price == low_buy_price

                if bot.sell_order:
                    sell_price = self.client_helper.quotation_to_float(bot.sell_order.initial_order_price)
                    high_sell_price = self.client_helper.quotation_to_float(candle.high)
                    if sell_price <= high_sell_price:
                        self.client_helper.sell_order_executed = True
                        self.client_helper.sell_order_executed_on_border = sell_price == high_sell_price

                # если пора просыпаться
                if self.time_helper.is_time_to_awake():
                    # print(dt.strftime("%H:%M"))
                    # запускаем итерацию торгового алгоритма
                    bot.run_iteration()

            bot.stop()

            operations = len(self.accounting_helper.get_deals())
            operations_cnt += operations
            operations_cnt_list.append(operations)
            if self.client_helper.sell_order_executed % 2 == 1:
                operations_not_closed_cnt += 1

            balance_change = round(self.accounting_helper.sum, 2)
            balance = round(balance + balance_change, 2)

            if balance_change > 0:
                success_days += 1

            balance_change_list.append(balance_change)

        return {
            'balance': balance,
            'balance_change_avg': round(sum(balance_change_list) / test_days_num, 2),

            'days': test_days_num,
            'success_days': success_days,
            'success_p': round(success_days / test_days_num, 2),

            'profit_steps': profit_steps,
            'candles_count': candles_count,
            'sleep_trading': sleep_trading,

            'take_profit_percent': take_profit_percent,
            'quit_on_balance_up_percent': quit_on_balance_up_percent,
            'quit_on_balance_down_percent': quit_on_balance_down_percent,

            'operations_cnt': operations_cnt,
            'operations_avg': round(sum(operations_cnt_list) / test_days_num, 2),
            'op_not_closed': operations_not_closed_cnt,
            'op_not_closed_avg': round(operations_not_closed_cnt / test_days_num, 2),
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
