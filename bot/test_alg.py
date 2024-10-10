import copy
from datetime import datetime, timezone

from tinkoff.invest import OrderDirection

from bot import TradingBot
from bot.db import TickerCache
from bot.env.test import TimeTestEnvHelper, LoggerTestEnvHelper, ClientTestEnvHelper, AccountingTestEnvHelper
from bot.helper import OrderHelper
from app.config import RunConfig
from app.helper import TimeHelper, LocalCache


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

        auto_conf_days_freq=0,
        auto_conf_prev_days=0,
    ):
        """
        Провести тестирование по заданному конфигу
        :param last_test_date: последняя дата для теста
        :param test_days_num: сколько дней надо проверить
        :param shares_count: сколько инструментов на балансе
        :param auto_conf_days_freq: частота подстройки конфига. если задано, то подстраивается
        :param auto_conf_prev_days: сколько дней претестить для каждого дня
        :return:
        """
        if test_days_num == 0:
            return None

        # внутренние переменные
        profit = 0
        success_days = 0
        balance_change_list = []
        operations_cnt = 0
        operations_cnt_list = []

        if last_test_date is None:
            # до утра гоняем предыдущий день, а то откинется лишний
            if TimeHelper.is_morning():
                last_test_date = TimeHelper.get_previous_date()
            else:
                last_test_date = TimeHelper.get_current_date()

        # #162 #159 тип выбора предыдущих дней - рабочие/все. может пригодиться для тестирования/экспериментов
        # days_list = TickerCache.get_days_list(last_test_date, test_days_num)
        days_list = TickerCache.get_days_list_working_only(last_test_date, test_days_num)

        self.accounting_helper.set_num(shares_count)

        # для расчета прибыли за весь период. купил в начале, в конце продал
        started_t = False
        start_price_t = 0
        # end_price_t = 0

        original_config = copy.copy(self.config)
        maj_commission = 0
        total_maj_commission = 0
        config = None

        # закручиваем цикл по датам
        for test_date in days_list:
            if self.accounting_helper.get_num() < 0:
                maj_commission += self.client_helper.get_current_price() * self.accounting_helper.get_num() * 0.0012
                # print(f"{test_date} - maj_commission {round(maj_commission, 2)} = "
                #       f"{self.client_helper.get_current_price()} * {self.accounting_helper.get_num()} * {0.0012}")

            if not TimeHelper.is_working_day(TimeHelper.to_datetime(test_date)):
                continue

            if auto_conf_days_freq:
                config = self.make_best_config(
                    start_date=days_list[0],
                    test_date=test_date,
                    auto_conf_days_freq=auto_conf_days_freq,
                    auto_conf_prev_days=auto_conf_prev_days,
                    original_config=original_config,
                    last_config=config)
            else:
                config = copy.copy(original_config)

            # дальше текущего времени не убегаем
            config.end_time = self.get_end_time(test_date, config.end_time)

            # прогоняем по дню (время в UTC)
            date_from = datetime.strptime(test_date + ' ' + config.start_time, "%Y-%m-%d %H:%M")
            date_to = datetime.strptime(test_date + ' ' + config.end_time, "%Y-%m-%d %H:%M")

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

            if not started_t:
                started_t = True
                start_price_t = start_price

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

            profit = round(profit + balance_change, 2)

            if balance_change > 0:
                success_days += 1

            balance_change_list.append(balance_change)

        # последние несколько дней могут быть не рабочими, учитываем накопленную комиссию
        total_maj_commission += maj_commission
        profit += maj_commission

        last_config = config
        config = original_config

        # коэф мажоритарной торговли. с ней заявок в 2 раза больше ставится, так как в 2 стороны открываем торги
        maj_k = 2 if config.majority_trade else 1

        profit_p = round(100 * profit / (start_price_t * config.step_max_cnt * config.step_lots * maj_k), 2) \
            if start_price_t and config.step_max_cnt else 0

        # # это для обычной торговли. купил в начале, в конце продал
        # potential_profit = round((end_price_t - start_price_t) * config.step_max_cnt * config.step_lots, 2)
        # # сколько от обычной торговли в процентах ты сделал
        # potential_profit_p = round(profit / potential_profit, 2) if potential_profit > 0 else 0

        return {
            'profit': profit,
            'profit_p': profit_p,  # не удалять
            'profit_p_avg': round(profit_p / test_days_num, 2),  # не удалять
            # 'pot_p': potential_profit_p,
            'config': config,  # не удалять
            'last_conf': last_config,
            # 'maj_com': round(total_maj_commission, 2),

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

    @staticmethod
    def is_nth_day_from_start(start_date_string: str, date_string: str, n: int):
        if n == 0:
            return True

        start_date = datetime.strptime(start_date_string, "%Y-%m-%d")
        target_date = datetime.strptime(date_string, "%Y-%m-%d")

        days_difference = (target_date - start_date).days
        return days_difference % n == 0

    def make_best_config(
            self,
            start_date: str,
            test_date: str,
            auto_conf_days_freq: int,
            auto_conf_prev_days: int,
            original_config: RunConfig,
            last_config: RunConfig | None
    ) -> RunConfig:
        config, _ = self.make_best_config_with_profit(
            start_date,
            test_date,
            auto_conf_days_freq,
            auto_conf_prev_days,
            original_config,
            last_config
        )
        return config

    def make_best_config_with_profit(
            self,
            start_date: str,
            test_date: str,
            auto_conf_days_freq: int,
            auto_conf_prev_days: int,
            original_config: RunConfig,
            last_config: RunConfig | None
    ) -> (RunConfig, float):
        need_run = self.is_nth_day_from_start(start_date, test_date, auto_conf_days_freq)

        if not need_run:
            return copy.copy(last_config) if last_config is not None else copy.copy(original_config), 1

        conf_list = self.make_config_variants(original_config)

        if last_config is not None:
            conf_list2 = self.make_config_variants(last_config)
            conf_list += conf_list2

        unique_conf_list = list(set(conf_list))
        results = []

        # запускаем получение результатов работы всех вариантов конфигурации
        for config in unique_conf_list:
            test_alg = TestAlgorithm(do_printing=False, config=config, use_cache=self.use_cache)
            res = test_alg.test(
                last_test_date=TimeHelper.get_previous_date(TimeHelper.to_datetime(test_date)),
                test_days_num=auto_conf_prev_days,
                shares_count=0,

                # не менять, чтобы в рекурсию не уйти
                auto_conf_days_freq=0,
                auto_conf_prev_days=0,
            )
            if res:
                results.append(res)

        # сортировка результатов
        sorted_results = sorted(results, key=lambda x: float(x['profit_p']), reverse=True)

        # дальше берем лучший и возвращаем его
        best_res = sorted_results[0] if len(sorted_results) > 0 else None

        if best_res:
            best_conf = best_res['last_conf']
            if last_config:
                # пробросить, так как сбрасывается
                best_conf.use_shares = last_config.use_shares
            # print(f"Best of {len(sorted_results)}/{len(conf_list)} {test_date} - {best_conf}")
            # print(f"{best_conf} with profit_p {best_res['profit_p']}")
            return best_conf, best_res['profit_p']
        else:
            print(f"Ошибка при получении лучшей конфигурации")
            return copy.copy(original_config), 0.01

    @staticmethod
    def get_step_by_price(price: float | None) -> float:
        if price is None:
            return 0.2

        if price < 1:
            return 0.002
        elif price < 10:
            return 0.2
        else:
            return 0.2

    def make_config_variants(self, config: RunConfig) -> list[RunConfig]:
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
                sleep_no_trade=config.sleep_no_trade,

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

                use_shares=None,  # тут None, чтобы текущая настройка с чистого листа работала
            ))
            # for step_max_cnt in [config.step_max_cnt]
            # for step_base_cnt in [config.step_max_cnt]
            # for step_size in [config.step_size]
            # for step_set_orders_cnt in [config.step_set_orders_cnt]
            for step_max_cnt in [
                config.step_max_cnt,
                config.step_max_cnt+step_step,
                max(
                    config.step_max_cnt-step_step,
                    RunConfig.MIN_MAJ_MAX_CNT if config.is_maj_trade() else RunConfig.MIN_NON_MAJ_MAX_CNT
                ),
            ]
            for step_base_cnt in (
                [
                    0 if config.is_maj_trade() else step_max_cnt // 2
                ] if config.is_fan_layout() else [
                    0,
                    step_max_cnt,
                    -step_max_cnt if config.is_maj_trade() else step_max_cnt // 2
                ]
            )
            for step_size in [
                round(config.step_size, step_round_digits),
                round(config.step_size - step_diff, step_round_digits),
                round(config.step_size + step_diff, step_round_digits),
            ]
        ]
