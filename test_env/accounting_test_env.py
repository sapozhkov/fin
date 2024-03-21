from tinkoff.invest import OrderDirection

from dto.deal_dto import DealDTO
from helper.accounting_helper import AbstractAccountingHelper
from lib.historical_trade import HistoricalTrade
from test_env.client_test_env import ClientTestEnvHelper


class AccountingTestEnvHelper(AbstractAccountingHelper):
    def __init__(self, client: ClientTestEnvHelper):
        super().__init__()
        self.client = client
        self.sum = 0
        self.deals = []

    def reset(self):
        self.sum = 0
        self.deals = []

    def add_deal_by_order(self, order):
        super().add_deal_by_order(order)

        price = self.client.quotation_to_float(order.executed_order_price)

        commission = self.client.quotation_to_float(order.executed_commission, 2)
        # хак. иногда итоговая комиссия не проставляется в нужное поле
        if commission == 0:
            commission = self.client.quotation_to_float(order.initial_commission, 2)

        if order.direction == OrderDirection.ORDER_DIRECTION_BUY:
            price = -price

        total = round(price - commission, 2)

        self.deals.append(DealDTO(
            None,
            self.client.time.now(),
            HistoricalTrade.TYPE_BUY if order.direction == OrderDirection.ORDER_DIRECTION_BUY
                else HistoricalTrade.TYPE_SELL,
            '',
            price,
            commission,
            total
        ))

        self.sum += total

    def get_deals(self):
        return self.deals
