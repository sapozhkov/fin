import unittest

from app.config import RunConfig
from starter import Stock, distribute_budget


class TestDistributeBudget(unittest.TestCase):
    @staticmethod
    def create_stocks(stock_data):
        out = []
        for name, budget in stock_data:
            stock = Stock()
            conf = RunConfig()
            conf.name = name
            conf.step_lots = 0
            stock.budget = budget
            stock.config = conf
            stock.instrument_lots = 1
            out.append(stock)
        return out

    @staticmethod
    def create_stocks_with_lots(stock_data):
        out = []
        for name, budget, lots in stock_data:
            stock = Stock()
            conf = RunConfig()
            conf.name = name
            conf.step_lots = 0
            stock.budget = budget
            stock.config = conf
            stock.instrument_lots = lots
            out.append(stock)
        return out

    def test_equal_distribution(self):
        stocks = self.create_stocks([("A", 10), ("B", 10), ("C", 10)])
        budget = 30
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {"A": 1, "B": 1, "C": 1}
        self.assertEqual(expected, result)

    def test_remaining_budget(self):
        stocks = self.create_stocks([("A", 10), ("B", 10), ("C", 10)])
        budget = 35
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {"A": 1, "B": 1, "C": 1}
        self.assertEqual(expected, result)

    def test_unequal_stock_budgets(self):
        stocks = self.create_stocks([("A", 10), ("B", 20), ("C", 30)])
        budget = 60
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {"A": 2, "B": 2, "C": 0}
        self.assertEqual(expected, result)

    def test_no_budget(self):
        stocks = self.create_stocks([("A", 10), ("B", 20), ("C", 30)])
        budget = 0
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {"A": 0, "B": 0, "C": 0}
        self.assertEqual(expected, result)

    def test_large_budget(self):
        stocks = self.create_stocks([("A", 10), ("B", 20), ("C", 30)])
        budget = 300
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {"A": 11, "B": 5, "C": 3}
        self.assertEqual(expected, result)

    def test_complex_distribution(self):
        stocks = self.create_stocks([("A", 10), ("B", 15), ("C", 20), ("D", 25)])
        budget = 100
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {"A": 2, "B": 1, "C": 2, "D": 1}
        self.assertEqual(expected, result)

    def test_fair_distribution(self):
        stocks = self.create_stocks([("A", 51), ("B", 52), ("C", 53), ("D", 54), ("E", 55)])
        budget = 500
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {'A': 1, 'B': 2, 'C': 2, 'D': 2, 'E': 2}
        self.assertEqual(expected, result)

    def test_fair_distribution_2(self):
        stocks = self.create_stocks([("A", 26), ("B", 27), ("C", 28), ("D", 29), ("E", 30)])
        budget = 500
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {'A': 3, 'B': 3, 'C': 3, 'D': 4, 'E': 4}
        self.assertEqual(expected, result)

    def test_with_lots(self):
        stocks = self.create_stocks_with_lots([("A", 20, 1), ("B", 17, 10)])
        budget = 500
        distribute_budget(stocks, budget)
        result = {stock.config.name: stock.lots for stock in stocks}
        expected = {'A': 16, 'B': 10}
        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
