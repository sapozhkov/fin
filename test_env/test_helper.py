from datetime import datetime
from typing import Tuple

from common.config import RunConfig
from bot.db import TickerCache
from bot.env.test import AccountingTestEnvHelper, LoggerTestEnvHelper, TimeTestEnvHelper
from test_env.client_test_env import ClientTestEnvHelper


class TestHelper:
    DEF_TICKER = 'RNFT'

    @staticmethod
    def get_time() -> TimeTestEnvHelper:
        time_helper = TimeTestEnvHelper()
        time_helper.set_time(datetime.now())
        return time_helper

    @staticmethod
    def get_logger(
            time_helper: TimeTestEnvHelper,
            do_printing=False,
    ) -> LoggerTestEnvHelper:
        return LoggerTestEnvHelper(time_helper, do_printing)

    @staticmethod
    def get_client(
            token,
            config: RunConfig,
            logger_helper: LoggerTestEnvHelper,
            time_helper: TimeTestEnvHelper,
    ) -> ClientTestEnvHelper:
        return ClientTestEnvHelper(token, config.ticker, logger_helper, time_helper)

    @staticmethod
    def get_ticker_cache(ticker=DEF_TICKER) -> TickerCache:
        return TickerCache(ticker)

    @staticmethod
    def get_accounting(client_helper=None) -> AccountingTestEnvHelper:
        return AccountingTestEnvHelper(client_helper)

    @staticmethod
    def get_helper_pack(token='', ticker=DEF_TICKER, do_printing=False) -> \
            Tuple[RunConfig, TimeTestEnvHelper, LoggerTestEnvHelper,
                  ClientTestEnvHelper, AccountingTestEnvHelper]:
        config = RunConfig(ticker=ticker, pretest_period=0)
        time_helper = TestHelper.get_time()
        logger_helper = TestHelper.get_logger(time_helper, do_printing)
        client_helper = TestHelper.get_client(token, config, logger_helper, time_helper)
        accounting_helper = TestHelper.get_accounting(client_helper)

        return config, time_helper, logger_helper, client_helper, accounting_helper
