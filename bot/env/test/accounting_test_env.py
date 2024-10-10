from tinkoff.invest import PostOrderResponse, OrderType, OrderDirection

from app.models import Order
from bot.env import AbstractAccountingHelper
from bot.helper import OrderHelper
from app.constants import HistoryOrderType
from bot.env.test import ClientTestEnvHelper, TimeTestEnvHelper


class AccountingTestEnvHelper(AbstractAccountingHelper):
    def __init__(self, client: ClientTestEnvHelper, time: TimeTestEnvHelper):
        super().__init__(client, time)
        self.orders = []

    def reset(self):
        super().reset()
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
    def add_executed_order(self, order_type, order_direction, price, count, commission, total):
        if order_type == OrderType.ORDER_TYPE_MARKET:
            type_ = HistoryOrderType.BUY_MARKET if order_direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.SELL_MARKET
        else:
            type_ = HistoryOrderType.EXECUTED_BUY_LIMIT if order_direction == OrderDirection.ORDER_DIRECTION_BUY \
                else HistoryOrderType.EXECUTED_SELL_LIMIT

        self.orders.append(Order(
            run=0,
            type=type_,
            datetime=self.client.time.now(),
            price=price,
            commission=commission,
            total=total,
            count=count
        ))

    def get_executed_order_cnt(self) -> int:
        """
        Возвращает количество ордеров с реальными покупками, а не просто заявками
        """
        return sum(1 for order in self.orders if order.type in HistoryOrderType.EXECUTED_TYPES)

    def get_orders(self):
        return self.orders

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

        self.orders.append(order)

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

        self.orders.append(order)

    def get_instrument_count(self):
        return self.num
