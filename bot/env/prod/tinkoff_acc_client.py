from app.lib import TinkoffApi
from bot.env import AbstractAccClient


class TinkoffAccClient(AbstractAccClient):
    @staticmethod
    def sell(account_id: str, figi: str, quantity: int):
        return TinkoffApi.sell(account_id, figi, quantity)

    @staticmethod
    def get_shares_on_account(account_id):
        return TinkoffApi.get_shares_on_account(account_id)

    @staticmethod
    def get_account_balance_rub(account_id: str) -> float:
        return TinkoffApi.get_account_balance_rub(account_id)
