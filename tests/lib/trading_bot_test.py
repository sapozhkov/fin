import unittest
from datetime import datetime

from dto.config_dto import ConfigDTO
from lib.trading_bot import TradingBot
from test_env.test_helper import TestHelper


class MyTestCase(unittest.TestCase):
    def setUp(self):

        self.config, self.time_helper, self.logger_helper, self.client_helper, self.accounting_helper = \
            TestHelper.get_helper_pack()

        self.bot = TradingBot(
            '',
            config=self.config,
            time_helper=self.time_helper,
            logger_helper=self.logger_helper,
            client_helper=self.client_helper,
            accounting_helper=self.accounting_helper,
        )

    def test_is_trading_day(self):
        # пятница - обычный день
        date = datetime.strptime('2024-04-26 06:30', "%Y-%m-%d %H:%M")
        self.time_helper.set_time(date)
        self.assertTrue(self.bot.is_trading_day())

        # рабочая суббота
        date = datetime.strptime('2024-04-27 06:30', "%Y-%m-%d %H:%M")
        self.time_helper.set_time(date)
        self.assertTrue(self.bot.is_trading_day())

        # обычное воскресенье
        date = datetime.strptime('2024-04-28 06:30', "%Y-%m-%d %H:%M")
        self.time_helper.set_time(date)
        self.assertFalse(self.bot.is_trading_day())

        # 1 мая - среда - не работаем
        date = datetime.strptime('2024-05-01 06:30', "%Y-%m-%d %H:%M")
        self.time_helper.set_time(date)
        self.assertFalse(self.bot.is_trading_day())


if __name__ == '__main__':
    unittest.main()
