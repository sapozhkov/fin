from tinkoff.invest import OrderDirection

from dto.deal_dto import DealDTO
from helper.accounting_helper import AbstractAccountingHelper
from lib.historical_trade import HistoricalTrade
from test_env.client_test_env import ClientTestEnvHelper


class AccountingTestEnvHelper(AbstractAccountingHelper):
    def __init__(self, client: ClientTestEnvHelper):
        super().__init__(client)
        self.deals = []

    def reset(self):
        super().reset()
        self.deals = []

    def add_deal(self, deal_type, price, commission, total):
        self.deals.append(DealDTO(
            None,
            self.client.time.now(),
            deal_type,
            '',
            price,
            commission,
            total
        ))

    def get_deals(self):
        return self.deals
