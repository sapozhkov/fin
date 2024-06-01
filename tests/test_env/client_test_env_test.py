import unittest

from tinkoff.invest import OrderDirection, OrderType, OrderExecutionReportStatus

from bot.helper import OrderHelper
from test_env.test_helper import TestHelper


class TestOrderHelper(unittest.TestCase):

    def setUp(self):

        self.config, self.time_helper, self.logger_helper, self.client_helper, self.accounting_helper = \
            TestHelper.get_helper_pack()
        self.order_helper = OrderHelper(self.client_helper)

    def test_get_avg_price_on_post(self):
        price = 100
        lots = 10

        self.client_helper.set_current_price(price)

        # покупка по рыночной цене
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY,
                                               None, OrderType.ORDER_TYPE_MARKET)
        self.assertEqual(self.order_helper.get_avg_price(order), price)
        self.assertEqual(self.order_helper.get_lots(order), lots)

        # продажа по рыночной цене
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL,
                                               None, OrderType.ORDER_TYPE_MARKET)
        self.assertEqual(self.order_helper.get_avg_price(order), price)

        # лимитная покупка
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_BUY,
                                               price, OrderType.ORDER_TYPE_LIMIT)
        self.assertEqual(self.order_helper.get_avg_price(order), price)

        # лимитная продажа
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL,
                                               price, OrderType.ORDER_TYPE_LIMIT)
        self.assertEqual(self.order_helper.get_avg_price(order), price)

        # лимитная продажа
        order = self.client_helper.place_order(lots, OrderDirection.ORDER_DIRECTION_SELL,
                                               price, OrderType.ORDER_TYPE_LIMIT)
        self.assertEqual(self.order_helper.get_avg_price(order), price)

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
        self.assertEqual(self.order_helper.get_avg_price(order_state), price)
        self.assertEqual(self.order_helper.get_lots(order_state), lots)

        # закрываем
        self.client_helper.executed_orders_ids.append(order.order_id)

        # закрытая
        order_state = self.client_helper.get_order_state(order)
        self.assertEqual(OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL, order_state.execution_report_status)
        self.assertEqual(self.order_helper.get_avg_price(order_state), price)
        self.assertEqual(self.order_helper.get_lots(order_state), lots)


if __name__ == '__main__':
    unittest.main()
