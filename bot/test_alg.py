import copy
import math
from datetime import datetime, timezone
from typing import Tuple, Optional

from tinkoff.invest import OrderDirection

from app import AppConfig
from bot import TradingBot
from app.cache import TickerCache, LocalCache
from bot.env.test import TimeTestEnvHelper, LoggerTestEnvHelper, ClientTestEnvHelper, AccountingTestEnvHelper
from bot.helper import OrderHelper
from app.config import RunConfig
from app.helper import TimeHelper


class TestAlgorithm:
    def __init__(
            self,
            config: RunConfig,
            do_printing=False,
            use_cache=True,
    ):
        self.config = config
        self.time_helper = TimeTestEnvHelper()
        self.logger_helper = LoggerTestEnvHelper(self.time_helper, do_printing)
        self.client_helper = ClientTestEnvHelper(config.ticker, self.logger_helper, self.time_helper)
        self.accounting_helper = AccountingTestEnvHelper(self.client_helper, self.time_helper)
        self.use_cache = use_cache

    def test(
        self,
        last_test_date,
        test_days_num,
        shares_count=0,

        try_find_best_config: bool = False,
    ):
        """
        Провести тестирование по конфигу
        :param last_test_date: последняя дата для теста
        :param test_days_num: сколько дней надо проверить
        :param shares_count: сколько инструментов на балансе
        :param try_find_best_config: подбирать лучший конфиг. рекурсивно вызывает эту же функцию. !осторожно - цикл
        :return:
        """
        if test_days_num == 0:
            return None

        # внутренние переменные
        success_days = 0
        balance_change_list = []
        operations_cnt = 0
        operations_cnt_list = []

        if last_test_date is None:
            # до утра гоняем предыдущий день, а то откинется лишний
            if TimeHelper.trades_are_not_started():
                last_test_date = TimeHelper.get_previous_date()
            else:
                last_test_date = TimeHelper.get_current_date()

        days_list = TickerCache.get_trade_days_only(last_test_date, test_days_num)

        self.accounting_helper.set_num(shares_count)

        original_config = copy.copy(self.config)
        maj_commission = 0
        total_maj_commission = 0
        config = None

        balance = 100000  # руб / usd / ...
        start_balance = balance

        # коэф мажоритарной торговли. с ней заявок в 2 раза больше ставится, так как в 2 стороны открываем торги
        maj_k = 2 if original_config.majority_trade else 1

        # закручиваем цикл по датам
        for test_date in days_list:
            if self.accounting_helper.get_num() < 0:
                maj_commission += self.client_helper.get_current_price() * self.accounting_helper.get_num() * 0.0012
                # print(f"{test_date} - maj_commission {round(maj_commission, 2)} = "
                #       f"{self.client_helper.get_current_price()} * {self.accounting_helper.get_num()} * {0.0012}")

            if not TimeHelper.is_trading_day(TimeHelper.to_datetime(test_date)):
                continue

            if try_find_best_config and config is not None:
                config, expected_profit = self.make_best_config_with_profit(
                    test_date=test_date,
                    prev_days=original_config.pretest_period,
                    original_config=original_config,
                    last_config=config)

                mod_do_not_disable = config.mod_do_not_change_instrument_activity
                is_low_profit = expected_profit < AppConfig.INSTRUMENT_ON_THRESHOLD

                if is_low_profit and not mod_do_not_disable:
                    continue

            else:
                config = copy.copy(original_config)

            # дальше текущего времени не убегаем
            config.end_time = self.get_end_time(test_date, config.end_time)

            # прогоняем по дню (время в UTC)
            date_from = datetime.strptime(test_date + ' ' + config.start_time, "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone.utc)
            date_to = datetime.strptime(test_date + ' ' + config.end_time, "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone.utc)

            # задаем параметры дня
            self.time_helper.set_current_time(date_from)

            # сбрасываем все заказы и заявки
            self.accounting_helper.reset()

            normal_trade_day = self.client_helper.set_candles_list_by_date(test_date)
            if not normal_trade_day:
                # print(f"{test_date} - skip, no candles")
                continue

            cache_name = f"b_{test_date}-{config}-{self.accounting_helper.get_num()}"
            cached_val = LocalCache.get(cache_name) if self.use_cache else None

            # Ищем в кэше обходов, если нашли, берем значения оттуда
            # if False and cached_val:
            if cached_val:
                LocalCache.inc_counter('cache_find')

                operations = cached_val['operations']
                end_price = cached_val['end_price']
                end_cnt = cached_val['end_cnt']
                start_price = cached_val['start_price']
                start_cnt = cached_val['start_cnt']
                day_sum = cached_val['day_sum']

                self.accounting_helper.set_num(end_cnt)

            else:

                # создаем бота с настройками
                bot = TradingBot(
                    config=config,
                    time_helper=self.time_helper,
                    logger_helper=self.logger_helper,
                    client_helper=self.client_helper,
                    accounting_helper=self.accounting_helper,
                )

                if bot.state == bot.STATE_FINISHED:
                    # print(f"{test_date} - skip, finished status on start")
                    continue

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
                        config.step_lots = math.floor(balance / (maj_k * start_price * config.step_max_cnt))

                    for order_id, order in self.client_helper.orders.items():
                        if order_id in self.client_helper.executed_orders_ids:
                            continue
                        avg_price = self.client_helper.round(OrderHelper.get_avg_price(order))
                        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
                            low_buy_price = self.client_helper.q2f(candle.low)
                            order_executed = avg_price >= low_buy_price
                            # order_executed_on_border = price == low_buy_price
                        else:
                            high_sell_price = self.client_helper.q2f(candle.high)
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

                operations = self.accounting_helper.get_executed_order_cnt()
                end_price = self.client_helper.get_current_price()
                end_cnt = self.accounting_helper.get_instrument_count()
                day_sum = self.accounting_helper.get_sum()

                to_cache = {
                    'operations': operations,
                    'end_price': end_price,
                    'end_cnt': end_cnt,
                    'start_price': start_price,
                    'start_cnt': start_cnt,
                    'day_sum': day_sum,
                }

                if self.use_cache:
                    LocalCache.set(cache_name, to_cache)
                    LocalCache.inc_counter('cache_miss')

                # конец не кэшированной части

            operations_cnt += operations
            operations_cnt_list.append(operations)

            balance_change = (
                    - start_price * start_cnt
                    + day_sum
                    + end_price * end_cnt
                    + maj_commission
            )

            total_maj_commission += maj_commission
            maj_commission = 0

            # end_price_t = end_price

            balance = round(balance + balance_change, 2)

            if balance_change > 0:
                success_days += 1

            balance_change_list.append(balance_change)

            # if auto_conf_prev_days:
            #     print(f"{test_date}\t{config}\t{balance_change:.2f}\t{balance}")

        # последние несколько дней могут быть не рабочими, учитываем накопленную комиссию
        total_maj_commission += maj_commission
        balance += maj_commission

        last_config = config
        config = original_config

        profit = round(balance - start_balance)
        profit_p = round(100 * profit / start_balance, 2)

        return {
            'exp': f"{config.ticker} {config.pretest_type} {config.mods}",
            'profit': profit,
            'profit_p': profit_p,  # не удалять
            'profit_p_avg': round(profit_p / test_days_num, 2),  # не удалять
            'config': config,  # не удалять
            'last_conf': last_config,

            # 'profit_avg': round(sum(balance_change_list) / test_days_num, 2),
            #
            # 'pot_profit': potential_profit,
            #
            # 'days': test_days_num,
            # 'success_days': success_days,
            # 'success_p': round(success_days / test_days_num, 2),
            #
            'op': operations_cnt,
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

    def make_best_config(
            self,
            test_date: str,
            prev_days: int,
            original_config: RunConfig,
            last_config: RunConfig | None = None
    ) -> RunConfig:
        config, _ = self.make_best_config_with_profit(
            test_date,
            prev_days,
            original_config,
            last_config
        )
        return config

    def make_best_config_with_profit(
            self,
            test_date: str,
            prev_days: int,
            original_config: RunConfig,
            last_config: Optional[RunConfig] = None
    ) -> Tuple[RunConfig, float]:
        prev_test_date = TimeHelper.get_previous_date(TimeHelper.to_datetime(test_date))
        conf_list = self.make_config_variants(original_config, prev_test_date)

        if last_config is not None:
            conf_list2 = self.make_config_variants(last_config, prev_test_date)
            conf_list += conf_list2

        unique_conf_list = list(set(conf_list))
        results = []

        # запускаем получение результатов работы всех вариантов конфигурации
        for config in unique_conf_list:
            test_alg = TestAlgorithm(do_printing=False, config=config, use_cache=self.use_cache)
            res = test_alg.test(
                last_test_date=prev_test_date,
                test_days_num=prev_days,
                shares_count=0,

                # не менять, чтобы в рекурсию не уйти
                try_find_best_config=False,
            )
            if res:
                results.append(res)

        # сортировка результатов
        sorted_results = sorted(results, key=lambda x: float(x['profit_p']), reverse=True)

        # дальше берем лучший и возвращаем его
        best_res = sorted_results[0] if len(sorted_results) > 0 else None

        if best_res:
            best_conf = best_res['last_conf']
            # print(f"Best of {len(sorted_results)}/{len(conf_list)} {test_date} - {best_conf}")
            # print(f"{best_conf} with profit_p {best_res['profit_p']}")
            return best_conf, best_res['profit_p']
        else:
            print(f"Ошибка при получении лучшей конфигурации")
            return copy.copy(original_config), 0

    @staticmethod
    def get_step_by_price(price: float | None) -> float:
        if price is None or price == 0:
            return 0.2

        if price < 1:
            return 0.002
        elif price < 10:
            return 0.2
        else:
            return 0.2

    def make_config_variants(self, config: RunConfig, prev_test_date: str) -> list[RunConfig]:
        step_step = 1 if config.is_maj_trade() else 2
        step_diff = self.get_step_by_price(self.client_helper.get_current_price())
        step_round_digits = self.client_helper.instrument.round_signs
        return [
            (RunConfig(
                name=config.name,
                ticker=config.ticker,

                start_time=config.start_time,
                end_time=config.end_time,

                stop_up_p=config.stop_up_p,
                stop_down_p=config.stop_down_p,

                sleep_trading=config.sleep_trading,

                pretest_period=config.pretest_period,
                pretest_type=config.pretest_type,

                majority_trade=config.majority_trade,

                threshold_buy_steps=config.threshold_buy_steps,
                threshold_sell_steps=config.threshold_sell_steps,

                step_max_cnt=step_max_cnt,
                step_base_cnt=step_base_cnt,
                step_size=step_size,
                step_set_orders_cnt=config.step_set_orders_cnt,
                step_lots=config.step_lots,
                step_size_shift=config.step_size_shift,

                mods=config.mods
            ))
            # for step_max_cnt in [config.step_max_cnt]
            # for step_base_cnt in [config.step_max_cnt]
            # for step_size in [config.step_size]
            # for step_set_orders_cnt in [config.step_set_orders_cnt]
            for step_size in [
                max(round(config.step_size - step_diff, step_round_digits), 0.4),
                round(config.step_size, step_round_digits),
                round(config.step_size + step_diff, step_round_digits),
            ]
            for step_max_cnt in (
                [
                    self.get_max_steps_by_step_size(config, step_size, prev_test_date)
                ] if config.is_fan_layout() and prev_test_date else [
                    max(
                        config.step_max_cnt-step_step,
                        RunConfig.MIN_MAJ_MAX_CNT if config.is_maj_trade() else RunConfig.MIN_NON_MAJ_MAX_CNT
                    ),
                    config.step_max_cnt,
                    config.step_max_cnt+step_step,
                ]
            )
            for step_base_cnt in (
                [
                    0 if config.is_maj_trade() else step_max_cnt // 2
                ] if config.is_fan_layout() else [
                    0,
                    step_max_cnt,
                    -step_max_cnt if config.is_maj_trade() else step_max_cnt // 2
                ]
            )
        ]

    def get_max_steps_by_step_size(
            self,
            config: RunConfig,
            step_size: float,
            prev_test_date: str,
    ) -> int:
        max_steps = RunConfig.MIN_MAJ_MAX_CNT if config.is_maj_trade() else RunConfig.MIN_NON_MAJ_MAX_CNT

        if not config.pretest_period:
            return max_steps

        # перебираем указанные дни
        days_list = TickerCache.get_trade_days_only(prev_test_date, config.pretest_period)
        candles = self.client_helper.get_day_candles(
            datetime.strptime(days_list[0], "%Y-%m-%d"),
            datetime.strptime(days_list[-1], "%Y-%m-%d"))

        # берем максимальное изменение за эти дни в абсолютных значениях
        for candle in candles.candles:
            # берем дневную свечу
            c_open = self.client_helper.q2f(candle.open)
            c_high = self.client_helper.q2f(candle.high)
            c_low = self.client_helper.q2f(candle.low)

            # берем максимальное отклонение от открытия
            max_steps = max(
                max_steps,
                math.ceil(abs((c_open - c_high) / step_size)) if step_size > 0 else max_steps,
                math.ceil(abs((c_open - c_low) / step_size)) if step_size > 0 else max_steps,
            )

        return max_steps
