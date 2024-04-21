import unittest
from datetime import datetime, timezone
from dateutil import parser

from dto.order_dto import OrderDTO


class TestOrderDTO(unittest.TestCase):

    def test_order_repr(self):
        datetime_ = datetime.now()
        type_ = 'buy'
        price = 100
        count = 5
        algorithm_name = 'TestAlgorithm'

        order = OrderDTO(datetime_, type_, price, count, algorithm_name)
        expected_repr = f"{datetime_}, {algorithm_name}, {price} x {count} "
        self.assertEqual(repr(order), expected_repr)

    def test_order_attributes(self):
        datetime_ = datetime.now()
        type_ = 'buy'
        price = 100
        count = 5
        algorithm_name = 'TestAlgorithm'

        order = OrderDTO(datetime_, type_, price, count, algorithm_name)

        self.assertEqual(order.datetime, datetime_)
        self.assertEqual(order.type, type_)
        self.assertEqual(order.price, price)
        self.assertEqual(order.count, count)
        self.assertEqual(order.algorithm_name, algorithm_name)

if __name__ == '__main__':
    unittest.main()
