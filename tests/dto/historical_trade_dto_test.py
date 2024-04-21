import unittest

from dto.historical_trade_dto import HistoricalTradeDTO


class TestHistoricalTradeDTO(unittest.TestCase):

    def test_historical_trade_attributes(self):
        date = '2022-04-20'
        alg_name = 'TestAlgorithm'
        total = 123.456
        cnt = 5
        is_closed = True

        trade = HistoricalTradeDTO(date, alg_name, total, cnt, is_closed)

        self.assertEqual(trade.date, date)
        self.assertEqual(trade.alg_name, alg_name)
        self.assertEqual(trade.total, round(total, 2))
        self.assertEqual(trade.cnt, cnt)
        self.assertEqual(trade.is_closed, is_closed)


if __name__ == '__main__':
    unittest.main()
