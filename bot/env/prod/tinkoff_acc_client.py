from typing import List

from app.lib import TinkoffApi
from app.dto import BoughtInstrumentDto
from bot.env import AbstractAccClient


class TinkoffAccClient(AbstractAccClient):
    def sell(self, account_id: str, figi: str, quantity: int):
        return TinkoffApi.sell(account_id, figi, quantity)

    def get_shares_on_account(self, account_id) -> List[BoughtInstrumentDto]:
        return TinkoffApi.get_shares_on_account(account_id)

    def get_account_balance_rub(self, account_id: str) -> float:
        return TinkoffApi.get_account_balance_rub(account_id)
