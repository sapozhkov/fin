import unittest
from datetime import datetime

from bot import TradingBot
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

    @staticmethod
    def test_data():
        """
        формат min_increment, round_signs, price, rounded_price
        перебрать инкременты: 0.01, 0.02, 0.05, 0.1, 0.2, 0.5,
        на будущее: 1, 2, 5, 10, 20, 50
        """
        return [
            (0.01, 2, 321.241, 321.24),
            (0.01, 2, 321.249, 321.25),
            (0.01, 2, 321.251, 321.25),

            (0.02, 2, 321.241, 321.24),
            (0.02, 2, 321.249, 321.24),
            (0.02, 2, 321.251, 321.26),

            (0.05, 2, 321.241, 321.25),
            (0.05, 2, 321.249, 321.25),
            (0.05, 2, 321.251, 321.25),
            (0.05, 2, 321.281, 321.30),

            (0.1, 1, 321.241, 321.2),
            (0.1, 1, 321.249, 321.2),
            (0.1, 1, 321.251, 321.3),

            (0.2, 1, 321.241, 321.2),
            (0.2, 1, 321.249, 321.2),
            (0.2, 1, 321.251, 321.2),
            (0.2, 1, 321.301, 321.4),

            (0.5, 1, 321.241, 321.0),
            (0.5, 1, 321.249, 321.0),
            (0.5, 1, 321.251, 321.5),
        ]

    def test_round(self):
        # todo когда появится спец тест на клиентов, утащить туда
        for min_increment, round_signs, price, rounded_price in self.test_data():
            with self.subTest(min_increment=min_increment, round_signs=round_signs,
                              price=price, rounded_price=rounded_price):
                self.bot.client.instrument.min_increment = min_increment
                self.bot.client.instrument.round_signs = round_signs
                self.assertEqual(rounded_price, self.bot.round(price),
                                 f"{min_increment}, {round_signs}, {price}, {rounded_price}")


if __name__ == '__main__':
    unittest.main()
