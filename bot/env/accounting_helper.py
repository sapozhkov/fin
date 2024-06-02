from abc import ABC, abstractmethod

from tinkoff.invest import OrderDirection, PostOrderResponse

from bot.helper import OrderHelper
from bot.env import AbstractProxyClient


class AbstractAccountingHelper(ABC):
    def __init__(self, client):
        self.sum = 0
        self.num = 0
        self.operations_cnt = 0
        self.client: AbstractProxyClient = client

    def add_deal_by_order(self, order):
        lots = OrderHelper.get_lots(order)
        avg_price = self.client.round(OrderHelper.get_avg_price(order))
        commission = OrderHelper.get_commission(order)

        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            avg_price = -avg_price
            self.num += lots
        else:
            self.num -= lots

        total = round(avg_price * lots - commission, 2)

        self.sum += total

        self.operations_cnt += 1

        self.add_deal(
            order.direction,
            avg_price,
            lots,
            self.client.round(commission / lots),
            total
        )

    def add_order(self, order: PostOrderResponse):
        pass

    def del_order(self, order: PostOrderResponse):
        pass

    @abstractmethod
    def add_deal(self, deal_type, price, count, commission, total):
        pass

    @abstractmethod
    def get_instrument_count(self):
        pass

    def reset(self):
        self.sum = 0

    def get_num(self):
        return self.num

    def set_num(self, num):
        self.num = num

    def get_sum(self):
        return self.sum
