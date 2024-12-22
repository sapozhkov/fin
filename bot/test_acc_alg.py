from typing import List

from app.config import AccConfig
from bot import TestAlgorithm
from bot.env.test import TimeTestEnvHelper, LoggerTestEnvHelper


class TestAccAlgorithm:
    def __init__(
            self,
            config: AccConfig,
            bot_alg_list: List[TestAlgorithm],
            do_printing=False,
            use_cache=True,
    ):
        # текущий конфиг прогона
        self.config: AccConfig = config

        self.time_helper = TimeTestEnvHelper()
        self.logger_helper = LoggerTestEnvHelper(self.time_helper, do_printing)
        self.use_cache = use_cache  # todo del?

    def test(
            self,
            last_test_date,
            test_days_num,

    ):
        pass
        # self.bot_alg_list: List[TestAlgorithm] = []
        #
        # days_list = TestHelper.get_trade_days_only(last_test_date, test_days_num) # для полного промежутка без конфига
        # # self.accounting_helper.set_num(shares_count) - это при инициализации должно быть
        #
        # for test_date in days_list:
        #     date_from, date_to = self.set_day(test_date)
        #
        #     # обновление конфигов и возможность точечного отключения на день ботов
        #     self.bots_upd_config()
        #
        #     self.bots_create()
        #
        #     time_list = self.time_helper.get_hour_minute_pairs(date_from, date_to)
        #     for dt in time_list:
        #         self.time_helper.set_time(dt)
        #         self.bots_execute()
        #         self.acc_execute()
        #
        #     self.bots_stop()
        #     self.acc_stop()
        #
        #     self.calculate_day_results()
        #
        # self.calculate_total_results()
        # return self.get_results()