from tinkoff.invest import OrderDirection

from helper.accounting_helper import AbstractAccountingHelper


class AccountingTestEnvHelper(AbstractAccountingHelper):
    def __init__(self, client):
        self.client = client
        self.sum = 0

    def add_deal_by_order(self, order):
        price = self.client.quotation_to_float(order.executed_order_price)
        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            price = -price
        commission = self.client.quotation_to_float(order.executed_commission, 2)
        # хак. иногда итоговая комиссия не проставляется в нужное поле
        if commission == 0:
            commission = self.client.quotation_to_float(order.initial_commission, 2)
        self.sum += round(price - commission, 2)
