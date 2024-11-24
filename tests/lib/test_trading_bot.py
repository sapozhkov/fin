import unittest
from datetime import datetime

from app.helper import TimeHelper
from bot import TradingBot, TestHelper


class MyTestCase(unittest.TestCase):
    def setUp(self):

        self.config, self.time_helper, self.logger_helper, self.client_helper, self.accounting_helper = \
            TestHelper.get_helper_pack()

        self.bot = TradingBot(
            config=self.config,
            time_helper=self.time_helper,
            logger_helper=self.logger_helper,
            client_helper=self.client_helper,
            accounting_helper=self.accounting_helper,
        )

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
        # когда появится спец тест на клиентов, утащить туда
        for min_increment, round_signs, price, rounded_price in self.test_data():
            with self.subTest(min_increment=min_increment, round_signs=round_signs,
                              price=price, rounded_price=rounded_price):
                self.bot.client.instrument.min_increment = min_increment
                self.bot.client.instrument.round_signs = round_signs
                self.assertEqual(rounded_price, self.bot.trade_strategy.round(price),
                                 f"{min_increment}, {round_signs}, {price}, {rounded_price}")


if __name__ == '__main__':
    unittest.main()
