from app.models import Order
from bot.env import AbstractAccountingHelper
from app.constants import HistoryOrderType
from bot.env.test import ClientTestEnvHelper, TimeTestEnvHelper


class AccountingTestEnvHelper(AbstractAccountingHelper):
    def __init__(self, client: ClientTestEnvHelper, time: TimeTestEnvHelper):
        super().__init__(client, time)
        self.orders = []

    def reset(self):
        super().reset()
        self.orders = []

    def register_order(self, order: Order):
        self.orders.append(order)

    def get_executed_order_cnt(self) -> int:
        """
        Возвращает количество ордеров с реальными покупками, а не просто заявками
        """
        return sum(1 for order in self.orders if order.type in HistoryOrderType.EXECUTED_TYPES)

    def get_orders(self):
        return self.orders

    def get_instrument_count(self):
        return self.num
