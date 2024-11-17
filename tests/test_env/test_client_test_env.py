import unittest

from tinkoff.invest import OrderDirection, OrderType, OrderExecutionReportStatus, PostOrderResponse, OrderState

from bot import TestHelper
from bot.helper import OrderHelper


class TestOrderHelper(unittest.TestCase):

    def setUp(self):

        self.config, self.time_helper, self.logger_helper, self.client_helper, self.accounting_helper = \
            TestHelper.get_helper_pack()

    def get_order_avg_price(self, order: PostOrderResponse | OrderState) -> float:
        return self.client_helper.round(OrderHelper.get_avg_price(order))

    def test_get_avg_price_on_post(self):
        price = 100
        lots = 10

        self.client_helper.set_current_price(price)

        # покупка по рыночной цене
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY,
                                               None, OrderType.ORDER_TYPE_MARKET)
        self.assertEqual(self.get_order_avg_price(order), price)
        self.assertEqual(OrderHelper.get_lots(order), lots)

        # продажа по рыночной цене
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL,
                                               None, OrderType.ORDER_TYPE_MARKET)
        self.assertEqual(self.get_order_avg_price(order), price)

        # лимитная покупка
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY,
                                               price, OrderType.ORDER_TYPE_LIMIT)
        self.assertEqual(self.get_order_avg_price(order), price)

        # лимитная продажа
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL,
                                               price, OrderType.ORDER_TYPE_LIMIT)
        self.assertEqual(self.get_order_avg_price(order), price)

        # лимитная продажа
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL,
                                               price, OrderType.ORDER_TYPE_LIMIT)
        self.assertEqual(self.get_order_avg_price(order), price)

        # покупка по лучшей цене
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY,
                                               None, OrderType.ORDER_TYPE_BESTPRICE)
        self.assertEqual(self.get_order_avg_price(order), price)
        self.assertEqual(OrderHelper.get_lots(order), lots)

        # продажа по лучшей цене
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL,
                                               None, OrderType.ORDER_TYPE_BESTPRICE)
        self.assertEqual(self.get_order_avg_price(order), price)

    def test_get_avg_price_on_state(self):
        price = 100
        lots = 10

        self.client_helper.set_current_price(price)

        # лимитная покупка
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY,
                                               price, OrderType.ORDER_TYPE_LIMIT)

        # открытая
        order_state = self.client_helper.get_order_state(order)
        self.assertEqual(OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_NEW, order_state.execution_report_status)
        self.assertEqual(self.get_order_avg_price(order_state), price)
        self.assertEqual(OrderHelper.get_lots(order_state), lots)

        # закрываем
        self.client_helper.executed_orders_ids.append(order.order_id)

        # закрытая
        order_state = self.client_helper.get_order_state(order)
        self.assertEqual(OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL, order_state.execution_report_status)
        self.assertEqual(self.get_order_avg_price(order_state), price)
        self.assertEqual(OrderHelper.get_lots(order_state), lots)


if __name__ == '__main__':
    unittest.main()
