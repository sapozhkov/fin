from typing import Tuple

from lib.historical_candles import HistoricalCandles
from test_env.accounting_test_env import AccountingTestEnvHelper
from test_env.client_test_env import ClientTestEnvHelper
from test_env.logger_test_env import LoggerTestEnvHelper
from test_env.time_test_env import TimeTestEnvHelper


class TestHelper:
    DEF_TICKER = 'RNFT'
    DEF_FIGI = 'BBG00F9XX7H4'

    @staticmethod
    def get_time() -> TimeTestEnvHelper:
        return TimeTestEnvHelper()

    @staticmethod
    def get_logger(
            time_helper: TimeTestEnvHelper | None = None,
            do_printing=False,
    ) -> LoggerTestEnvHelper:
        if time_helper is None:
            time_helper = TestHelper.get_time()

        return LoggerTestEnvHelper(time_helper, do_printing)

    @staticmethod
    def get_client(
            data_handler: HistoricalCandles | None = None,
            logger_helper=None,
            time_helper=None,
            ticker=DEF_TICKER,
            round_signs=1,
            step_size=0.1,
            figi=DEF_FIGI,
            currency='RUR',
    ) -> ClientTestEnvHelper:
        if time_helper is None:
            time_helper = TestHelper.get_time()

        if logger_helper is None:
            logger_helper = TestHelper.get_logger(time_helper)

        if data_handler is None:
            data_handler = TestHelper.get_historical_candles()

        client = ClientTestEnvHelper(ticker, logger_helper, time_helper, data_handler)
        client.set_ticker_params(round_signs, step_size, figi, currency)

        return client

    @staticmethod
    def get_historical_candles(token='', figi=DEF_FIGI, ticker=DEF_TICKER) -> HistoricalCandles:
        return HistoricalCandles(token, figi, ticker)

    @staticmethod
    def get_accounting(client_helper=None) -> AccountingTestEnvHelper:
        if client_helper is None:
            client_helper = TestHelper.get_client()
        return AccountingTestEnvHelper(client_helper)

    @staticmethod
    def get_helper_pack(token='', figi=DEF_FIGI, ticker=DEF_TICKER, do_printing=False) -> \
            Tuple[HistoricalCandles, TimeTestEnvHelper, LoggerTestEnvHelper,
                  ClientTestEnvHelper, AccountingTestEnvHelper]:
        data_handler = TestHelper.get_historical_candles(token, figi, ticker)
        time_helper = TestHelper.get_time()
        logger_helper = TestHelper.get_logger(time_helper, do_printing)
        client_helper = TestHelper.get_client(data_handler, logger_helper, time_helper, ticker, figi=figi)
        accounting_helper = TestHelper.get_accounting(client_helper)

        return data_handler, time_helper, logger_helper, client_helper, accounting_helper
