import copy
from datetime import datetime, timezone

from tinkoff.invest import OrderDirection

from lib.time_helper import TimeHelper
from lib.order_helper import OrderHelper
from lib.trading_bot import TradingBot
from test_env.accounting_test_env import AccountingTestEnvHelper
from test_env.client_test_env import ClientTestEnvHelper
from test_env.logger_test_env import LoggerTestEnvHelper

from dto.config_dto import ConfigDTO
from test_env.time_test_env import TimeTestEnvHelper


class TestAlgorithm:
    def __init__(
            self,
            token,
            config: ConfigDTO,
            do_printing=False
    ):
        self.token = token
        self.config = config
        self.time_helper = TimeTestEnvHelper()
        self.logger_helper = LoggerTestEnvHelper(self.time_helper, do_printing)
        self.client_helper = ClientTestEnvHelper(token, config.ticker, self.logger_helper, self.time_helper)
        self.accounting_helper = AccountingTestEnvHelper(self.client_helper)
        self.order_helper = OrderHelper(self.client_helper)

    def test(
        self,
        last_test_date,
        test_days_num,
        shares_count=0,
    ):
        # внутренние переменные
        profit = 0
        success_days = 0
        balance_change_list = []
        operations_cnt = 0
        operations_cnt_list = []

        if last_test_date is None:
            last_test_date = TimeHelper.get_current_date()

        days_list = self.client_helper.ticker_cache.get_days_list(last_test_date, test_days_num)

        self.accounting_helper.set_num(shares_count)

        # для расчета прибыли за весь период. купил в начале, в конце продал
        started_t = False
        start_price_t = 0
        end_price_t = 0

        original_config = copy.copy(self.config)
        maj_commission = 0
        total_maj_commission = 0

        # закручиваем цикл по датам
        for test_date in days_list:

            config = copy.copy(original_config)

            # дальше текущего времени не убегаем
            config.end_time = self.get_end_time(test_date, config.end_time)

            # прогоняем по дню (-3 часа для компенсации часового сдвига)
            date_from = datetime.strptime(test_date + ' ' + config.start_time, "%Y-%m-%d %H:%M")
            date_to = datetime.strptime(test_date + ' ' + config.end_time, "%Y-%m-%d %H:%M")

            # задаем параметры дня
            self.time_helper.set_current_time(date_from)

            # создаем бота с настройками
            bot = TradingBot(
                self.token,
                config=self.config,
                time_helper=self.time_helper,
                logger_helper=self.logger_helper,
                client_helper=self.client_helper,
                accounting_helper=self.accounting_helper,
            )

            if self.accounting_helper.get_num() < 0:
                maj_commission += self.client_helper.get_current_price() * self.accounting_helper.get_num() * 0.0012
                # print(f"{test_date} - maj_commission {round(maj_commission, 2)} = "
                #       f"{self.client_helper.get_current_price()} * {self.accounting_helper.get_num()} * {0.0012}")

            if bot.state == bot.STATE_FINISHED:
                # print(f"{test_date} - skip, finished status on start")
                continue

            normal_trade_day = self.client_helper.set_candles_list_by_date(test_date)
            if not normal_trade_day:
                # print(f"{test_date} - skip, no candles")
                continue

            self.accounting_helper.reset()

            started = False
            start_price = 0
            start_cnt = 0

            # Использование итератора для вывода каждой пары час-минута
            for dt in self.time_helper.get_hour_minute_pairs(date_from, date_to):
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
                    start_cnt = self.accounting_helper.get_num()

                    if not started_t:
                        started_t = True
                        start_price_t = start_price

                for order_id, order in self.client_helper.orders.items():
                    if order_id in self.client_helper.executed_orders_ids:
                        continue
                    avg_price = self.order_helper.get_avg_price(order)
                    if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
                        low_buy_price = self.client_helper.quotation_to_float(candle.low)
                        order_executed = avg_price >= low_buy_price
                        # order_executed_on_border = price == low_buy_price
                    else:
                        high_sell_price = self.client_helper.quotation_to_float(candle.high)
                        order_executed = avg_price <= high_sell_price
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
            end_cnt = self.accounting_helper.get_instrument_count()

            balance_change = (
                    - start_price * start_cnt
                    + self.accounting_helper.get_sum()
                    + end_price * end_cnt
                    + maj_commission
            )

            total_maj_commission += maj_commission
            maj_commission = 0

            end_price_t = end_price

            profit = round(profit + balance_change, 2)

            # if bot.config.pretest_period > 0:
            #     rsi = bot.get_rsi_trend_val(bot.config.pretest_period)
            #     if rsi is not None:
            #         rsi_text = f"rsi - {round(rsi, 2)} {'^' if rsi > .5 else 'v'} "
            #     else:
            #         rsi_text = 'no rsi '
            # else:
            #     rsi_text = ''
            # print(f"{test_date} "
            #       f"{rsi_text}"
            #       f"change: {round(balance_change, 2)}, "
            #       f"num: {bot.get_current_count()}")

            # #51 для перебирания дат с потерями
            # if balance_change < 0:
            #     print(f"{test_date} - {round(balance_change, 2)}")

            if balance_change > 0:
                success_days += 1

            balance_change_list.append(balance_change)

        # последние несколько дней могут быть не рабочими, учитываем накопленную комиссию
        total_maj_commission += maj_commission
        profit += maj_commission

        config = original_config

        profit_p = round(100 * profit / (start_price_t * config.step_max_cnt * config.step_lots), 2) \
            if start_price_t and config.step_max_cnt else 0

        # это для обычной торговли. купил в начале, в конце продал
        potential_profit = round((end_price_t - start_price_t) * config.step_max_cnt * config.step_lots, 2)
        # сколько от обычной торговли в процентах ты сделал
        potential_profit_p = round(profit / potential_profit, 2) if potential_profit > 0 else 0

        return {
            'profit': profit,
            'profit_p': profit_p,
            'config': config,
            # 'maj_com': round(total_maj_commission, 2),

            # 'profit_avg': round(sum(balance_change_list) / test_days_num, 2),
            #
            # 'pot_profit': potential_profit,
            # 'pot_profit_p': potential_profit_p,
            #
            # 'days': test_days_num,
            # 'success_days': success_days,
            # 'success_p': round(success_days / test_days_num, 2),
            #
            'op_cnt': operations_cnt,
            # 'op_avg': round(sum(operations_cnt_list) / test_days_num, 2),

            # 'sleep_trading': config.sleep_trading,
            #
            # # 'quit_on_balance_up_percent': quit_on_balance_up_percent,
            # # 'quit_on_balance_down_percent': quit_on_balance_down_percent,
            #
            # 'step_max_cnt': config.step_max_cnt,
            # 'step_base_cnt': config.step_base_cnt,
            # 'threshold_buy_steps': config.threshold_buy_steps,
            # 'threshold_sell_steps': config.threshold_sell_steps,
            # 'step_size': config.step_size,
            # 'step_set_orders_cnt': config.step_set_orders_cnt,
            #
            # 'operations_cnt': operations_cnt,
            # 'operations_avg': round(sum(operations_cnt_list) / test_days_num, 2),
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
