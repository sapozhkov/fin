from abc import ABC, abstractmethod

from tinkoff.invest import OrderDirection, PostOrderResponse, OrderType

from app.constants import HistoryOrderType
from bot.helper import OrderHelper
from bot.env import AbstractProxyClient, AbstractTimeHelper
from app.models import Order


class AbstractAccountingHelper(ABC):
    def __init__(self, client, time):
        self.sum = 0
        self.num = 0
        self.operations_cnt = 0
        self.client: AbstractProxyClient = client
        self.time: AbstractTimeHelper = time
        self.run_id = 0

    @abstractmethod
    def register_order(self, order: Order):
        pass

    def add_deal_by_order(self, order: PostOrderResponse):
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

        if order.order_type == OrderType.ORDER_TYPE_MARKET:
            type_ = HistoryOrderType.BUY_MARKET if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.SELL_MARKET
        else:
            type_ = HistoryOrderType.EXECUTED_BUY_LIMIT if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.EXECUTED_SELL_LIMIT

        self.register_order(Order(
            run=self.run_id,
            type=type_,
            datetime=self.client.time.now(),
            price=avg_price,
            commission=self.client.round(commission / lots),
            total=total,
            count=lots
        ))

    def add_order(self, order: PostOrderResponse):
        lots = OrderHelper.get_lots(order)
        avg_price = self.client.round(OrderHelper.get_avg_price(order))
        if order.order_type == OrderType.ORDER_TYPE_MARKET:
            type_ = HistoryOrderType.BUY_MARKET if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.SELL_MARKET
        else:
            type_ = HistoryOrderType.OPEN_BUY_LIMIT if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.OPEN_SELL_LIMIT

        order = Order(
            run=self.run_id,
            type=type_,
            datetime=self.time.now(),
            price=avg_price,
            total=self.client.round(lots * avg_price),
            count=lots
        )

        self.register_order(order)

    def del_order(self, order: PostOrderResponse):
        lots = OrderHelper.get_lots(order)
        avg_price = self.client.round(OrderHelper.get_avg_price(order))
        type_ = HistoryOrderType.CANCEL_BUY_LIMIT if order.direction == OrderDirection.ORDER_DIRECTION_BUY \
            else HistoryOrderType.CANCEL_SELL_LIMIT

        order = Order(
            run=self.run_id,
            type=type_,
            datetime=self.time.now(),
            price=avg_price,
            total=self.client.round(lots * avg_price),
            count=lots
        )

        self.register_order(order)

    @abstractmethod
    def get_instrument_count(self):
        pass

    def reset(self):
        self.sum = 0
        self.operations_cnt = 0

    def get_num(self):
        return self.num

    def set_num(self, num):
        self.num = num

    def get_sum(self):
        return self.sum

    def set_run_id(self, id:int):
        self.run_id = id
