from tinkoff.invest import OrderDirection, PostOrderResponse, OrderType

from common.dto import DealDTO, OrderDTO
from prod_env.accounting_helper import AbstractAccountingHelper

from lib.order_vis_helper import OrderVisHelper
from test_env.client_test_env import ClientTestEnvHelper


class AccountingTestEnvHelper(AbstractAccountingHelper):
    def __init__(self, client: ClientTestEnvHelper):
        super().__init__(client)
        self.deals = []
        self.orders = []

    def reset(self):
        super().reset()
        self.deals = []
        self.orders = []

    def add_deal(self, deal_type, price, count, commission, total):
        self.deals.append(DealDTO(
            None,
            self.client.time.now(),
            deal_type,
            'test_alg',
            price,
            count,
            commission,
            total
        ))

    def get_deals(self):
        return self.deals

    def get_orders(self):
        return self.orders

    def add_order(self, order: PostOrderResponse):
        lots = self.order_helper.get_lots(order)
        avg_price = self.order_helper.get_avg_price(order)
        if order.order_type == OrderType.ORDER_TYPE_MARKET:
            type_ = OrderVisHelper.OPEN_BUY_MARKET if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else OrderVisHelper.OPEN_SELL_MARKET
        else:
            type_ = OrderVisHelper.OPEN_BUY_LIMIT if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else OrderVisHelper.OPEN_SELL_LIMIT

        self.orders.append(OrderDTO(
            self.client.time.now(),
            type_,
            avg_price,
            lots,
            'test_alg'
        ))

    def del_order(self, order: PostOrderResponse):
        lots = self.order_helper.get_lots(order)
        avg_price = self.order_helper.get_avg_price(order)
        type_ = OrderVisHelper.CANCEL_BUY_LIMIT if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
            else OrderVisHelper.CANCEL_SELL_LIMIT

        self.orders.append(OrderDTO(
            self.client.time.now(),
            type_,
            avg_price,
            lots,
            'test_alg'
        ))

    def get_instrument_count(self):
        return self.num
