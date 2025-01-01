from datetime import datetime, timezone
from typing import List, Tuple, Optional

from app.config import AccConfig
from bot import TestAlgorithm, TradingAccountBot
from bot.env.test import TimeTestEnvHelper, LoggerTestEnvHelper
from bot.env.test.acc import TestAccClientEnvHelper, AccDbTestEnvHelper


class TestAccAlgorithm:
    # todo перевезти всё в поддиректорию test
    def __init__(
            self,
            config: AccConfig,
            bot_alg_list: List[TestAlgorithm],
            do_printing=False,
            use_cache=True,
    ):
        # текущий конфиг прогона
        self.config: AccConfig = config

        self.bot_alg_list: List[TestAlgorithm] = bot_alg_list

        self.time_helper = TimeTestEnvHelper()
        self.logger_helper = LoggerTestEnvHelper(self.time_helper, do_printing)
        self.acc_client = TestAccClientEnvHelper(self.bot_alg_list)
        self.acc_db = AccDbTestEnvHelper(self.bot_alg_list, self.config)
        self.use_cache = use_cache  # todo del?

        self.acc_bot: Optional[TradingAccountBot] = None
        self.bot_started = False

        self.profit = 1

    def test(
            self,
            last_test_date,
            test_days_num,

    ):
        days_list = TestAlgorithm.get_days_list(last_test_date, test_days_num)

        for test_date in days_list:
            date_from, date_to = self.set_day(test_date)

            self.bots_create(test_date)
            self.acc_create()

            for dt in TestAlgorithm.get_time_list(date_from, date_to):
                self.bots_run_iteration(dt)
                self.acc_run_iteration(dt)

            self.bots_stop()
            self.acc_stop()

            self.bots_upd_day_trade()
            self.bots_calculate_day_results()
            self.acc_calculate_day_results()

        self.bots_calculate_total_results()
        self.acc_calculate_total_results()
        return self.get_results(test_days_num)

    def bots_create(self, test_date):
        for bot_alg in self.bot_alg_list:
            bot_alg.update_config(test_date, True)

        for bot_alg in self.bot_alg_list:
            if not bot_alg.process_this_day:
                continue
            bot_alg.bot_create()

    def bots_run_iteration(self, dt):
        for bot_alg in self.bot_alg_list:
            if not bot_alg.process_this_day:
                continue
            bot_alg.bot_run_iteration(dt)

    def bots_stop(self):
        for bot_alg in self.bot_alg_list:
            if not bot_alg.process_this_day:
                continue
            bot_alg.bot_stop()

    # todo вот это надо для кэширования, если не будет, то можно склеить со следующим методом
    def bots_upd_day_trade(self):
        for bot_alg in self.bot_alg_list:
            if not bot_alg.process_this_day:
                continue
            bot_alg.bot_upd_day_trade()

    def bots_calculate_day_results(self):
        for bot_alg in self.bot_alg_list:
            if not bot_alg.process_this_day:
                continue
            bot_alg.calculate_day_results()

    def bots_calculate_total_results(self):
        for bot_alg in self.bot_alg_list:
            bot_alg.calculate_total_results()

    def set_day(self, test_date: str) -> Tuple[datetime, datetime]:
        # прогоняем по дню (время в UTC)
        date_from_ = datetime.strptime(test_date + ' ' + TestAlgorithm.START_TIME,
                                       "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        date_to_ = datetime.strptime(test_date + ' ' + TestAlgorithm.END_TIME,
                                     "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

        # задаем параметры дня
        self.time_helper.set_current_time(date_from_)

        for bot_alg in self.bot_alg_list:
            bot_alg.set_day(test_date)

        return date_from_, date_to_

    def acc_create(self):
        # создаем бота с настройками
        self.acc_bot = TradingAccountBot(
            config=self.config,
            time_helper=self.time_helper,
            logger_helper=self.logger_helper,
            acc_client=self.acc_client,
            db_=self.acc_db,
        )

        if self.acc_bot.state == self.acc_bot.STATE_FINISHED:
            return False

        self.bot_started = False

        return True

    def acc_run_iteration(self, dt):
        """
        Запуск минутной итерации для бота
        :return: bool False если работу можно прерывать и бот закончил, True - продолжаем на след минуте
        """
        self.time_helper.set_time(dt)
        self.acc_bot.run_iteration()

    def acc_stop(self):
        self.acc_bot.stop()

    def get_acc_results(self, test_days_num):
        profit_p = 100 * (self.profit - 1)
        return {
            'profit': round(profit_p, 2),
            'p_avg': round(profit_p / test_days_num, 2) if test_days_num > 0 else 0,
            'config': self.config,
        }

    def acc_calculate_day_results(self):
        self.profit *= self.acc_bot.run_state.profit_n

    def acc_calculate_total_results(self):
        # todo implement
        pass

    def get_results(self, test_days_num):
        return {
            'acc': self.get_acc_results(test_days_num),
            'bots': [x.get_results(test_days_num) for x in self.bot_alg_list],
        }
