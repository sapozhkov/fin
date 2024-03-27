from tinkoff.invest import OrderDirection, PostOrderResponse, OrderType

from dto.deal_dto import DealDTO
from prod_env.accounting_helper import AbstractAccountingHelper

from dto.order_dto import OrderDTO
from lib.order_helper import OrderHelper
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

    def add_deal(self, deal_type, price, commission, total):
        self.deals.append(DealDTO(
            None,
            self.client.time.now(),
            deal_type,
            'test_alg',
            price,
            commission,
            total
        ))

    def get_deals(self):
        return self.deals

    def get_orders(self):
        return self.orders

    def add_order(self, order: PostOrderResponse):
        if order.order_type == OrderType.ORDER_TYPE_MARKET:
            price = self.client.current_price
            type_ = OrderHelper.OPEN_BUY_MARKET if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else OrderHelper.OPEN_SELL_MARKET
        else:
            price = abs(self.client.quotation_to_float(order.initial_order_price))
            type_ = OrderHelper.OPEN_BUY_LIMIT if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else OrderHelper.OPEN_SELL_LIMIT

        self.orders.append(OrderDTO(
            self.client.time.now(),
            type_,
            price,
            'test_alg'
        ))

    def del_order(self, order: PostOrderResponse):
        type_ = OrderHelper.CANCEL_BUY_LIMIT if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
            else OrderHelper.CANCEL_SELL_LIMIT

        self.orders.append(OrderDTO(
            self.client.time.now(),
            type_,
            self.client.quotation_to_float(order.initial_order_price),
            'test_alg'
        ))

    def get_instrument_count(self):
        return self.num
