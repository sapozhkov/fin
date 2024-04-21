import unittest
from datetime import datetime, timezone
from dateutil import parser

from dto.deal_dto import DealDTO


class TestDealDTO(unittest.TestCase):

    def test_deal_repr(self):
        id_ = 1
        datetime_ = datetime.now()
        type_ = 'buy'
        algorithm_name = 'TestAlgorithm'
        price = 100
        count = 5
        commission = 1
        total = 500

        deal = DealDTO(id_, datetime_, type_, algorithm_name, price, count, commission, total)
        expected_repr = f"{datetime_}, {algorithm_name}, {total} = {count} x ({price} - {commission}) "
        self.assertEqual(repr(deal), expected_repr)

    def test_deal_attributes(self):
        id_ = 1
        datetime_ = datetime.now()
        type_ = 'buy'
        algorithm_name = 'TestAlgorithm'
        price = 100
        count = 5
        commission = 1
        total = 500

        deal = DealDTO(id_, datetime_, type_, algorithm_name, price, count, commission, total)

        self.assertEqual(deal.id, id_)
        self.assertEqual(deal.datetime, datetime_)
        self.assertEqual(deal.type, type_)
        self.assertEqual(deal.algorithm_name, algorithm_name)
        self.assertEqual(deal.price, price)
        self.assertEqual(deal.count, count)
        self.assertEqual(deal.commission, commission)
        self.assertEqual(deal.total, total)

if __name__ == '__main__':
    unittest.main()
