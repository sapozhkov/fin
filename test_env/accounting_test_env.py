from tinkoff.invest import OrderDirection

from helper.accounting_helper import AbstractAccountingHelper
from test_env.client_test_env import ClientTestEnvHelper


class AccountingTestEnvHelper(AbstractAccountingHelper):
    def __init__(self, client: ClientTestEnvHelper):
        self.client = client
        self.sum = 0
        self.deals = []

    def reset(self):
        self.sum = 0
        self.deals = []

    def add_deal_by_order(self, order):
        price = self.client.quotation_to_float(order.executed_order_price)

        self.deals.append({
            'time': self.client.time.now(),
            'price': price,
            'type': 'buy' if order.direction == OrderDirection.ORDER_DIRECTION_BUY else 'sell'
        })

        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            price = -price

        commission = self.client.quotation_to_float(order.executed_commission, 2)
        # хак. иногда итоговая комиссия не проставляется в нужное поле
        if commission == 0:
            commission = self.client.quotation_to_float(order.initial_commission, 2)

        self.sum += round(price - commission, 2)
